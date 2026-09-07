"""Manual, sequential GUNZscope batch refresh with atomic JSON publication."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from collections import Counter
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
from gunzscope_supply import ATTRIBUTION, provider_lookup_pair, validate_snapshot, valid_supply  # noqa: E402

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def _retained_record(previous_record, outcome, now):
    retained = dict(previous_record) if isinstance(previous_record, dict) else {}
    if valid_supply(retained.get("supply")):
        retained["last_good_supply"] = retained.get("last_good_supply", retained["supply"])
    retained["status"] = "stale" if outcome in {"transport_error", "rate_limit", "server_error"} else "unavailable"
    retained["last_refresh_outcome"] = outcome
    retained["last_attempt_at"] = now
    return retained


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
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK_PATH.open("a+b")
    try:
        handle.seek(0)
        if handle.read(1) == b"":
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if sys.platform == "win32":
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                handle.close()
                return None
        else:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                handle.close()
                return None
        return handle
    except OSError:
        handle.close()
        return None


def release_lock(handle):
    if handle:
        try:
            handle.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


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
    candidates = result.get("items", []) if isinstance(result, dict) else None
    now = timestamp()
    def failure(outcome):
        item = _retained_record(previous_record, outcome, now)
        item.update({"request_name": name, "request_rarity": rarity})
        return item, outcome
    if not isinstance(candidates, list):
        return failure("invalid_payload")
    if not candidates:
        return failure("empty_result")
    if len(candidates) > 1:
        return failure("multiple_candidates")
    candidate = candidates[0] if len(candidates) == 1 else None
    if not isinstance(candidate, dict):
        return failure("invalid_payload")
    if candidate.get("itemName") != name:
        return failure("name_mismatch")
    if candidate.get("rarity") != rarity:
        return failure("rarity_mismatch")
    valid = (isinstance(candidate, dict) and candidate.get("itemName") == name
             and candidate.get("rarity") == rarity
             and isinstance(candidate.get("activeMints"), int)
             and not isinstance(candidate.get("activeMints"), bool)
             and candidate["activeMints"] >= 0)
    if valid:
        return {"request_name": name, "request_rarity": rarity,
                "provider_item_name": candidate["itemName"], "provider_rarity": candidate["rarity"],
                "supply": candidate["activeMints"], "provider_updated_at": wrapper_updated_at,
                "fetched_at": now, "last_attempt_at": now,
                "last_refresh_outcome": "ok", "status": "ok"}, "ok"
    return failure("invalid_payload")


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
    outcomes = Counter()
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
            except GunzscopeError as exc:
                payload = None
                message = str(exc).lower()
                batch_outcome = "rate_limit" if "rate limit" in message or "429" in message else "server_error" if "server error" in message or "http 5" in message else "transport_error"
            results = payload.get("results", {}) if payload else {}
            for record in batch:
                key = record["item_key"]
                name, rarity = provider_lookup_pair(record["display_name"], record["rarity"])
                result = results.get(f"{name}::{rarity}") if payload else None
                if payload is None:
                    outcome = batch_outcome
                    item = _retained_record(previous_items.get(key), outcome, timestamp())
                    item.update({"request_name": name, "request_rarity": rarity})
                else:
                    item, outcome = build_item_record(record, result, previous_items.get(key), payload.get("updatedAt"))
                items[key] = item
                outcomes[outcome] += 1
            if batch_no + 1 < len(batches):
                time.sleep(max(0.0, args.interval))
        publish({"schema_version": 1, "source": "gunzscope", "snapshot_fetched_at": timestamp(), "attribution": ATTRIBUTION, "items": items})
        print(f"FULL_REFRESH PASS items={len(records)} batches={len(batches)} outcomes={dict(sorted(outcomes.items()))}")
        return 0
    finally:
        release_lock(lock)


if __name__ == "__main__":
    raise SystemExit(main())
