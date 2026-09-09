"""Read-only current Supply snapshot and dense scarcity rank helpers."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data_opensea_sales"
SNAPSHOT_PATH = DATA_DIR / "gunzscope_supply_snapshot.json"
V2_SHADOW_PATH = DATA_DIR / "gunzscope_supply_snapshot_v2_shadow.json"
ATTRIBUTION = {"text": "Data by GUNZscope", "url": "https://gunzscope.xyz", "logoUrl": "https://gunzscope.xyz/brand/gunzscope-mark-mono.svg"}
VALID_STATUSES = {"ok", "stale", "unavailable", "unmapped"}


def normalize_provider_lookup_name(value: Any) -> str:
    """Remove only outer whitespace at the GUNZscope lookup boundary."""
    return str(value).strip()


def normalize_provider_lookup_rarity(value: Any) -> str:
    """Remove only outer whitespace at the GUNZscope lookup boundary."""
    return str(value).strip()


def provider_lookup_pair(display_name: Any, rarity: Any) -> tuple[str, str]:
    return normalize_provider_lookup_name(display_name), normalize_provider_lookup_rarity(rarity)


def valid_supply(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_snapshot(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schema_version") != 1 or payload.get("source") != "gunzscope":
        raise ValueError("unsupported supply snapshot")
    attribution = payload.get("attribution")
    if not isinstance(attribution, Mapping) or attribution.get("text") != ATTRIBUTION["text"] or attribution.get("url") != ATTRIBUTION["url"]:
        raise ValueError("invalid attribution")
    if not isinstance(payload.get("items"), dict):
        raise ValueError("invalid items")
    for key, record in payload["items"].items():
        if not isinstance(key, str) or not isinstance(record, dict) or record.get("status") not in VALID_STATUSES:
            raise ValueError("invalid item record")
        if record["status"] in {"ok", "stale"} and not valid_supply(record.get("supply")):
            raise ValueError("invalid supply")
    return payload


@st.cache_data(ttl=60, show_spinner=False)
def load_snapshot(path: str = str(SNAPSHOT_PATH), mtime: float | None = None):
    del mtime
    target = Path(path)
    if not target.exists():
        return None
    try:
        return validate_snapshot(json.loads(target.read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def read_current_snapshot():
    try:
        mtime = SNAPSHOT_PATH.stat().st_mtime
    except OSError:
        return None
    return load_snapshot(str(SNAPSHOT_PATH), mtime)


def validate_shadow_v2(payload):
    if not isinstance(payload, dict) or payload.get("schema_version") != 2 or payload.get("source") != "gunzscope":
        raise ValueError("invalid v2 shadow header")
    providers, mappings = payload.get("provider_items"), payload.get("catalog_mappings")
    if not isinstance(providers, dict) or not isinstance(mappings, dict):
        raise ValueError("invalid v2 shadow maps")
    for key, record in providers.items():
        if not isinstance(record, dict) or record.get("provider_item_id") != key or record.get("status") != "ok":
            raise ValueError("invalid provider identity/status")
        if not isinstance(record.get("provider_item_name"), str) or not record["provider_item_name"].strip() or not isinstance(record.get("provider_rarity"), str) or not record["provider_rarity"].strip():
            raise ValueError("invalid provider identity fields")
        supply = record.get("raw_active_mints")
        if not isinstance(supply, int) or isinstance(supply, bool) or supply < 0:
            raise ValueError("invalid provider supply")
    for mapping in mappings.values():
        if not isinstance(mapping, dict):
            raise ValueError("invalid catalog mapping")
        if mapping.get("mapping_status") in {"DIRECT_CURRENT", "RETIRED_RARITY_RESOLVED"} and mapping.get("provider_item_id") not in providers:
            raise ValueError("dangling catalog mapping")
    return payload


@st.cache_data(ttl=60, show_spinner=False)
def load_shadow_v2(path: str = str(V2_SHADOW_PATH), mtime: float | None = None):
    del mtime
    try:
        return validate_shadow_v2(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def read_shadow_v2():
    try:
        mtime = V2_SHADOW_PATH.stat().st_mtime
    except OSError:
        return None
    return load_shadow_v2(str(V2_SHADOW_PATH), mtime)


def selected_supply_source():
    return "v2" if os.getenv("GUNZSCOPE_SUPPLY_SOURCE", "").strip().lower() == "v2" and read_shadow_v2() else "v1"


def read_serving_snapshot():
    return read_shadow_v2() if selected_supply_source() == "v2" else read_current_snapshot()


def _v2_provider_for_item(item_key: str, snapshot):
    mapping = snapshot.get("catalog_mappings", {}).get(item_key, {}) if isinstance(snapshot, dict) else {}
    if mapping.get("mapping_status") not in {"DIRECT_CURRENT", "RETIRED_RARITY_RESOLVED"}:
        return None
    return snapshot.get("provider_items", {}).get(mapping.get("provider_item_id"))


def get_item_supply(item_key: str, snapshot=None):
    data = snapshot if snapshot is not None else read_serving_snapshot()
    if data and data.get("schema_version") == 2:
        record = _v2_provider_for_item(item_key, data)
        return {"supply": record["raw_active_mints"], "status": "ok", "provider_item_id": record["provider_item_id"]} if record else None
    record = data.get("items", {}).get(item_key) if data else None
    if isinstance(record, dict) and record.get("status") in {"ok", "stale"} and valid_supply(record.get("supply")):
        return record
    return None


def dense_supply_ranks(snapshot):
    if not snapshot:
        return {}
    if snapshot.get("schema_version") == 2:
        providers = snapshot.get("provider_items")
        if not isinstance(providers, Mapping):
            return {}
        valid = [(key, record["raw_active_mints"]) for key, record in providers.items() if isinstance(record, Mapping) and record.get("status") == "ok" and valid_supply(record.get("raw_active_mints"))]
        rank_by_value = {value: index + 1 for index, value in enumerate(sorted({value for _, value in valid}))}
        return {key: rank_by_value[value] for key, value in valid}
    valid = [(key, record["supply"]) for key, record in snapshot["items"].items() if isinstance(record, Mapping) and record.get("status") in {"ok", "stale"} and valid_supply(record.get("supply"))]
    rank_by_value = {value: index + 1 for index, value in enumerate(sorted({value for _, value in valid}))}
    return {key: rank_by_value[value] for key, value in valid}


def build_v2_canonical_index(snapshot):
    """Return canonical catalog rows, aliases, and fail-safe ambiguities."""
    if not snapshot or snapshot.get("schema_version") != 2:
        return {"canonical_by_provider_id": {}, "aliases": {}, "ambiguous_provider_ids": set()}
    groups = {}
    for item_key, mapping in snapshot.get("catalog_mappings", {}).items():
        if not isinstance(mapping, Mapping) or mapping.get("mapping_status") not in {"DIRECT_CURRENT", "RETIRED_RARITY_RESOLVED"}:
            continue
        groups.setdefault(mapping.get("provider_item_id"), []).append((item_key, mapping))
    canonical, aliases, ambiguous = {}, {}, set()
    for provider_id, entries in groups.items():
        directs = [item_key for item_key, mapping in entries if mapping.get("mapping_status") == "DIRECT_CURRENT"]
        if len(directs) > 1 or (not directs and len(entries) != 1):
            ambiguous.add(provider_id)
            continue
        chosen = directs[0] if directs else entries[0][0]
        canonical[provider_id] = chosen
        aliases[provider_id] = [item_key for item_key, _ in entries if item_key != chosen]
    return {"canonical_by_provider_id": canonical, "aliases": aliases, "ambiguous_provider_ids": ambiguous}


def get_item_supply_with_rank(item_key: str, snapshot=None):
    data = snapshot if snapshot is not None else read_serving_snapshot()
    rank = dense_supply_ranks(data).get(item_key)
    if data and data.get("schema_version") == 2:
        mapping = data.get("catalog_mappings", {}).get(item_key, {})
        provider_id = mapping.get("provider_item_id")
        rank = dense_supply_ranks(data).get(provider_id)
    return get_item_supply(item_key, data), rank
