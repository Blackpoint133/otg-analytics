"""Read-only access to current item metadata with a legacy class fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st


UNCLASSIFIED = "UNCLASSIFIED"


def snapshot_path() -> Path:
    return Path(__file__).resolve().parent / "data_opensea_sales" / "item_class_snapshot.json"


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


def class_mapping(snapshot: dict[str, Any] | None = None) -> dict[str, str]:
    payload = snapshot if snapshot is not None else read_item_class_snapshot()
    result: dict[str, str] = {}
    for name, record in (payload.get("items", {}) if isinstance(payload, dict) else {}).items():
        if isinstance(record, dict) and str(record.get("class") or "").strip():
            result[str(name)] = str(record["class"]).strip()
    return result


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
