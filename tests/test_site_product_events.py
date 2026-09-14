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
    events.st.session_state[events.RECORDED_KEY] = True
    events.st.session_state[events.SESSION_ID_KEY] = "11111111-1111-4111-8111-111111111111"
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
    events.st.session_state[events.RECORDED_KEY] = True
    events.st.session_state[events.SESSION_ID_KEY] = "11111111-1111-4111-8111-111111111111"
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
    events.st.session_state[events.RECORDED_KEY] = True
    events.st.session_state[events.SESSION_ID_KEY] = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("OTG_ANALYTICS_WRITES_ENABLED", "true")
    monkeypatch.setenv("OTG_PRODUCT_EVENTS_ENABLED", "true")
    conn = Mock(); conn.cursor.side_effect = RuntimeError("failure")
    monkeypatch.setattr(events, "_connect", lambda: conn)
    assert events.record_product_event("item", "surface_open") is False
    assert events.st.session_state.get(events.PRODUCT_SEQUENCE_KEY, 0) == 0
    assert events.st.session_state.get(events.PRODUCT_LAST_SURFACE_KEY) is None


@pytest.mark.parametrize("value, expected", [(None, 0), (0, 0), (4, 4), ("4", 4), ("bad", 0), (-5, 0)])
def test_safe_sequence_handles_malformed_state(value, expected):
    events.st.session_state.clear()
    events.st.session_state[events.PRODUCT_SEQUENCE_KEY] = value
    assert events._safe_product_sequence() == expected


def test_safe_control_states_filters_malformed_entries():
    events.st.session_state[events.PRODUCT_CONTROL_STATES_KEY] = {
        "item:view": ("view_change", "chart"),
        "bad1": "not-a-state",
        "bad2": ("view_change", object()),
        4: ("view_change", "table"),
        "bad3": ("unknown", None),
    }
    assert events._safe_control_states() == {"item:view": ("view_change", "chart")}


def test_malformed_state_does_not_block_valid_event(monkeypatch):
    events.st.session_state.clear()
    events.st.session_state[events.RECORDED_KEY] = True
    events.st.session_state[events.SESSION_ID_KEY] = "11111111-1111-4111-8111-111111111111"
    events.st.session_state[events.PRODUCT_SEQUENCE_KEY] = "bad"
    events.st.session_state[events.PRODUCT_CONTROL_STATES_KEY] = "bad"
    monkeypatch.setenv("OTG_ANALYTICS_WRITES_ENABLED", "true")
    monkeypatch.setenv("OTG_PRODUCT_EVENTS_ENABLED", "true")
    cursor = Mock(); cursor.fetchone.return_value = (1,)
    conn = Mock(); conn.cursor.return_value = cursor
    monkeypatch.setattr(events, "_connect", lambda: conn)
    assert events.record_product_event("item", "surface_open") is True
    assert events._safe_product_sequence() == 1


def test_commit_failure_does_not_advance_state(monkeypatch):
    events.st.session_state.clear()
    events.st.session_state[events.RECORDED_KEY] = True
    events.st.session_state[events.SESSION_ID_KEY] = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("OTG_ANALYTICS_WRITES_ENABLED", "true")
    monkeypatch.setenv("OTG_PRODUCT_EVENTS_ENABLED", "true")
    cursor = Mock(); cursor.fetchone.return_value = (1,)
    conn = Mock(); conn.cursor.return_value = cursor; conn.commit.side_effect = RuntimeError("commit")
    monkeypatch.setattr(events, "_connect", lambda: conn)
    assert events.record_product_event("item", "surface_open") is False
    assert events._safe_product_sequence() == 0
    assert events.st.session_state.get(events.PRODUCT_LAST_SURFACE_KEY) is None
    conn.rollback.assert_called_once()


def test_duplicate_is_recorded_and_advances_state(monkeypatch):
    events.st.session_state.clear()
    events.st.session_state[events.RECORDED_KEY] = True
    events.st.session_state[events.SESSION_ID_KEY] = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("OTG_ANALYTICS_WRITES_ENABLED", "true")
    monkeypatch.setenv("OTG_PRODUCT_EVENTS_ENABLED", "true")
    cursor = Mock(); cursor.fetchone.return_value = None
    conn = Mock(); conn.cursor.return_value = cursor
    monkeypatch.setattr(events, "_connect", lambda: conn)
    assert events.record_product_event("market", "surface_open") is True
    assert events._safe_product_sequence() == 1
    assert events.st.session_state[events.PRODUCT_LAST_SURFACE_KEY] == "market"


@pytest.mark.parametrize("shape", [
    *( (surface, "surface_open", None, None) for surface in ("item", "market", "top_items", "trader") ),
    ("item", "filter_apply", "wallet_filter", None), ("item", "filter_clear", "wallet_filter", None),
    ("top_items", "filter_apply", "item_class_filter", None), ("top_items", "filter_clear", "item_class_filter", None),
    ("trader", "filter_apply", "trader_filter", None), ("trader", "filter_clear", "trader_filter", None),
    *( ("top_items", "sort_change", "sort", value) for value in ("market_strength", "volume", "liquidity", "total_supply") ),
    *( ("trader", "sort_change", "sort", value) for value in ("earned", "invested", "sold", "trades") ),
    *( ("market", "period_change", "period", value) for value in ("all", "12m", "6m", "3m") ),
    *( ("top_items", "period_change", "period", value) for value in ("all", "30d", "7d", "1d") ),
    *( ("item", "view_change", "view", value) for value in ("chart", "table") ),
    *( ("item", "toggle_change", control, value) for control in ("usd_price", "trend_line") for value in ("on", "off") ),
    *( ("market", "toggle_change", control, value) for control in ("usd_price", "token_price", "unique_wallets") for value in ("on", "off") ),
    *( ("top_items", "toggle_change", "usd_price", value) for value in ("on", "off") ),
])
def test_every_finite_valid_shape_is_accepted(shape):
    assert events._shape(*shape) == tuple(shape)


@pytest.mark.parametrize("shape", [
    ("unknown", "surface_open", None, None), ("item", "unknown", None, None),
    ("item", "item_select", None, None), ("item", "surface_open", "x", None),
    ("item", "surface_open", None, "x"), ("market", "sort_change", "sort", "trades"),
    ("trader", "toggle_change", "usd_price", "on"), ("item", "filter_apply", "wallet_filter", "on"),
    ("item", "filter_clear", "wallet_filter", "x"), ("top_items", "sort_change", "sort", "bad"),
    ("market", "period_change", "period", "bad"), ("item", "toggle_change", "usd_price", "bad"),
    ("trader", "sort_change", "sort", "0x1234567890abcdef"),
    ("trader", "filter_apply", "trader_filter", "SECRET_RAW_SEARCH_SENTINEL"),
    ("item", "view_change", "view", "some_user_name"),
])
def test_invalid_shapes_are_rejected_before_db(shape):
    assert events._shape(*shape) is None


@pytest.mark.parametrize("global_gate, product_gate", [("false", "true"), ("true", "false"), ("true", "")])
def test_each_write_gate_blocks_before_db(monkeypatch, global_gate, product_gate):
    events.st.session_state.clear()
    events.st.session_state[events.RECORDED_KEY] = True
    events.st.session_state[events.SESSION_ID_KEY] = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("OTG_ANALYTICS_WRITES_ENABLED", global_gate)
    monkeypatch.setenv("OTG_PRODUCT_EVENTS_ENABLED", product_gate)
    db = Mock(); monkeypatch.setattr(events, "_connect", db)
    assert events.record_product_event("item", "surface_open") is False
    db.assert_not_called()


def test_invalid_parent_uuid_blocks_before_db(monkeypatch):
    events.st.session_state.clear()
    events.st.session_state[events.RECORDED_KEY] = True
    events.st.session_state[events.SESSION_ID_KEY] = "not-a-uuid"
    monkeypatch.setenv("OTG_ANALYTICS_WRITES_ENABLED", "true")
    monkeypatch.setenv("OTG_PRODUCT_EVENTS_ENABLED", "true")
    db = Mock(); monkeypatch.setattr(events, "_connect", db)
    assert events.record_product_event("item", "surface_open") is False
    db.assert_not_called()


def test_invalid_values_and_exception_logging_never_include_raw_input_or_uuid(monkeypatch, caplog):
    events.st.session_state.clear()
    events.st.session_state[events.RECORDED_KEY] = True
    events.st.session_state[events.SESSION_ID_KEY] = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("OTG_ANALYTICS_WRITES_ENABLED", "true")
    monkeypatch.setenv("OTG_PRODUCT_EVENTS_ENABLED", "true")
    with caplog.at_level("INFO"):
        assert events.record_product_event("trader", "sort_change", control_key="sort", value_key="SECRET_RAW_SEARCH_SENTINEL") is False
    assert "SECRET_RAW_SEARCH_SENTINEL" not in caplog.text
    assert "0xDEADBEEF_PRIVATE_WALLET_SENTINEL" not in caplog.text
    assert "11111111-1111-4111-8111-111111111111" not in caplog.text


def test_execute_failure_isolated_and_does_not_advance(monkeypatch):
    events.st.session_state.clear(); events.st.session_state[events.RECORDED_KEY] = True; events.st.session_state[events.SESSION_ID_KEY] = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("OTG_ANALYTICS_WRITES_ENABLED", "true"); monkeypatch.setenv("OTG_PRODUCT_EVENTS_ENABLED", "true")
    cursor = Mock(); cursor.execute.side_effect = RuntimeError("SECRET_RAW_SEARCH_SENTINEL")
    conn = Mock(); conn.cursor.return_value = cursor; monkeypatch.setattr(events, "_connect", lambda: conn)
    assert events.record_product_event("item", "surface_open") is False
    conn.rollback.assert_called_once(); assert events._safe_product_sequence() == 0
