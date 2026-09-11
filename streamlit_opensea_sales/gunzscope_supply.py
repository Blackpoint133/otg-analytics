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
V3_PROVIDER_PATH = DATA_DIR / "gunzscope_supply_snapshot_v3_provider.json"
SUPPLY_PRESENTATION_OVERRIDES_PATH = Path(__file__).resolve().parent / "config" / "supply_presentation_overrides.json"
SUPPLY_RANK_EXCLUSIONS_PATH = Path(__file__).resolve().parent / "config" / "supply_rank_exclusions.json"
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


def _validate_supply_presentation_config(payload):
    if not isinstance(payload, dict) or payload.get("schema_version") != 1 or payload.get("purpose") != "opensea_sales presentation-only Supply canonicalization":
        raise ValueError("invalid Supply presentation config")
    groups, seen, result = payload.get("rename_groups"), set(), {}
    if not isinstance(groups, dict):
        raise ValueError("invalid Supply presentation groups")
    for name, group in groups.items():
        canonical, members = (group.get("canonical_provider_item_id"), group.get("member_provider_item_ids")) if isinstance(group, dict) else (None, None)
        if not isinstance(name, str) or not name.strip() or not isinstance(canonical, str) or not canonical.strip() or not isinstance(members, list) or len(members) < 2 or canonical not in members or group.get("strategy") != "sum_raw_supply" or any(not isinstance(pid, str) or not pid.strip() for pid in members) or len(set(members)) != len(members) or seen.intersection(members) or ("reason" in group and not isinstance(group["reason"], str)):
            raise ValueError("invalid Supply presentation group")
        seen.update(members)
        result[name] = {"canonical_provider_item_id": canonical, "member_provider_item_ids": tuple(members), "strategy": "sum_raw_supply"}
    return result


@st.cache_data(ttl=60, show_spinner=False)
def load_supply_presentation_config(path: str = str(SUPPLY_PRESENTATION_OVERRIDES_PATH), mtime: float | None = None):
    del mtime
    try:
        return _validate_supply_presentation_config(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def read_supply_presentation_config():
    try:
        mtime = SUPPLY_PRESENTATION_OVERRIDES_PATH.stat().st_mtime
    except OSError:
        return {}
    return load_supply_presentation_config(str(SUPPLY_PRESENTATION_OVERRIDES_PATH), mtime)


def _validate_supply_rank_exclusions(payload):
    if not isinstance(payload, dict) or payload.get("schema_version") != 1 or payload.get("purpose") != "opensea_sales presentation-only Supply rank exclusions":
        raise ValueError("invalid Supply rank exclusions config")
    entries = payload.get("excluded_provider_items")
    if not isinstance(entries, dict):
        raise ValueError("invalid Supply rank exclusions")
    result = {}
    for provider_id, entry in entries.items():
        if not isinstance(provider_id, str) or not provider_id.strip() or not isinstance(entry, dict):
            raise ValueError("invalid Supply rank exclusion entry")
        if not isinstance(entry.get("item_name"), str) or not entry["item_name"].strip() or not isinstance(entry.get("rarity"), str) or not entry["rarity"].strip():
            raise ValueError("invalid Supply rank exclusion identity")
        if "reason" in entry and not isinstance(entry["reason"], str):
            raise ValueError("invalid Supply rank exclusion reason")
        result[provider_id] = {"item_name": entry["item_name"].strip(), "rarity": entry["rarity"].strip(), "reason": entry.get("reason", "")}
    return result


@st.cache_data(ttl=60, show_spinner=False)
def load_supply_rank_exclusions(path: str = str(SUPPLY_RANK_EXCLUSIONS_PATH), mtime: float | None = None):
    del mtime
    try:
        return _validate_supply_rank_exclusions(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}


def read_supply_rank_exclusions():
    try:
        mtime = SUPPLY_RANK_EXCLUSIONS_PATH.stat().st_mtime
    except OSError:
        return {}
    return load_supply_rank_exclusions(str(SUPPLY_RANK_EXCLUSIONS_PATH), mtime)


def validated_supply_rank_exclusion_ids(snapshot):
    providers = snapshot.get("provider_items", {}) if isinstance(snapshot, dict) else {}
    valid = set()
    for provider_id, expected in read_supply_rank_exclusions().items():
        current = providers.get(provider_id)
        if isinstance(current, Mapping) and current.get("provider_item_name") == expected["item_name"] and current.get("provider_rarity") == expected["rarity"]:
            valid.add(provider_id)
    return valid


def build_v3_supply_presentation_index(snapshot, overrides=None):
    providers = snapshot.get("provider_items", {}) if isinstance(snapshot, dict) else {}
    groups = read_supply_presentation_config() if overrides is None else _validate_supply_presentation_config(overrides)
    canonical_by_member, suppressed, effective, members_by_canonical, invalid = {}, set(), {}, {}, set()
    for group in groups.values():
        members = group["member_provider_item_ids"]; canonical = group["canonical_provider_item_id"]
        if not all(pid in providers and providers[pid].get("ranking_eligible") is True and valid_supply(providers[pid].get("raw_active_mints")) for pid in members):
            invalid.add(canonical); continue
        members_by_canonical[canonical] = members
        effective[canonical] = sum(providers[pid]["raw_active_mints"] for pid in members)
        for pid in members:
            canonical_by_member[pid] = canonical
            if pid != canonical: suppressed.add(pid)
    for pid, record in providers.items():
        if record.get("ranking_eligible") is True and pid not in canonical_by_member:
            canonical_by_member[pid] = pid; effective[pid] = record.get("raw_active_mints"); members_by_canonical[pid] = (pid,)
    return {"canonical_by_member_provider_id": canonical_by_member, "suppressed_provider_ids": suppressed, "effective_supply_by_canonical_provider_id": effective, "members_by_canonical_provider_id": members_by_canonical, "invalid_groups": invalid}


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


def validate_snapshot_v3(payload):
    if not isinstance(payload, dict) or payload.get("schema_version") != 3 or payload.get("source") != "gunzscope":
        raise ValueError("invalid v3 header")
    scope = payload.get("provider_scope")
    if not isinstance(scope, Mapping) or scope.get("exclude_zero") is not True or scope.get("exclude_base") is not False or scope.get("sort") != "activeMints" or scope.get("order") != "asc":
        raise ValueError("invalid v3 provider scope")
    providers, mappings = payload.get("provider_items"), payload.get("catalog_mappings")
    if not isinstance(providers, dict) or not isinstance(mappings, dict) or not isinstance(payload.get("provider_item_conflicts", []), list):
        raise ValueError("invalid v3 maps")
    for key, record in providers.items():
        if not isinstance(key, str) or not isinstance(record, Mapping) or record.get("provider_item_id") != key:
            raise ValueError("invalid v3 provider identity")
        if not isinstance(record.get("provider_item_name"), str) or not record["provider_item_name"].strip() or not isinstance(record.get("provider_rarity"), str) or not record["provider_rarity"].strip():
            raise ValueError("invalid v3 provider fields")
        if record.get("status") not in {"ok", "catalog_only"} or not isinstance(record.get("ranking_eligible"), bool):
            raise ValueError("invalid v3 ranking eligibility")
        if (record["ranking_eligible"] and record.get("status") != "ok") or (not record["ranking_eligible"] and record.get("status") != "catalog_only"):
            raise ValueError("inconsistent v3 provider status")
        if not record["ranking_eligible"] and record.get("scope_reason") != "catalog_only_outside_current_rankings":
            raise ValueError("invalid v3 catalog-only scope reason")
        if not valid_supply(record.get("raw_active_mints")):
            raise ValueError("invalid v3 supply")
    statuses = {"DIRECT_CURRENT", "RETIRED_RARITY_RESOLVED", "AMBIGUOUS_CURRENT", "UNAVAILABLE", "INVALID"}
    for mapping in mappings.values():
        if not isinstance(mapping, Mapping) or mapping.get("mapping_status") not in statuses:
            raise ValueError("invalid v3 catalog mapping")
        if mapping.get("mapping_status") in {"DIRECT_CURRENT", "RETIRED_RARITY_RESOLVED"} and mapping.get("provider_item_id") not in providers:
            raise ValueError("dangling v3 mapping")
    return payload


@st.cache_data(ttl=60, show_spinner=False)
def load_snapshot_v3(path: str = str(V3_PROVIDER_PATH), mtime: float | None = None):
    del mtime
    try:
        return validate_snapshot_v3(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def read_snapshot_v3():
    try:
        mtime = V3_PROVIDER_PATH.stat().st_mtime
    except OSError:
        return None
    return load_snapshot_v3(str(V3_PROVIDER_PATH), mtime)


def selected_supply_source():
    requested = os.getenv("GUNZSCOPE_SUPPLY_SOURCE", "").strip().lower()
    if requested == "v3" and read_snapshot_v3():
        return "v3"
    if requested == "v3" and read_shadow_v2():
        return "v2"
    if requested == "v2" and read_shadow_v2():
        return "v2"
    return "v1"


def read_serving_snapshot():
    source = selected_supply_source()
    return read_snapshot_v3() if source == "v3" else (read_shadow_v2() if source == "v2" else read_current_snapshot())


def _v2_provider_for_item(item_key: str, snapshot):
    mapping = snapshot.get("catalog_mappings", {}).get(item_key, {}) if isinstance(snapshot, dict) else {}
    if mapping.get("mapping_status") not in {"DIRECT_CURRENT", "RETIRED_RARITY_RESOLVED"}:
        return None
    return snapshot.get("provider_items", {}).get(mapping.get("provider_item_id"))


def get_item_supply(item_key: str, snapshot=None):
    data = snapshot if snapshot is not None else read_serving_snapshot()
    if data and data.get("schema_version") in {2, 3}:
        record = _v2_provider_for_item(item_key, data)
        if record and (data.get("schema_version") == 2 or record.get("status") in {"ok", "catalog_only"}) and valid_supply(record.get("raw_active_mints")):
            if data.get("schema_version") == 3:
                idx = build_v3_supply_presentation_index(data)
                pid = idx["canonical_by_member_provider_id"].get(record["provider_item_id"], record["provider_item_id"])
                value = idx["effective_supply_by_canonical_provider_id"].get(pid, record["raw_active_mints"])
                return {"supply": value, "status": record.get("status", "ok"), "provider_item_id": record["provider_item_id"]}
            return {"supply": record["raw_active_mints"], "status": record.get("status", "ok"), "provider_item_id": record["provider_item_id"]}
        return None
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
    if snapshot.get("schema_version") == 3:
        providers = snapshot.get("provider_items")
        if not isinstance(providers, Mapping):
            return {}
        idx = build_v3_supply_presentation_index(snapshot)
        excluded = validated_supply_rank_exclusion_ids(snapshot)
        excluded_canonical = {idx["canonical_by_member_provider_id"].get(provider_id, provider_id) for provider_id in excluded}
        valid = [(key, value) for key, value in idx["effective_supply_by_canonical_provider_id"].items() if key not in excluded_canonical and valid_supply(value)]
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


def build_v3_canonical_index(snapshot):
    """Build the safe canonical local mapping for provider-wide rows."""
    groups = {}
    for item_key, mapping in (snapshot or {}).get("catalog_mappings", {}).items():
        if mapping.get("mapping_status") in {"DIRECT_CURRENT", "RETIRED_RARITY_RESOLVED"}:
            groups.setdefault(mapping.get("provider_item_id"), []).append((item_key, mapping.get("mapping_status")))
    canonical, aliases, ambiguous = {}, {}, set()
    for pid, entries in groups.items():
        direct = [key for key, status in entries if status == "DIRECT_CURRENT"]
        if len(direct) > 1 or (not direct and len(entries) != 1):
            ambiguous.add(pid); continue
        chosen = direct[0] if direct else entries[0][0]
        canonical[pid] = chosen
        aliases[pid] = [key for key, _ in entries if key != chosen]
    return {"canonical_by_provider_id": canonical, "aliases": aliases, "ambiguous_provider_ids": ambiguous}


def get_item_supply_with_rank(item_key: str, snapshot=None):
    data = snapshot if snapshot is not None else read_serving_snapshot()
    rank = dense_supply_ranks(data).get(item_key)
    if data and data.get("schema_version") in {2, 3}:
        mapping = data.get("catalog_mappings", {}).get(item_key, {})
        provider_id = mapping.get("provider_item_id")
        if data.get("schema_version") == 3:
            provider_id = build_v3_supply_presentation_index(data)["canonical_by_member_provider_id"].get(provider_id, provider_id)
        rank = dense_supply_ranks(data).get(provider_id)
    return get_item_supply(item_key, data), rank
