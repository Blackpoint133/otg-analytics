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
from gunzscope_supply import ATTRIBUTION, provider_lookup_pair, validate_snapshot  # noqa: E402


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def load_catalog():
    records = list(json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["items"].values())
    if len({r["item_key"] for r in records}) != len(records):
        raise ValueError("duplicate item_key")
    return records


def mapping_dry_run(records):
    original_anomalies = 0
    normalized_pairs = []
    invalid = 0
    for record in records:
        original_name, original_rarity = record.get("display_name"), record.get("rarity")
        name, rarity = provider_lookup_pair(original_name, original_rarity)
        original_anomalies += int(name != str(original_name) or rarity != str(original_rarity))
        if name and rarity:
            normalized_pairs.append((name, rarity))
        else:
            invalid += 1
    duplicates = len(normalized_pairs) - len(set(normalized_pairs))
    if duplicates:
        raise ValueError(f"normalized request pair collision: {duplicates}")
    return {"items": len(records), "original_whitespace_anomalies": original_anomalies,
            "normalized_pairs": len(normalized_pairs), "duplicates": duplicates,
            "invalid": invalid, "batches": (len(records) + MAX_BATCH_ITEMS - 1) // MAX_BATCH_ITEMS}


def valid_request_records(records):
    valid = []
    for record in records:
        name, rarity = provider_lookup_pair(record.get("display_name"), record.get("rarity"))
        if name and rarity:
            valid.append(record)
    return valid


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


def build_item_record(record, result, previous_record=None, wrapper_updated_at=None):
    key = record["item_key"]
    name, rarity = provider_lookup_pair(record["display_name"], record["rarity"])
    candidates = result.get("items", []) if isinstance(result, dict) else []
    candidate = candidates[0] if len(candidates) == 1 else None
    valid = (isinstance(candidate, dict) and candidate.get("itemName") == name
             and candidate.get("rarity") == rarity
             and isinstance(candidate.get("activeMints"), int)
             and not isinstance(candidate.get("activeMints"), bool)
             and candidate["activeMints"] >= 0)
    if valid:
        return {"request_name": name, "request_rarity": rarity,
                "provider_item_name": candidate["itemName"], "provider_rarity": candidate["rarity"],
                "supply": candidate["activeMints"], "provider_updated_at": wrapper_updated_at,
                "fetched_at": timestamp(), "status": "ok"}, "ok"
    if (isinstance(previous_record, dict) and previous_record.get("status") in {"ok", "stale"}
            and isinstance(previous_record.get("supply"), int) and previous_record["supply"] >= 0):
        retained = dict(previous_record)
        retained["status"] = "stale"
        return retained, "stale"
    return {"request_name": name, "request_rarity": rarity, "fetched_at": timestamp(),
            "status": "unavailable"}, "mismatch" if candidates else "empty"


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
    mapping = mapping_dry_run(records)
    batches = list(chunks(valid_request_records(records)))
    if args.dry_run:
        print("OFFLINE_MAPPING_DRY_RUN PASS " + " ".join(f"{k}={v}" for k, v in mapping.items()))
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
        for record in records:
            name, rarity = provider_lookup_pair(record.get("display_name"), record.get("rarity"))
            if not name or not rarity:
                items[record["item_key"]] = {"request_name": name, "request_rarity": rarity,
                                              "fetched_at": timestamp(), "status": "unavailable"}
        for batch_no, batch in enumerate(batches):
            requests_items = [{"name": provider_lookup_pair(r["display_name"], r["rarity"])[0],
                               "rarity": provider_lookup_pair(r["display_name"], r["rarity"])[1]} for r in batch]
            try:
                payload = fetch_batch(requests_items)
            except GunzscopeError:
                payload = None
            results = payload.get("results", {}) if payload else {}
            for record in batch:
                key = record["item_key"]
                name, rarity = provider_lookup_pair(record["display_name"], record["rarity"])
                result = results.get(f"{name}::{rarity}")
                item, outcome = build_item_record(record, result, previous_items.get(key), payload.get("updatedAt") if payload else None)
                items[key] = item
                mapped += outcome == "ok"
                stale += outcome == "stale"
                empty += outcome == "empty"
                mismatch += outcome == "mismatch"
            if batch_no + 1 < len(batches):
                time.sleep(max(0.0, args.interval))
        publish({"schema_version": 1, "source": "gunzscope", "snapshot_fetched_at": timestamp(), "attribution": ATTRIBUTION, "items": items})
        print(f"FULL_REFRESH PASS items={len(records)} batches={len(batches)} mapped_ok={mapped} empty={empty} mismatches={mismatch} stale={stale}")
        return 0
    finally:
        release_lock(lock)


if __name__ == "__main__":
    raise SystemExit(main())
