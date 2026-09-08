"""Read-only access to the prepared public.common_data.class snapshot."""

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
        return {"schema_version": 1, "source": "public.common_data.class", "items": {}}
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


def class_for_name(name: str, snapshot: dict[str, Any] | None = None) -> str:
    return class_mapping(snapshot).get(str(name), UNCLASSIFIED)


def class_options(catalog_names: list[str], snapshot: dict[str, Any] | None = None) -> list[str]:
    mapping = class_mapping(snapshot)
    values = {mapping[name] for name in catalog_names if name in mapping}
    if any(name not in mapping for name in catalog_names):
        values.add(UNCLASSIFIED)
    return ["ALL CLASSES", *sorted(values, key=str.casefold)]
