from pathlib import Path
from typing import Any
import streamlit.components.v1 as components

_item_search = components.declare_component("otg_item_search", path=str(Path(__file__).parent / "item_search_component"))

def render_item_search(records: list[dict[str, str]], selected_item: str | None = None, selected_display_name: str | None = None, key: str = "item_search") -> dict[str, Any] | None:
    value = _item_search(records=records, selected_item=selected_item, selected_display_name=selected_display_name, default=None, key=key)
    if not isinstance(value, dict) or value.get("action") != "select" or not isinstance(value.get("event_id"), str) or not value["event_id"].strip() or not isinstance(value.get("item_key"), str) or not value["item_key"].strip():
        return None
    return value
