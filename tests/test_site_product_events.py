import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

APP = Path(__file__).resolve().parents[1] / "streamlit_opensea_sales"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

import site_product_events as events


def test_exact_allowlists_and_shape_contract():
    assert events.VALID_SURFACES == {"item", "market", "top_items", "trader"}
    assert events.VALID_EVENT_TYPES == {"surface_open", "filter_apply", "filter_clear", "sort_change", "period_change", "view_change", "toggle_change"}
    assert events._shape("trader", "surface_open", None, None) == ("trader", "surface_open", None, None)
    assert events._shape("item", "filter_apply", "wallet_filter", None) is not None
    assert events._shape("top_items", "sort_change", "sort", "market_strength") is not None
    assert events._shape("trader", "sort_change", "sort", "trades") is not None
    assert events._shape("market", "period_change", "period", "12m") is not None
    assert events._shape("top_items", "period_change", "period", "30d") is not None
    assert events._shape("item", "view_change", "view", "table") is not None
    assert events._shape("market", "toggle_change", "token_price", "on") is not None
    assert events._shape("trader", "sort_change", "sort", "0x1234") is None
    assert events._shape("item", "filter_apply", "trader_filter", None) is None
    assert events._shape("item", "item_select", None, None) is None


def test_disabled_or_missing_parent_rejects_before_db(monkeypatch):
    events.st.session_state.clear()
    monkeypatch.setenv("OTG_ANALYTICS_WRITES_ENABLED", "true")
    monkeypatch.setenv("OTG_PRODUCT_EVENTS_ENABLED", "true")
    db = Mock()
    monkeypatch.setattr(events, "_connect", db)
    assert events.record_product_event("item", "surface_open") is False
    db.assert_not_called()


def test_success_advances_sequence_and_control_state(monkeypatch):
    events.st.session_state.clear()
    events.st.session_state["site_analytics_recorded"] = True
    events.st.session_state["site_analytics_session_id"] = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("OTG_ANALYTICS_WRITES_ENABLED", "true")
    monkeypatch.setenv("OTG_PRODUCT_EVENTS_ENABLED", "true")
    cursor = Mock()
    cursor.fetchone.return_value = (7,)
    conn = Mock()
    conn.cursor.return_value = cursor
    monkeypatch.setattr(events, "_connect", lambda: conn)
    assert events.record_product_event("trader", "sort_change", control_key="sort", value_key="trades") is True
    assert events.st.session_state[events.PRODUCT_SEQUENCE_KEY] == 1
    assert events.st.session_state[events.PRODUCT_CONTROL_STATES_KEY]["trader:sort"] == ("sort_change", "trades")
    assert "ON CONFLICT (parent_session_id, sequence_no)" in events._SQL
    assert events.record_product_event("trader", "sort_change", control_key="sort", value_key="trades") is False
    assert cursor.execute.call_count == 1


def test_surface_transitions_and_filter_reapply(monkeypatch):
    events.st.session_state.clear()
    events.st.session_state["site_analytics_recorded"] = True
    events.st.session_state["site_analytics_session_id"] = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("OTG_ANALYTICS_WRITES_ENABLED", "true")
    monkeypatch.setenv("OTG_PRODUCT_EVENTS_ENABLED", "true")
    cursor = Mock(); cursor.fetchone.return_value = (1,)
    conn = Mock(); conn.cursor.return_value = cursor
    monkeypatch.setattr(events, "_connect", lambda: conn)
    assert events.record_product_event("item", "surface_open")
    assert not events.record_product_event("item", "surface_open")
    assert events.record_product_event("market", "surface_open")
    assert events.record_product_event("item", "surface_open")
    assert events.record_product_event("item", "filter_apply", control_key="wallet_filter")
    assert events.record_product_event("item", "filter_clear", control_key="wallet_filter")
    assert events.record_product_event("item", "filter_apply", control_key="wallet_filter")


def test_failed_insert_does_not_advance_state(monkeypatch):
    events.st.session_state.clear()
    events.st.session_state["site_analytics_recorded"] = True
    events.st.session_state["site_analytics_session_id"] = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("OTG_ANALYTICS_WRITES_ENABLED", "true")
    monkeypatch.setenv("OTG_PRODUCT_EVENTS_ENABLED", "true")
    conn = Mock(); conn.cursor.side_effect = RuntimeError("failure")
    monkeypatch.setattr(events, "_connect", lambda: conn)
    assert events.record_product_event("item", "surface_open") is False
    assert events.st.session_state.get(events.PRODUCT_SEQUENCE_KEY, 0) == 0
    assert events.st.session_state.get(events.PRODUCT_LAST_SURFACE_KEY) is None
