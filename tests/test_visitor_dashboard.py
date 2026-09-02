from datetime import datetime, timezone
import sys
import uuid
from pathlib import Path

import pandas as pd
import psycopg2
import streamlit as st
import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "streamlit_opensea_sales"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from visitor_dashboard_queries import (
    classify_all_profiles,
    count_all_post_returning_profiles,
    count_bounded_returning_profiles,
    period_bounds,
)


def test_period_bounds_are_utc_and_whitelisted():
    now = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
    start, end = period_bounds("24H", now)
    assert end == now
    assert start == datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


def test_all_period_has_no_lower_bound():
    start, end = period_bounds("ALL", datetime(2026, 8, 27, 12, tzinfo=timezone.utc))
    assert start is None
    assert end.tzinfo is not None


def test_invalid_period_is_rejected():
    try:
        period_bounds("90D")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid range accepted")


def test_mode_labels_are_dashboard_safe():
    from visitor_dashboard import MODE_LABELS
    assert set(MODE_LABELS) == {"item", "market", "top_items"}


def test_empty_post_frame_is_supported():
    frame = pd.DataFrame(columns=["post", "sessions"])
    assert frame.empty


def test_all_categories_are_mutually_exclusive():
    result = classify_all_profiles({"a": 1, "b": 1, "c": 2, "d": 3})
    assert result == {"stable_visitors": 4, "new_visitors": 2, "returning_visitors": 2}
    assert result["new_visitors"] + result["returning_visitors"] == result["stable_visitors"]


def test_bounded_new_and_returning_are_separate():
    start = datetime(2026, 8, 27, tzinfo=timezone.utc)
    first_seen = {"a": start.replace(day=26), "b": start, "c": start.replace(day=28)}
    selected = {"a", "b"}
    returning = {profile for profile in selected if first_seen[profile] < start}
    assert count_bounded_returning_profiles(selected, first_seen, start) == 1
    assert selected - returning == {"b"}
    assert returning.isdisjoint(selected - returning)


def test_all_post_returning_uses_overall_profile_history():
    result = count_all_post_returning_profiles(["a", "b"], {"a": 2, "b": 1})
    assert result == 1
    assert count_all_post_returning_profiles(["c"], {"c": 3}) == 1


def test_unique_visitor_presentation_terms_are_consistent():
    source = (APP_DIR / "visitor_dashboard.py").read_text(encoding="utf-8")
    assert 'metric("Unique Visitors"' in source
    assert 'name="Unique Visitors"' in source
    assert '"Unique Visitors"' in source
    assert 'metric("Stable Visitors"' not in source


def test_single_series_charts_disable_legends_and_summary_is_dynamic():
    source = (APP_DIR / "visitor_dashboard.py").read_text(encoding="utf-8")
    assert source.count("showlegend=False") >= 4
    assert 'posts["post"]' in source
    assert 'posts["sessions"]' in source


def test_item_interest_and_drilldown_surface_are_present():
    source = (APP_DIR / "visitor_dashboard.py").read_text(encoding="utf-8")
    query_source = (APP_DIR / "visitor_dashboard_queries.py").read_text(encoding="utf-8")
    assert 'st.subheader("Item Interest")' in source
    assert 'Recorded Item' in source
    assert 'st.expander("Visitor Drilldown", expanded=False)' in source
    assert 'Shows recorded session contexts, not every page or item viewed.' in source
    assert 'load_item_interest' in query_source
    assert 'load_visitor_summaries' in query_source
    assert 'load_visitor_timeline' in query_source


def test_item_interest_query_is_human_filtered_and_v2_scoped_for_unique_counts():
    source = (APP_DIR / "visitor_dashboard_queries.py").read_text(encoding="utf-8")
    assert "s.mode = 'item'" in source
    assert "NOT s.is_bot AND NOT s.is_internal" in source
    assert "s.identity_version = 2 AND s.browser_visitor_hash IS NOT NULL" in source
    assert "unique_v2_visitors" in source


def test_drilldown_visible_fields_exclude_raw_identity_columns():
    source = (APP_DIR / "visitor_dashboard_queries.py").read_text(encoding="utf-8")
    timeline_section = source[source.index("def load_visitor_timeline"):source.index("def load_dashboard_data")]
    selected_sql = timeline_section.split('SELECT', 1)[-1].split('FROM', 1)[0]
    assert "session_id" not in selected_sql
    assert "visitor_hash" not in selected_sql
    assert "profile_key" not in selected_sql


def test_transient_aliases_are_not_hash_derived():
    source = (APP_DIR / "visitor_dashboard.py").read_text(encoding="utf-8")
    assert 'f"Visitor #{idx:03d}"' in source
    assert "profile_key[:" not in source
    assert "profile_key[-" not in source


def test_item_interest_data_is_part_of_dashboard_aggregate_payload():
    source = (APP_DIR / "visitor_dashboard_queries.py").read_text(encoding="utf-8")
    assert '"item_interest": item_interest' in source
    assert '"item_missing": item_missing' in source


def test_item_event_contract_and_activity_queries_are_present():
    writer = (APP_DIR / "site_item_events.py").read_text(encoding="utf-8")
    queries = (APP_DIR / "visitor_dashboard_queries.py").read_text(encoding="utf-8")
    migration = (APP_DIR.parent / "sql" / "create_site_item_events.sql").read_text(encoding="utf-8")
    for event_type in ("initial_default", "initial_explicit", "item_select"):
        assert event_type in writer
        assert event_type in migration
    assert "def load_item_activity" in queries
    assert "def load_visitor_item_activity" in queries
    assert "event_type IN ('initial_explicit', 'item_select')" in queries


def test_item_event_writer_rejects_invalid_or_empty_item_without_db_access(monkeypatch):
    import site_item_events

    monkeypatch.setattr(site_item_events, "_connect", lambda: (_ for _ in ()).throw(AssertionError("DB must not be opened")))
    assert site_item_events.record_item_event("", "item_select", None) is False
    assert site_item_events.record_item_event("valid", "unknown", None) is False


def test_item_event_selection_deduplicates_same_state_and_allows_return_to_item(monkeypatch):
    import site_item_events

    st = site_item_events.st
    st.session_state.clear()
    calls = []

    def fake_record(item_key, event_type, browser_identity):
        calls.append((item_key, event_type))
        st.session_state[site_item_events.LAST_ITEM_KEY] = item_key
        return True

    monkeypatch.setattr(site_item_events, "record_item_event", fake_record)
    assert site_item_events.record_explicit_item_selection("A", None) is True
    assert site_item_events.record_explicit_item_selection("A", None) is False
    assert site_item_events.record_explicit_item_selection("B", None) is True
    assert site_item_events.record_explicit_item_selection("A", None) is True
    assert calls == [("A", "item_select"), ("B", "item_select"), ("A", "item_select")]


def test_item_activity_visible_fields_are_aggregate_or_safe_timeline_fields():
    source = (APP_DIR / "visitor_dashboard.py").read_text(encoding="utf-8")
    assert 'st.subheader("Item Activity")' in source
    assert '"Selections"' in source
    assert '"Unique Sessions"' in source
    assert '"Unique Visitors"' in source
    assert '"Latest Selection"' in source
    assert 'event_labels' in source
    assert 'expanded=False' in source


def test_refresh_clears_the_dashboard_cache_wrapper_only():
    import visitor_dashboard

    class CacheStub:
        def __init__(self):
            self.clear_calls = 0

        def clear(self):
            self.clear_calls += 1

    stub = CacheStub()
    original = visitor_dashboard._cached_dashboard_data
    try:
        visitor_dashboard._cached_dashboard_data = stub
        visitor_dashboard._clear_dashboard_cache()
    finally:
        visitor_dashboard._cached_dashboard_data = original

    assert stub.clear_calls == 1
    assert not hasattr(visitor_dashboard.load_dashboard_data, "clear")


def test_visitor_item_activity_is_loaded_and_rendered_once(monkeypatch):
    from contextlib import contextmanager
    import visitor_dashboard

    summary = pd.DataFrame([{
        "profile_key": "server-only-profile",
        "sessions": 1,
        "recorded_items": 1,
        "first_seen": datetime(2026, 8, 27, tzinfo=timezone.utc),
        "latest_visit": datetime(2026, 8, 27, tzinfo=timezone.utc),
    }])
    session_timeline = pd.DataFrame([{
        "started_at_utc": datetime(2026, 8, 27, tzinfo=timezone.utc),
        "mode": "item", "recorded_item": "A", "acquisition": "Direct",
        "campaign": None, "post": None,
    }])
    event_timeline = pd.DataFrame([{
        "occurred_at_utc": datetime(2026, 8, 27, tzinfo=timezone.utc),
        "event_type": "item_select", "item_key": "B", "sequence_no": 1,
        "campaign": None, "post": None,
    }])
    calls = []

    @contextmanager
    def fake_expander(*args, **kwargs):
        yield None

    class FakeColumn:
        def metric(self, *args, **kwargs):
            pass

    monkeypatch.setattr(visitor_dashboard, "load_visitor_summaries", lambda range_key: summary)
    monkeypatch.setattr(visitor_dashboard, "load_visitor_timeline", lambda profile_key: session_timeline)
    monkeypatch.setattr(visitor_dashboard, "load_visitor_item_activity", lambda profile_key: calls.append(profile_key) or event_timeline)
    monkeypatch.setattr(visitor_dashboard.st, "expander", fake_expander)
    monkeypatch.setattr(visitor_dashboard.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(visitor_dashboard.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(visitor_dashboard.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(visitor_dashboard.st, "selectbox", lambda label, options, **kwargs: options[0])
    monkeypatch.setattr(visitor_dashboard.st, "columns", lambda count: [FakeColumn() for _ in range(count)])
    monkeypatch.setattr(visitor_dashboard.st, "dataframe", lambda *args, **kwargs: None)

    visitor_dashboard._render_visitor_drilldown("ALL")

    assert calls == ["server-only-profile"]


def test_item_event_writer_logs_successful_lifecycle_without_sensitive_values(monkeypatch):
    import site_item_events

    class FakeLogger:
        def __init__(self):
            self.messages = []

        def info(self, message):
            self.messages.append(message)

    class FakeCursor:
        def execute(self, *args, **kwargs):
            pass

        def close(self):
            pass

    class FakeConnection:
        def __init__(self):
            self.cursor_instance = FakeCursor()

        def cursor(self):
            return self.cursor_instance

        def commit(self):
            pass

        def rollback(self):
            raise AssertionError("rollback was not expected")

        def close(self):
            pass

    logger = FakeLogger()
    monkeypatch.setattr(site_item_events, "LOGGER", logger)
    monkeypatch.setattr(site_item_events, "_connect", lambda: FakeConnection())
    site_item_events.st.session_state.clear()

    assert site_item_events.record_item_event("Synthetic Item", "item_select", None) is True
    text = " ".join(logger.messages)
    assert "ITEM_EVENT_ATTEMPT" in text
    assert "ITEM_EVENT_DB_CONNECT_OK" in text
    assert "ITEM_EVENT_INSERT_OK" in text
    assert "ITEM_EVENT_COMMIT_OK" in text
    for sensitive in ("Synthetic Item", "fake-browser-hash", "parent-uuid", "password"):
        assert sensitive not in text


def test_item_event_parent_uuid_uses_driver_compatible_string_payload():
    import site_item_events
    from psycopg2.extensions import adapt

    parent_value = "11111111-1111-4111-8111-111111111111"
    site_item_events.st.session_state.clear()
    site_item_events.st.session_state["site_analytics_session_id"] = parent_value
    canonical = site_item_events._parent_session_id()
    assert canonical == parent_value
    assert isinstance(canonical, str)
    assert adapt(canonical).getquoted() == b"'11111111-1111-4111-8111-111111111111'"
    with pytest.raises(psycopg2.ProgrammingError):
        adapt(uuid.UUID(parent_value))


def test_item_event_writer_logs_connect_failure_without_raw_exception(monkeypatch):
    import site_item_events

    class FakeLogger:
        def __init__(self):
            self.messages = []

        def info(self, message):
            self.messages.append(message)

    logger = FakeLogger()
    monkeypatch.setattr(site_item_events, "LOGGER", logger)
    monkeypatch.setattr(site_item_events, "_connect", lambda: (_ for _ in ()).throw(RuntimeError("password=secret item=Hidden")))
    site_item_events.st.session_state.clear()

    assert site_item_events.record_item_event("Hidden", "item_select", None) is False
    text = " ".join(logger.messages)
    assert "ITEM_EVENT_WRITE_FAILED" in text
    assert "stage=connect" in text
    assert "exception_class=RuntimeError" in text
    assert "password=secret" not in text
    assert "Hidden" not in text


def test_item_event_writer_distinguishes_insert_and_commit_failures(monkeypatch):
    import site_item_events

    class FakeLogger:
        def __init__(self):
            self.messages = []

        def info(self, message):
            self.messages.append(message)

    class SyntheticInsertError(Exception):
        pgcode = "23505"

    class FakeCursor:
        def __init__(self, error=None):
            self.error = error

        def execute(self, *args, **kwargs):
            if self.error:
                raise self.error

        def close(self):
            pass

    class FakeConnection:
        def __init__(self, cursor, commit_error=None):
            self.cursor_instance = cursor
            self.commit_error = commit_error
            self.rolled_back = False

        def cursor(self):
            return self.cursor_instance

        def commit(self):
            if self.commit_error:
                raise self.commit_error

        def rollback(self):
            self.rolled_back = True

        def close(self):
            pass

    logger = FakeLogger()
    monkeypatch.setattr(site_item_events, "LOGGER", logger)
    site_item_events.st.session_state.clear()
    insert_conn = FakeConnection(FakeCursor(SyntheticInsertError("raw item and password")))
    monkeypatch.setattr(site_item_events, "_connect", lambda: insert_conn)
    assert site_item_events.record_item_event("Hidden", "item_select", None) is False
    insert_text = " ".join(logger.messages)
    assert "stage=insert" in insert_text
    assert "exception_class=SyntheticInsertError" in insert_text
    assert "sqlstate=23505" in insert_text
    assert "raw item" not in insert_text
    assert insert_conn.rolled_back is True

    logger.messages.clear()
    commit_conn = FakeConnection(FakeCursor(), commit_error=RuntimeError("raw commit detail"))
    monkeypatch.setattr(site_item_events, "_connect", lambda: commit_conn)
    assert site_item_events.record_item_event("Hidden", "item_select", None) is False
    commit_text = " ".join(logger.messages)
    assert "ITEM_EVENT_INSERT_OK" in commit_text
    assert "stage=commit" in commit_text
    assert "ITEM_EVENT_COMMIT_OK" not in commit_text
    assert "raw commit detail" not in commit_text
    assert commit_conn.rolled_back is True


def test_sidebar_item_callback_observability_is_redacted_and_reports_result(monkeypatch):
    import ui.sidebar as sidebar

    class FakeLogger:
        def __init__(self):
            self.messages = []

        def info(self, message):
            self.messages.append(message)

    logger = FakeLogger()
    results = iter((True, False))
    monkeypatch.setattr(sidebar, "SIDEBAR_LOGGER", logger)
    monkeypatch.setattr(
        sidebar,
        "record_explicit_item_selection",
        lambda item, identity: next(results),
    )
    sidebar.st.session_state.clear()
    sidebar.st.session_state["selected_item"] = "Synthetic Item"
    sidebar.st.session_state[sidebar.LAST_ITEM_KEY] = "Previous Item"
    sidebar.st.session_state[sidebar.SEQUENCE_KEY] = 2
    identity = {
        "status": "ok",
        "id": "FAKE_BROWSER_ID",
        "hash": "FAKE_BROWSER_HASH",
    }

    sidebar._on_item_selection_changed(identity)
    sidebar.st.session_state["selected_item"] = "Another Synthetic Item"
    sidebar._on_item_selection_changed(identity)

    text = " ".join(logger.messages)
    assert "ITEM_UI_CALLBACK_ENTER" in text
    assert "ITEM_UI_CALLBACK_STATE" in text
    assert "ITEM_UI_EVENT_CALL" in text
    assert "success=True" in text
    assert "success=False" in text
    for sensitive in (
        "Synthetic Item",
        "Another Synthetic Item",
        "FAKE_BROWSER_ID",
        "FAKE_BROWSER_HASH",
        "parent-session-uuid",
        "password",
    ):
        assert sensitive not in text
