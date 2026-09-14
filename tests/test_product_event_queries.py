import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "streamlit_opensea_sales"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

import product_event_queries as queries
from datetime import datetime, timezone
from unittest.mock import Mock


def test_query_contract_and_read_only_connection():
    source = (APP / "product_event_queries.py").read_text(encoding="utf-8")
    assert queries.OUTPUT_COLUMNS == ["surface", "event_type", "control_key", "value_key", "events", "unique_sessions", "unique_v2_visitors", "latest_event"]
    assert "JOIN public.site_visit_sessions s ON s.session_id = e.parent_session_id" in source
    assert "NOT s.is_bot AND NOT s.is_internal" in source
    assert "count(DISTINCT e.parent_session_id)" in source
    assert "identity_version = 2 AND s.browser_visitor_hash IS NOT NULL" in source
    assert "ORDER BY events DESC" in source
    assert "default_transaction_read_only=on" in (APP / "visitor_dashboard_queries.py").read_text(encoding="utf-8")


def test_ranges_reuse_dashboard_semantics():
    for key in ("24H", "7D", "30D", "ALL"):
        start, end = queries.period_bounds(key)
        assert end is not None
    try:
        queries.period_bounds("90D")
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported range accepted")


def test_query_returns_mocked_aggregate_rows_and_exact_range(monkeypatch):
    rows = [("trader", "sort_change", "sort", "trades", 3, 2, 1, datetime(2026, 9, 14, tzinfo=timezone.utc)), ("item", "surface_open", None, None, 1, 1, 1, datetime(2026, 9, 13, tzinfo=timezone.utc))]
    cursor = Mock(); cursor.fetchall.return_value = rows
    conn = Mock(); conn.cursor.return_value = cursor
    monkeypatch.setattr(queries, "_connect", lambda: conn)
    result = queries.load_product_event_aggregates("7D", datetime(2026, 9, 14, tzinfo=timezone.utc))
    assert list(result.columns) == queries.OUTPUT_COLUMNS
    assert result.iloc[0]["surface"] == "trader" and result.iloc[0]["events"] == 3
    sql, params = cursor.execute.call_args.args
    assert "JOIN public.site_visit_sessions s ON s.session_id = e.parent_session_id" in sql
    assert "NOT s.is_bot" in sql and "NOT s.is_internal" in sql
    assert "count(DISTINCT e.parent_session_id)" in sql
    assert "s.identity_version = 2 AND s.browser_visitor_hash IS NOT NULL" in sql
    assert params["period_start"] == datetime(2026, 9, 7, tzinfo=timezone.utc)
    assert params["period_end"] == datetime(2026, 9, 14, tzinfo=timezone.utc)
    cursor.close.assert_called_once(); conn.close.assert_called_once()


def test_query_failure_closes_resources(monkeypatch):
    cursor = Mock(); cursor.execute.side_effect = RuntimeError("query failed")
    conn = Mock(); conn.cursor.return_value = cursor
    monkeypatch.setattr(queries, "_connect", lambda: conn)
    try:
        queries.load_product_event_aggregates("24H", datetime(2026, 9, 14, tzinfo=timezone.utc))
    except RuntimeError:
        pass
    else:
        raise AssertionError("query failure was swallowed")
    cursor.close.assert_called_once(); conn.close.assert_called_once()
