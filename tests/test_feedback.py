from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
APP = ROOT / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

from feedback_store import normalize_source_mode, sanitize_source_item


def test_feedback_store_normalizes_source_context():
    assert normalize_source_mode("top_items") == "top_items"
    assert normalize_source_mode("not-valid") == "unknown"
    assert len(sanitize_source_item("<b>unsafe</b>" * 100)) == 180


def test_feedback_page_contract_and_safe_persistence_hooks():
    source = (APP / "ui" / "feedback.py").read_text(encoding="utf-8")
    assert 'BUG": "bug"' in source
    assert '"SUGGESTION"' in source and '"DATA ISSUE"' in source and '"OTHER"' in source
    assert 'placeholder="Describe the issue or idea..."' in source
    assert '10 <= len(clean_message) <= 2000' in source
    assert "source_context" in source
    assert "Do not include passwords, seed phrases, private keys" in source
    assert "TOO MANY SUBMISSIONS" in source


def test_feedback_navigation_and_early_routing_contract():
    nav = (APP / "ui" / "mode_switch.py").read_text(encoding="utf-8")
    app = (APP / "app_opensea_sales.py").read_text(encoding="utf-8")
    store = (APP / "feedback_store.py").read_text(encoding="utf-8")
    assert "'feedback']" in nav
    assert "feedback_href" in nav and "source" in nav
    assert "href=\"{feedback_href}\"" in nav
    assert "current_mode == \"feedback\"" in app
    route = app.index('current_mode == "feedback"')
    analytics = app.index('current_mode = mode_switch.render_mode_switch()')
    session_call = app.index('record_current_session_once', analytics)
    assert analytics < route < session_call
    assert "ON CONFLICT (submission_id) DO NOTHING" in store
    assert "%(message)s" in store


def test_feedback_schema_is_additive_and_constrained():
    sql = (ROOT / "sql" / "create_user_feedback.sql").read_text(encoding="utf-8")
    assert "public.user_feedback" in sql
    assert "CREATE TABLE IF NOT EXISTS" in sql
    assert "GENERATED ALWAYS AS IDENTITY" in sql
    assert "submission_id uuid NOT NULL UNIQUE" in sql
    assert "char_length(message) BETWEEN 10 AND 2000" in sql
    assert "in-game" not in sql
