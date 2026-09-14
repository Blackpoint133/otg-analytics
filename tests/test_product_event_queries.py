import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "streamlit_opensea_sales"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

import product_event_queries as queries


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
