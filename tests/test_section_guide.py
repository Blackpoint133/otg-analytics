from pathlib import Path


ROOT = Path(__file__).parents[1]
SIDEBAR = (ROOT / "streamlit_opensea_sales" / "ui" / "sidebar.py").read_text(encoding="utf-8")
TRADER = (ROOT / "streamlit_opensea_sales" / "ui" / "trader_overview.py").read_text(encoding="utf-8")
GUIDE = (ROOT / "streamlit_opensea_sales" / "ui" / "section_guide.py").read_text(encoding="utf-8")


def test_trader_guide_is_sidebar_scoped_and_uses_stable_state_key():
    assert 'render_section_guide_button("trader")' in SIDEBAR
    assert SIDEBAR.index('otg-sidebar-label">GUIDE') < SIDEBAR.index('render_section_guide_button("trader")')
    assert 'state_key = f"{section_key}_guide_open"' in GUIDE
    assert 'control_key = f"{section_key}_guide"' in GUIDE
    assert 'label: str = "GUIDE"' in GUIDE
    assert 'type="primary" if is_open else "secondary"' in GUIDE
    assert "background:#FF003A!important" in GUIDE


def test_old_main_metric_trigger_is_removed_and_content_is_main_area():
    assert "METRIC GUIDE" not in TRADER
    assert "trader_metric_guide" not in TRADER
    assert "if guide_open:" in TRADER
    assert TRADER.index("if guide_open:") < TRADER.index("render_trader_table(consolidated_table_rows")


def test_helper_is_per_section_and_no_unimplemented_section_buttons_exist():
    assert "def render_section_guide_button" in GUIDE
    assert 'render_section_guide_button("item")' not in SIDEBAR
    assert 'render_section_guide_button("market")' not in SIDEBAR
    assert 'render_section_guide_button("top_items")' not in SIDEBAR


def test_trader_sort_controls_remain_before_guide():
    assert SIDEBAR.index('key="trader_sort_controls"') < SIDEBAR.index('render_section_guide_button("trader")')
    assert '"sort_by": st.session_state.trader_sort_by' in SIDEBAR
