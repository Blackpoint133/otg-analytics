"""Manual, sequential GUNZscope batch refresh with atomic JSON publication."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "streamlit_opensea_sales"
DATA_DIR = APP_DIR / "data_opensea_sales"
CATALOG_PATH = DATA_DIR / "items_index.json"
SNAPSHOT_PATH = DATA_DIR / "gunzscope_supply_snapshot.json"
LOCK_PATH = DATA_DIR / "gunzscope_supply_refresh.lock"
sys.path.insert(0, str(APP_DIR))
from gunzscope_client import MAX_BATCH_ITEMS, GunzscopeError, fetch_batch  # noqa: E402
from gunzscope_supply import ATTRIBUTION, validate_snapshot  # noqa: E402


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def load_catalog():
    records = list(json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["items"].values())
    if len({r["item_key"] for r in records}) != len(records):
        raise ValueError("duplicate item_key")
    pairs = [(r["display_name"], r["rarity"]) for r in records]
    if len(set(pairs)) != len(pairs) or any(not n.strip() or not q.strip() for n, q in pairs):
        raise ValueError("invalid or duplicate request pair")
    return records


def chunks(values, size=MAX_BATCH_ITEMS):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def acquire_lock():
    try:
        return LOCK_PATH.open("x", encoding="ascii")
    except FileExistsError:
        return None


def release_lock(handle):
    if handle:
        handle.close()
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass


def load_previous():
    if not SNAPSHOT_PATH.exists():
        return None
    try:
        return validate_snapshot(json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def publish(payload):
    validate_snapshot(payload)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="gunzscope_supply_", suffix=".tmp", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as output:
            json.dump(payload, output, ensure_ascii=False, indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_name, SNAPSHOT_PATH)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit-items", type=int, default=0)
    parser.add_argument("--interval", type=float, default=1.52)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    records = load_catalog()
    if args.limit_items:
        records = records[:max(0, args.limit_items)]
    batches = list(chunks(records))
    if args.dry_run:
        print(f"OFFLINE_MAPPING_DRY_RUN PASS items={len(records)} pairs={len(records)} batches={len(batches)} duplicates=0")
        return 0
    if not os.getenv("API_GUNZSCOPE", "").strip():
        print("WAITING_FOR_STAGING_GUNZSCOPE_KEY", file=sys.stderr)
        return 0
    lock = acquire_lock()
    if lock is None:
        print("GUNZscope refresh already running; exiting")
        return 0
    previous = load_previous()
    previous_items = previous.get("items", {}) if previous else {}
    items = {}
    mapped = empty = mismatch = stale = 0
    try:
        for batch_no, batch in enumerate(batches):
            requests_items = [{"name": r["display_name"], "rarity": r["rarity"]} for r in batch]
            try:
                payload = fetch_batch(requests_items)
            except GunzscopeError:
                payload = None
            results = payload.get("results", {}) if payload else {}
            for record in batch:
                key, name, rarity = record["item_key"], record["display_name"], record["rarity"]
                result = results.get(f"{name}::{rarity}")
                candidates = result.get("items", []) if isinstance(result, dict) else []
                candidate = candidates[0] if len(candidates) == 1 else None
                valid = isinstance(candidate, dict) and candidate.get("itemName") == name and candidate.get("rarity") == rarity and isinstance(candidate.get("activeMints"), int) and not isinstance(candidate.get("activeMints"), bool) and candidate["activeMints"] >= 0
                if valid:
                    items[key] = {"request_name": name, "request_rarity": rarity, "provider_item_name": name, "provider_rarity": rarity, "supply": candidate["activeMints"], "provider_updated_at": payload.get("updatedAt"), "fetched_at": timestamp(), "status": "ok"}
                    mapped += 1
                elif key in previous_items and previous_items[key].get("status") in {"ok", "stale"} and isinstance(previous_items[key].get("supply"), int):
                    items[key] = dict(previous_items[key]); items[key]["status"] = "stale"; stale += 1
                else:
                    items[key] = {"request_name": name, "request_rarity": rarity, "fetched_at": timestamp(), "status": "unavailable"}
                    empty += not candidates
                    mismatch += bool(candidates)
            if batch_no + 1 < len(batches):
                time.sleep(max(0.0, args.interval))
        publish({"schema_version": 1, "source": "gunzscope", "snapshot_fetched_at": timestamp(), "attribution": ATTRIBUTION, "items": items})
        print(f"FULL_REFRESH PASS items={len(records)} batches={len(batches)} mapped_ok={mapped} empty={empty} mismatches={mismatch} stale={stale}")
        return 0
    finally:
        release_lock(lock)


if __name__ == "__main__":
    raise SystemExit(main())
