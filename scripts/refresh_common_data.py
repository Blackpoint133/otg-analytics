"""Bounded current-item metadata reconciliation for staging.

The unit of work is one representative current item name, never one NFT.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.fspath(ROOT))

from streamlit_opensea_sales.common_data_sync import (
    MAX_METADATA_FETCHES_PER_RUN,
    merge_nonblank_metadata,
    normalize_item_name,
    normalization_collisions,
    select_reconciliation_targets,
)

DATA = ROOT / "streamlit_opensea_sales" / "data_opensea_sales"
INDEX = DATA / "items_index.json"
STATE = DATA / "common_data_sync_state.json"
ENV_CANDIDATES = (ROOT / ".env", ROOT.parent.parent / "parsers" / ".env")
METADATA_TIMEOUT = 10


def db_values() -> dict[str, str]:
    for path in ENV_CANDIDATES:
        values = dotenv_values(path)
        required = ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB")
        if all(values.get(key) for key in required):
            candidate = {
                "user": str(values["POSTGRES_USER"]),
                "password": str(values["POSTGRES_PASSWORD"]),
                "host": str(values["POSTGRES_HOST"]),
                "port": int(values["POSTGRES_PORT"]),
                "dbname": str(values["POSTGRES_DB"]),
            }
            try:
                with psycopg2.connect(**candidate, connect_timeout=5, options="-c default_transaction_read_only=on -c statement_timeout=3000") as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT to_regclass('public.common_data')")
                        if cur.fetchone()[0] == "common_data":
                            return candidate
            except psycopg2.Error:
                continue
    raise RuntimeError("PostgreSQL configuration is unavailable")


def connect(values: dict[str, str], readonly: bool = False):
    options = "-c statement_timeout=30000"
    if readonly:
        options += " -c default_transaction_read_only=on"
    return psycopg2.connect(**values, connect_timeout=5, options=options)


def current_names() -> list[str]:
    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    return sorted({normalize_item_name(record.get("display_name", "")) for record in payload["items"].values() if record.get("display_name")})


def representative_assets() -> dict[str, dict[str, str]]:
    """Use the latest local enriched sale as one representative asset per name."""
    import glob
    import pandas as pd

    result: dict[str, dict[str, str]] = {}
    for filename in glob.glob(str(DATA / "sales_enriched" / "*.csv")):
        try:
            frame = pd.read_csv(filename, usecols=["sale_date", "name", "token_id", "item_url"])
        except Exception:
            continue
        for row in frame.dropna(subset=["name", "item_url", "token_id"]).to_dict("records"):
            name = normalize_item_name(row["name"])
            parsed = urlparse(str(row["item_url"]))
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) < 2:
                continue
            candidate = {"name": name, "contract": parts[-2], "token_id": str(row["token_id"]), "sale_date": str(row.get("sale_date", ""))}
            if name not in result or candidate["sale_date"] > result[name].get("sale_date", ""):
                result[name] = candidate
    return result


def fetch_metadata(asset: dict[str, str], session: requests.Session | None = None) -> dict[str, str]:
    client = session or requests.Session()
    url = f"https://metadata.gunzchain.io/api/v1/nft/{asset['contract']}/{asset['token_id']}"
    response = client.get(url, timeout=METADATA_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    attrs = {str(item.get("trait_type", "")).strip().casefold(): item.get("value") for item in payload.get("attributes", []) if isinstance(item, dict)}
    return {
        "name": normalize_item_name(payload.get("name") or asset["name"]),
        "image": str(payload.get("image") or "").strip(),
        "class": str(attrs.get("class") or "").strip(),
        "type": str(attrs.get("type") or "").strip(),
    }


def read_state() -> dict[str, dict[str, str]]:
    if not STATE.exists():
        return {}
    payload = json.loads(STATE.read_text(encoding="utf-8"))
    return payload.get("items", {}) if isinstance(payload, dict) else {}


def publish_state(items: dict[str, dict[str, str]]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "items": dict(sorted(items.items()))}
    fd, temporary = tempfile.mkstemp(prefix=".common_data_sync_state.", suffix=".tmp", dir=DATA)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, STATE)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def fetch_common_rows(conn) -> list[tuple[str, str | None, str | None, str | None]]:
    with conn.cursor() as cur:
        cur.execute("SELECT name, image, class, type FROM public.common_data ORDER BY name")
        return cur.fetchall()


def repair_normalized_names(conn, rows) -> int:
    collisions = normalization_collisions(row[0] for row in rows)
    if collisions:
        raise RuntimeError(f"normalization collisions detected: {len(collisions)}")
    repaired = 0
    with conn.cursor() as cur:
        for name, image, class_value, type_value in rows:
            clean = normalize_item_name(name)
            if clean != name:
                cur.execute("UPDATE public.common_data SET name = %s WHERE name = %s", (clean, name))
                repaired += cur.rowcount
    return repaired


def upsert_metadata(conn, metadata: dict[str, str]) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO public.common_data (name, image, class, type) VALUES (%s, %s, %s, %s)
               ON CONFLICT (name) DO UPDATE SET
                 image = COALESCE(NULLIF(EXCLUDED.image, ''), common_data.image),
                 class = COALESCE(NULLIF(EXCLUDED.class, ''), common_data.class),
                 type = COALESCE(NULLIF(EXCLUDED.type, ''), common_data.type)
               RETURNING (xmax = 0) AS inserted""",
            (metadata["name"], metadata.get("image", ""), metadata.get("class", ""), metadata.get("type", "")),
        )
        return "inserted" if cur.fetchone()[0] else "updated"


def refresh_class_snapshot() -> None:
    python_exe = ROOT.parent.parent / ".venv" / "Scripts" / "python.exe"
    subprocess.run([os.fspath(python_exe), os.fspath(ROOT / "scripts" / "refresh_item_class_snapshot.py")], cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def run(limit: int = MAX_METADATA_FETCHES_PER_RUN) -> dict[str, int]:
    values = db_values()
    assets = representative_assets()
    names = current_names()
    with connect(values, readonly=False) as conn:
        rows = fetch_common_rows(conn)
        repaired = repair_normalized_names(conn, rows)
        existing = {normalize_item_name(row[0]) for row in rows}
        state = read_state()
        targets = select_reconciliation_targets(names, existing, state, limit)
        counters = Counter()
        session = requests.Session()
        for name in targets:
            asset = assets.get(name)
            if not asset:
                counters["no_representative_asset"] += 1
                continue
            try:
                metadata = fetch_metadata(asset, session)
                if normalize_item_name(metadata.get("name")) != name:
                    counters["metadata_name_mismatch"] += 1
                    continue
                action = upsert_metadata(conn, metadata)
                state[name] = {"last_success_at": datetime.now(timezone.utc).isoformat(), "representative_contract": asset["contract"], "representative_token_id": asset["token_id"], "last_metadata_status": "ok"}
                counters[action] += 1
            except requests.RequestException:
                counters["token_uri_failure"] += 1
            except (ValueError, KeyError):
                counters["invalid_metadata"] += 1
        conn.commit()
    publish_state(state)
    if counters.get("inserted", 0) or counters.get("updated", 0) or repaired:
        refresh_class_snapshot()
    counters["normalization_fixed"] = repaired
    counters["targets"] = len(targets)
    counters["representative_found"] = sum(1 for name in targets if name in assets)
    return dict(counters)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=MAX_METADATA_FETCHES_PER_RUN)
    args = parser.parse_args()
    if args.limit < 0 or args.limit > MAX_METADATA_FETCHES_PER_RUN:
        parser.error(f"--limit must be between 0 and {MAX_METADATA_FETCHES_PER_RUN}")
    print("COMMON_DATA_RECONCILIATION", run(args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
