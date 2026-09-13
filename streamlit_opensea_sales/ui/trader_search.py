from pathlib import Path
from typing import Any
import streamlit.components.v1 as components

_trader_search = components.declare_component("otg_trader_search", path=str(Path(__file__).parent / "trader_search_component"))

def render_trader_search(records: list[dict[str, str]], selected_wallet: str | None = None, selected_display_name: str | None = None, initial_query: str = "", key: str = "trader_search") -> dict[str, Any] | None:
    value = _trader_search(records=records, selected_wallet=selected_wallet, selected_display_name=selected_display_name, initial_query=initial_query, default=None, key=key)
    if not isinstance(value, dict) or value.get("action") not in {"select", "clear"} or not isinstance(value.get("event_id"), str) or not value["event_id"].strip():
        return None
    if value["action"] == "select" and (not isinstance(value.get("wallet"), str) or not value["wallet"].strip()):
        return None
    return value
