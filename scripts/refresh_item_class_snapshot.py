"""Publish a small local snapshot of public.common_data.class."""

from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "streamlit_opensea_sales" / "data_opensea_sales" / "item_class_snapshot.json"
ENV_CANDIDATES = (
    ROOT / ".env",
    ROOT.parent.parent / "data_streamlit" / "gaming_marketplace" / ".env",
    ROOT.parent.parent / "data_streamlit" / "opensea_sales" / ".env",
)


def _db_env() -> Path:
    for path in ENV_CANDIDATES:
        values = dotenv_values(path)
        if not all(values.get(key) for key in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB")):
            continue
        try:
            with psycopg2.connect(
                user=values["POSTGRES_USER"], password=values["POSTGRES_PASSWORD"],
                host=values["POSTGRES_HOST"], port=int(values["POSTGRES_PORT"]),
                dbname=values["POSTGRES_DB"], connect_timeout=5,
                options="-c default_transaction_read_only=on -c statement_timeout=3000",
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT to_regclass('public.common_data')")
                    if cur.fetchone()[0] == "common_data":
                        return path
        except Exception:
            continue
    raise RuntimeError("PostgreSQL configuration is unavailable")


def _fetch_rows():
    values = dotenv_values(_db_env())
    params = {"user": values["POSTGRES_USER"], "password": values["POSTGRES_PASSWORD"], "host": values["POSTGRES_HOST"], "port": int(values["POSTGRES_PORT"]), "dbname": values["POSTGRES_DB"]}
    with psycopg2.connect(**params, connect_timeout=5,
                          options="-c default_transaction_read_only=on -c statement_timeout=10000") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name, class FROM public.common_data ORDER BY name")
            return cur.fetchall()


def build_snapshot(rows):
    names = [str(name) for name, _ in rows]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate common_data names returned")
    items = {name: {"class": str(value).strip()} for name, value in rows if value is not None and str(value).strip()}
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "public.common_data.class",
        "items": items,
    }


def publish_snapshot(payload, output: Path = OUTPUT):
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    rows = _fetch_rows()
    payload = build_snapshot(rows)
    publish_snapshot(payload)
    counts = Counter(record["class"] for record in payload["items"].values())
    print(f"SNAPSHOT_ROWS={len(payload['items'])}")
    print(f"CLASS_COUNTS={dict(sorted(counts.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
