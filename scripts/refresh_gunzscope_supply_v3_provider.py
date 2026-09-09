"""Build the provider-wide GUNZscope v3 Supply snapshot."""
from __future__ import annotations
import argparse, json, os, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "streamlit_opensea_sales"
DATA = APP / "data_opensea_sales"
CATALOG = DATA / "items_index.json"
V2_PATH = DATA / "gunzscope_supply_snapshot_v2_shadow.json"
OUT = DATA / "gunzscope_supply_snapshot_v3_provider.json"
sys.path.insert(0, str(APP))
from gunzscope_client import fetch_batch, fetch_rankings, MAX_BATCH_ITEMS  # noqa: E402

def now(): return datetime.now(timezone.utc).isoformat()
def chunks(items):
    for i in range(0, len(items), MAX_BATCH_ITEMS): yield items[i:i + MAX_BATCH_ITEMS]

def classify(record, candidates):
    if isinstance(candidates, dict): candidates = candidates.get("items")
    if not isinstance(candidates, list) or len(candidates) != 1 or not isinstance(candidates[0], dict):
        return {"mapping_status": "UNAVAILABLE"}
    c = candidates[0]; name, rarity = str(record.get("display_name", "")).strip(), str(record.get("rarity", "")).strip()
    if c.get("itemName") != name or not isinstance(c.get("itemId"), str) or not c["itemId"].strip() or not isinstance(c.get("rarity"), str) or not c["rarity"].strip():
        return {"mapping_status": "INVALID"}
    if c.get("rarity") != rarity and c.get("matchedVia") not in {"rarityHistory", "retired", "history"}:
        return {"mapping_status": "INVALID"}
    return {"requested_name": name, "requested_rarity": rarity, "provider_item_id": c["itemId"],
            "returned_name": c.get("itemName"), "returned_rarity": c.get("rarity"),
            "queried_rarity": c.get("queriedRarity"), "matched_via": c.get("matchedVia"),
            "mapping_status": "RETIRED_RARITY_RESOLVED" if c.get("rarity") != rarity else "DIRECT_CURRENT"}

def provider_record(item, eligible=True, reason=None):
    out = {"provider_item_id": item.get("itemId"), "provider_item_name": item.get("itemName"),
           "provider_rarity": item.get("rarity"), "provider_asset_key": item.get("assetKey"),
           "provider_image_url": item.get("imageUrl"), "raw_active_mints": item.get("activeMints"),
           "ranking_eligible": eligible, "provider_rank_raw": item.get("rank"),
           "fetched_at": now(), "status": "ok" if eligible else "catalog_only"}
    if reason: out["scope_reason"] = reason
    return out

def build_payload(catalog, ranking_items, resolved):
    providers = {}; mappings = {}; conflicts = []
    for item in ranking_items:
        pid = item.get("itemId")
        if not isinstance(pid, str) or not pid.strip(): raise ValueError("ranking item lacks itemId")
        if pid in providers: raise ValueError("duplicate ranking provider itemId")
        if not isinstance(item.get("itemName"), str) or not item["itemName"].strip() or not isinstance(item.get("rarity"), str) or not item["rarity"].strip(): raise ValueError("invalid ranking identity")
        if not isinstance(item.get("activeMints"), int) or isinstance(item.get("activeMints"), bool) or item["activeMints"] < 0: raise ValueError("invalid ranking supply")
        providers[pid] = provider_record(item)
    exact = {}
    for pid, item in providers.items(): exact.setdefault((item["provider_item_name"], item["provider_rarity"]), []).append(pid)
    unmatched = []
    for record in catalog:
        pair = (str(record.get("display_name", "")).strip(), str(record.get("rarity", "")).strip())
        pids = exact.get(pair, [])
        if len(pids) == 1: mappings[record["item_key"]] = {"requested_name": pair[0], "requested_rarity": pair[1], "provider_item_id": pids[0], "returned_name": pair[0], "returned_rarity": pair[1], "matched_via": "current", "mapping_status": "DIRECT_CURRENT"}
        elif len(pids) > 1: mappings[record["item_key"]] = {"mapping_status": "AMBIGUOUS_CURRENT"}
        else: unmatched.append(record)
    for batch in chunks(unmatched):
        response = fetch_batch([{"name": str(r.get("display_name", "")).strip(), "rarity": str(r.get("rarity", "")).strip()} for r in batch], resolve_retired=True)
        for record in batch:
            key = record["item_key"]; pair = f"{str(record.get('display_name','')).strip()}::{str(record.get('rarity','')).strip()}"
            result = classify(record, response.get("results", {}).get(pair, [])); mappings[key] = result
            pid = result.get("provider_item_id")
            if result.get("mapping_status") in {"DIRECT_CURRENT", "RETIRED_RARITY_RESOLVED"} and pid and pid not in providers:
                candidates = response.get("results", {}).get(pair, [])
                if len(candidates) == 1 and isinstance(candidates[0], dict):
                    providers[pid] = provider_record(candidates[0], False, "catalog_only_outside_current_rankings")
    outside = [r for r in catalog if mappings.get(r["item_key"], {}).get("mapping_status") == "DIRECT_CURRENT" and mappings[r["item_key"]].get("provider_item_id") not in providers]
    for batch in chunks(outside):
        response = fetch_batch([{"name": str(r.get("display_name", "")).strip(), "rarity": str(r.get("rarity", "")).strip()} for r in batch])
        for record in batch:
            pair = f"{str(record.get('display_name','')).strip()}::{str(record.get('rarity','')).strip()}"
            candidates = response.get("results", {}).get(pair, [])
            if len(candidates) == 1 and isinstance(candidates[0], dict) and candidates[0].get("itemId"):
                providers[candidates[0]["itemId"]] = provider_record(candidates[0], False, "catalog_only_outside_current_rankings")
    if V2_PATH.exists():
        old = json.loads(V2_PATH.read_text(encoding="utf-8"))
        mapped_ids = {m.get("provider_item_id") for m in mappings.values() if m.get("mapping_status") in {"DIRECT_CURRENT", "RETIRED_RARITY_RESOLVED"}}
        for pid in mapped_ids - set(providers):
            old_record = old.get("provider_items", {}).get(pid)
            if isinstance(old_record, dict):
                providers[pid] = {"provider_item_id": pid, "provider_item_name": old_record.get("provider_item_name"), "provider_rarity": old_record.get("provider_rarity"), "provider_asset_key": old_record.get("provider_asset_key"), "provider_image_url": None, "raw_active_mints": old_record.get("raw_active_mints"), "ranking_eligible": False, "fetched_at": now(), "status": "catalog_only", "scope_reason": "catalog_only_outside_current_rankings"}
    return {"schema_version": 3, "source": "gunzscope", "snapshot_fetched_at": now(), "provider_scope": {"exclude_zero": True, "exclude_base": False, "sort": "activeMints", "order": "asc"}, "provider_items": providers, "catalog_mappings": mappings, "provider_item_conflicts": conflicts}

def publish(payload):
    DATA.mkdir(parents=True, exist_ok=True); fd, path = tempfile.mkstemp(prefix="gunzscope_v3_", suffix=".tmp", dir=DATA)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(payload, f, ensure_ascii=False, indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(path, OUT)
    finally:
        if os.path.exists(path): os.unlink(path)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a=ap.parse_args(); load_dotenv(ROOT/".env")
    catalog=list(json.loads(CATALOG.read_text(encoding="utf-8"))["items"].values())
    if a.dry_run:
        print(f"V3_PROVIDER_DRY_RUN PASS CATALOG_ROWS={len(catalog)} HTTP_REQUESTS=0 SNAPSHOT_WRITES=0"); return 0
    rankings=fetch_rankings(exclude_zero=True, exclude_base=False)["items"]; payload=build_payload(catalog, rankings, None)
    from gunzscope_supply import validate_snapshot_v3
    validate_snapshot_v3(payload); publish(payload)
    print(f"V3_PROVIDER_REFRESH PASS PROVIDER_ITEMS={len(payload['provider_items'])} CATALOG_ROWS={len(catalog)}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
