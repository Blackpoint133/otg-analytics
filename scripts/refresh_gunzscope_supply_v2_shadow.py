"""One-shot, shadow-only GUNZscope v2 refresh keyed by provider itemId."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import numbers
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "streamlit_opensea_sales"
DATA_DIR = APP_DIR / "data_opensea_sales"
CATALOG_PATH = DATA_DIR / "items_index.json"
V1_PATH = DATA_DIR / "gunzscope_supply_snapshot.json"
SHADOW_PATH = DATA_DIR / "gunzscope_supply_snapshot_v2_shadow.json"
sys.path.insert(0, str(APP_DIR))
from gunzscope_client import MAX_BATCH_ITEMS, GunzscopeError, fetch_batch  # noqa: E402


def now():
    return datetime.now(timezone.utc).isoformat()


def chunks(values, size=MAX_BATCH_ITEMS):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def load_catalog():
    return list(json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["items"].values())


def classify(record, candidates):
    if isinstance(candidates, dict):
        candidates = candidates.get("items")
    if not isinstance(candidates, list) or not candidates:
        return {"mapping_status": "UNAVAILABLE"}
    if len(candidates) != 1 or not isinstance(candidates[0], dict):
        return {"mapping_status": "INVALID"}
    c = candidates[0]
    requested_name, requested_rarity = str(record.get("display_name", "")).strip(), str(record.get("rarity", "")).strip()
    if c.get("itemName") != requested_name or not isinstance(c.get("itemName"), str) or not c["itemName"].strip() or not isinstance(c.get("rarity"), str) or not c["rarity"].strip() or not isinstance(c.get("itemId"), str) or not c["itemId"].strip():
        return {"mapping_status": "INVALID"}
    supply = c.get("activeMints")
    if not isinstance(supply, int) or isinstance(supply, bool) or supply < 0:
        return {"mapping_status": "INVALID_PROVIDER_DATA"}
    if c.get("rarity") != requested_rarity and c.get("matchedVia") not in {"rarityHistory", "retired", "history"}:
        return {"mapping_status": "INVALID"}
    return {"requested_name": requested_name, "requested_rarity": requested_rarity,
            "provider_item_id": c["itemId"], "returned_name": c.get("itemName"),
            "returned_rarity": c.get("rarity"), "queried_rarity": c.get("queriedRarity"),
            "matched_via": c.get("matchedVia"),
            "mapping_status": "RETIRED_RARITY_RESOLVED" if c.get("rarity") != requested_rarity else "DIRECT_CURRENT",
            "candidate": c}


def build_shadow(records, payloads):
    mappings, provider_items = {}, {}
    candidates_by_id = {}
    for record, candidates in zip(records, payloads):
        result = classify(record, candidates)
        candidate = result.pop("candidate", None)
        key = record["item_key"]
        if candidate:
            candidates_by_id.setdefault(result["provider_item_id"], []).append((key, candidate))
            provider_items.setdefault(result["provider_item_id"], {
                "provider_item_id": result["provider_item_id"], "provider_asset_key": candidate.get("assetKey"),
                "provider_item_name": candidate.get("itemName"), "provider_rarity": candidate.get("rarity"),
                "raw_active_mints": candidate.get("activeMints"), "burns": candidate.get("burns"),
                "provider_updated_at": None, "fetched_at": now(), "status": "ok",
            })
        result.pop("provider_item_id", None) if result.get("mapping_status") not in {"DIRECT_CURRENT", "RETIRED_RARITY_RESOLVED"} else None
        mappings[key] = result
    conflicts = []
    for provider_id, entries in candidates_by_id.items():
        fields = ("provider_item_id", "assetKey", "itemName", "rarity", "activeMints", "burns")
        signatures = {tuple(entry.get(field) for field in fields[1:]) for _, entry in entries}
        if len(signatures) > 1:
            conflicts.append({"provider_item_id": provider_id, "catalog_item_keys": [key for key, _ in entries], "values": [dict((field, entry.get(field)) for field in fields[1:]) for _, entry in entries]})
            provider_items.pop(provider_id, None)
            for key, _ in entries: mappings[key] = {"mapping_status": "PROVIDER_ITEM_CONFLICT", "provider_item_id": provider_id}
    return {"schema_version": 2, "source": "gunzscope", "snapshot_fetched_at": now(),
            "attribution": {"text": "Data by GUNZscope", "url": "https://gunzscope.xyz"},
            "provider_items": provider_items, "catalog_mappings": mappings, "provider_item_conflicts": conflicts}


def validate_shadow_v2(payload):
    if not isinstance(payload, dict) or payload.get("schema_version") != 2 or payload.get("source") != "gunzscope":
        raise ValueError("invalid v2 shadow header")
    providers, mappings = payload.get("provider_items"), payload.get("catalog_mappings")
    if not isinstance(providers, dict) or not isinstance(mappings, dict): raise ValueError("invalid v2 maps")
    for key, record in providers.items():
        if record.get("provider_item_id") != key or record.get("status") != "ok": raise ValueError("invalid provider identity/status")
        if not isinstance(record.get("provider_item_name"), str) or not record["provider_item_name"].strip() or not isinstance(record.get("provider_rarity"), str) or not record["provider_rarity"].strip(): raise ValueError("invalid provider identity fields")
        supply = record.get("raw_active_mints")
        if not isinstance(supply, int) or isinstance(supply, bool) or supply < 0: raise ValueError("invalid provider supply")
    for mapping in mappings.values():
        status = mapping.get("mapping_status")
        if status in {"DIRECT_CURRENT", "RETIRED_RARITY_RESOLVED"} and mapping.get("provider_item_id") not in providers: raise ValueError("dangling mapping")
    return payload


def publish(payload):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="gunzscope_v2_", suffix=".tmp", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as out:
            json.dump(payload, out, ensure_ascii=False, indent=2); out.write("\n"); out.flush(); os.fsync(out.fileno())
        os.replace(temp, SHADOW_PATH)
    finally:
        if os.path.exists(temp): os.unlink(temp)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--interval", type=float, default=60.0); args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    records = load_catalog(); valid = [r for r in records if str(r.get("display_name", "")).strip() and str(r.get("rarity", "")).strip()]
    if len({r["item_key"] for r in records}) != len(records): raise ValueError("duplicate catalog item_key")
    batches = list(chunks(valid))
    if args.dry_run:
        print(f"V2_SHADOW_DRY_RUN PASS CATALOG_ROWS={len(records)} BATCHES={len(batches)} HTTP_REQUESTS=0 SNAPSHOT_WRITES=0"); return 0
    payloads = []
    for batch in batches:
        response = fetch_batch([{"name": str(r["display_name"]).strip(), "rarity": str(r["rarity"]).strip()} for r in batch], resolve_retired=True)
        results = response.get("results", {})
        payloads.extend(results.get(f"{str(r['display_name']).strip()}::{str(r['rarity']).strip()}", []) for r in batch)
        if batch is not batches[-1]:
            time.sleep(max(0.0, args.interval))
    shadow = build_shadow(valid, payloads); validate_shadow_v2(shadow); publish(shadow)
    counts = Counter(v["mapping_status"] for v in shadow["catalog_mappings"].values())
    print(f"V2_SHADOW_REFRESH PASS CATALOG_ROWS={len(records)} MAPPED={sum(counts[k] for k in ('DIRECT_CURRENT','RETIRED_RARITY_RESOLVED'))} PROVIDER_ITEMS={len(shadow['provider_items'])} OUTCOMES={dict(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
