"""Read-only access to current item metadata with a legacy class fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st


UNCLASSIFIED = "UNCLASSIFIED"
USER_FACING_CLASSES = (
    "Customization Item", "Weapon", "Weapon Attachment", "Weapon Skin",
    "Body Part", "Profile Customization", "Music", "Anomalies",
)


def snapshot_path() -> Path:
    return Path(__file__).resolve().parent / "data_opensea_sales" / "item_class_snapshot.json"


def overrides_path() -> Path:
    return Path(__file__).resolve().parent / "config" / "item_class_overrides.json"


def provider_supply_snapshot_path() -> Path:
    return Path(__file__).resolve().parent / "data_opensea_sales" / "gunzscope_supply_snapshot_v3_provider.json"


@st.cache_data(show_spinner=False)
def load_item_class_snapshot(path_string: str, mtime_ns: int) -> dict[str, Any]:
    del mtime_ns
    try:
        payload = json.loads(Path(path_string).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"schema_version": 1, "source": "public.item_metadata_current.class + public.common_data.class fallback", "items": {}}
    items = payload.get("items") if isinstance(payload, dict) else {}
    return payload if isinstance(items, dict) else {"schema_version": 1, "items": {}}


def read_item_class_snapshot() -> dict[str, Any]:
    path = snapshot_path()
    try:
        mtime_ns = path.stat().st_mtime_ns
    except OSError:
        mtime_ns = 0
    return load_item_class_snapshot(str(path), mtime_ns)


def source_class_mapping(snapshot: dict[str, Any] | None = None) -> dict[str, str]:
    payload = snapshot if snapshot is not None else read_item_class_snapshot()
    result: dict[str, str] = {}
    for name, record in (payload.get("items", {}) if isinstance(payload, dict) else {}).items():
        if isinstance(record, dict) and str(record.get("class") or "").strip():
            result[str(name)] = str(record["class"]).strip()
    return result


@st.cache_data(show_spinner=False)
def load_item_class_overrides(path_string: str, mtime_ns: int) -> dict[str, dict[str, str]]:
    del mtime_ns
    try:
        payload = json.loads(Path(path_string).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict) or payload.get("schema_version") != 1 or not isinstance(payload.get("overrides"), dict):
        return {}
    valid: dict[str, dict[str, str]] = {}
    for name, entry in payload["overrides"].items():
        if not isinstance(name, str) or not name.strip() or not isinstance(entry, dict):
            continue
        class_name = entry.get("class")
        if not isinstance(class_name, str) or not class_name.strip():
            continue
        reason = entry.get("reason", "")
        if reason is not None and not isinstance(reason, str):
            continue
        valid[name] = {"class": class_name.strip(), "reason": reason or ""}
    return valid


def read_item_class_overrides() -> dict[str, dict[str, str]]:
    path = overrides_path()
    try:
        mtime_ns = path.stat().st_mtime_ns
    except OSError:
        mtime_ns = 0
    return load_item_class_overrides(str(path), mtime_ns)


def asset_key_family_mapping(snapshot: dict[str, Any] | None = None) -> dict[str, str]:
    """Return only exact, source-proven provider assetKey-family classes."""
    source = source_class_mapping(snapshot)
    overrides = read_item_class_overrides()
    try:
        provider = json.loads(provider_supply_snapshot_path().read_text(encoding="utf-8")).get("provider_items", {})
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}
    evidence: dict[str, set[str]] = {}
    for record in provider.values():
        if not isinstance(record, dict) or record.get("ranking_eligible") is not True:
            continue
        name = record.get("provider_item_name")
        asset_key = record.get("provider_asset_key")
        if not isinstance(name, str) or not isinstance(asset_key, str) or name in overrides:
            continue
        class_name = source.get(name)
        if class_name:
            evidence.setdefault(asset_key.split("_", 1)[0], set()).add(class_name)
    return {family: next(iter(classes)) for family, classes in evidence.items() if len(classes) == 1}


def effective_class_mapping(snapshot: dict[str, Any] | None = None) -> dict[str, str]:
    result = dict(source_class_mapping(snapshot))
    family_classes = asset_key_family_mapping(snapshot)
    try:
        provider = json.loads(provider_supply_snapshot_path().read_text(encoding="utf-8")).get("provider_items", {})
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        provider = {}
    for record in provider.values():
        if isinstance(record, dict) and record.get("provider_item_name") not in result:
            asset_key = record.get("provider_asset_key")
            family = asset_key.split("_", 1)[0] if isinstance(asset_key, str) else ""
            if family in family_classes:
                result[record["provider_item_name"]] = family_classes[family]
    for name, entry in read_item_class_overrides().items():
        result[name] = entry["class"]
    return result


def class_mapping(snapshot: dict[str, Any] | None = None) -> dict[str, str]:
    """Return the effective opensea_sales presentation classification."""
    return effective_class_mapping(snapshot)


def trim_alias_mapping(snapshot: dict[str, Any] | None = None) -> tuple[dict[str, str], set[str]]:
    """Return only unambiguous outer-trim aliases and their collisions."""
    mapping = class_mapping(snapshot)
    candidates: dict[str, set[str]] = {}
    for name, class_name in mapping.items():
        trimmed = name.strip()
        candidates.setdefault(trimmed, set()).add(class_name)
    aliases = {name: next(iter(classes)) for name, classes in candidates.items() if len(classes) == 1}
    collisions = {name for name, classes in candidates.items() if len(classes) > 1}
    return aliases, collisions


def class_for_name(name: str, snapshot: dict[str, Any] | None = None) -> str:
    raw_name = str(name)
    exact = class_mapping(snapshot)
    if raw_name in exact:
        return exact[raw_name]
    trimmed = raw_name.strip()
    if trimmed != raw_name:
        aliases, collisions = trim_alias_mapping(snapshot)
        if trimmed not in collisions and trimmed in aliases:
            return aliases[trimmed]
    return UNCLASSIFIED


def class_options(catalog_names: list[str], snapshot: dict[str, Any] | None = None) -> list[str]:
    resolved = [class_for_name(name, snapshot) for name in catalog_names]
    values = {class_name for class_name in resolved if class_name != UNCLASSIFIED}
    if UNCLASSIFIED in resolved:
        values.add(UNCLASSIFIED)
    return ["ALL CLASSES", *sorted(values, key=str.casefold)]
