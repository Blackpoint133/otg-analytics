from pathlib import Path


ROOT = Path(__file__).parents[1]
ITEM = (ROOT / "streamlit_opensea_sales" / "ui" / "item_overview.py").read_text(encoding="utf-8")
SIDEBAR = (ROOT / "streamlit_opensea_sales" / "ui" / "sidebar.py").read_text(encoding="utf-8")


def test_item_viewport_width_is_persisted_before_visible_sidebar_controls():
    viewport = SIDEBAR.index('get_viewport_info(key="item_chart_viewport")')
    display_options = SIDEBAR.index('st.sidebar.header("Display Options")')
    assert viewport < display_options
    assert "item_viewport_width" in SIDEBAR
    assert "if viewport_width > 0" in SIDEBAR


def test_item_desktop_ratios_preserve_large_and_add_exact_medium_breakpoint():
    assert "if 769 <= viewport_width <= 1440:" in ITEM
    assert "column_ratio = [0.26, 0.74]" in ITEM
    assert "elif 1441 <= viewport_width <= 1680:" in ITEM
    assert "column_ratio = [0.22, 0.78]" in ITEM
    assert "column_ratio = [0.17, 0.83]" in ITEM
    assert "st.columns(column_ratio)" in ITEM
    assert "is_mobile_chart" in ITEM


def test_top_items_has_one_gap_before_guide_after_one_day():
    period = SIDEBAR.split('key="top_items_period_1d"', 1)[1]
    guide = period.split('render_section_guide_button("top_items")', 1)[0]
    assert guide.count("otg-sidebar-section-gap") == 1
    assert '<div class="otg-sidebar-section-gap"></div>' in guide
