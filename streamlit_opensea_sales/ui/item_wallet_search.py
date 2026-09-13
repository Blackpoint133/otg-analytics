from pathlib import Path
from typing import Any
import streamlit.components.v1 as components
_component = components.declare_component("otg_item_wallet_search", path=str(Path(__file__).parent / "item_wallet_search_component"))
def render_item_wallet_search(records: list[dict[str, Any]], selected_wallet=None, selected_display_name=None, key="item_wallet_search"):
    value = _component(records=records, selected_wallet=selected_wallet, selected_display_name=selected_display_name, default=None, key=key)
    if not isinstance(value, dict) or value.get("action") not in {"select", "clear"} or not isinstance(value.get("event_id"), str) or not value["event_id"].strip(): return None
    if value["action"] == "select" and not isinstance(value.get("wallet"), str): return None
    return value
