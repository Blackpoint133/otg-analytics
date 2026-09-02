"""Read-only current Supply snapshot and dense scarcity rank helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data_opensea_sales"
SNAPSHOT_PATH = DATA_DIR / "gunzscope_supply_snapshot.json"
ATTRIBUTION = {"text": "Data by GUNZscope", "url": "https://gunzscope.xyz", "logoUrl": "https://gunzscope.xyz/brand/gunzscope-mark-mono.svg"}
VALID_STATUSES = {"ok", "stale", "unavailable", "unmapped"}


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


def get_item_supply(item_key: str, snapshot=None):
    data = snapshot if snapshot is not None else read_current_snapshot()
    record = data.get("items", {}).get(item_key) if data else None
    if isinstance(record, dict) and record.get("status") in {"ok", "stale"} and valid_supply(record.get("supply")):
        return record
    return None


def dense_supply_ranks(snapshot):
    if not snapshot or not isinstance(snapshot.get("items"), Mapping):
        return {}
    valid = [(key, record["supply"]) for key, record in snapshot["items"].items() if isinstance(record, Mapping) and record.get("status") in {"ok", "stale"} and valid_supply(record.get("supply"))]
    rank_by_value = {value: index + 1 for index, value in enumerate(sorted({value for _, value in valid}))}
    return {key: rank_by_value[value] for key, value in valid}


def get_item_supply_with_rank(item_key: str, snapshot=None):
    data = snapshot if snapshot is not None else read_current_snapshot()
    return get_item_supply(item_key, data), dense_supply_ranks(data).get(item_key)
