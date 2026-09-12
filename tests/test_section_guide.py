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
    assert TRADER.index("if guide_open:") < TRADER.index("render_trader_table(prepared_visible)")


def test_helper_is_per_section_and_all_guides_are_implemented():
    assert "def render_section_guide_button" in GUIDE
    for section in ("item", "market", "top_items", "trader"):
        assert f'render_section_guide_button("{section}")' in SIDEBAR
    for page in ("item_overview.py", "market_overview.py", "top_items_overview.py"):
        source = (ROOT / "streamlit_opensea_sales" / "ui" / page).read_text(encoding="utf-8")
        assert "Coming soon" not in source
        assert "render_section_guide_panel" in source


def test_analytics_guide_punctuation_uses_safe_html_entities():
    market = (ROOT / "streamlit_opensea_sales" / "ui" / "market_overview.py").read_text(encoding="utf-8")
    top_items = (ROOT / "streamlit_opensea_sales" / "ui" / "top_items_overview.py").read_text(encoding="utf-8")
    assert "trading activity &mdash; not order-book depth" not in market
    assert "show how many completed sales occurred over time" in market
    assert "FILTERED RANK (red) ranks within selected classes" in top_items
    assert "normalized Volume &times; normalized Liquidity" in top_items
    assert "trading activity  not order-book depth" not in market
    assert "recalculate ranks  displayed rank numbers" not in top_items
    assert "normalized Volume  normalized Liquidity" not in top_items


def test_trader_sort_controls_remain_before_guide():
    assert SIDEBAR.index('key="trader_sort_controls"') < SIDEBAR.index('render_section_guide_button("trader")')
    assert '"sort_by": st.session_state.trader_sort_by' in SIDEBAR


def test_sidebar_filter_labels_and_guide_reference_style():
    assert '<div class="otg-sidebar-label">FILTERS</div>' in SIDEBAR
    assert '<div class="otg-sidebar-label">TRADER</div>' not in SIDEBAR
    assert 'render_section_guide_button("item")' in SIDEBAR
    assert 'label_visibility="collapsed"' in SIDEBAR
    assert "height:28px!important" in SIDEBAR
    assert "padding:4px 10px!important" in SIDEBAR
    assert "margin-bottom:3px!important" in SIDEBAR
    assert "color:#FFFFFF!important" in GUIDE
    assert "color:#000!important" not in GUIDE


def test_all_sections_have_isolated_guides_and_short_navigation_labels():
    for section in ("item", "market", "top_items", "trader"):
        assert f'render_section_guide_button("{section}")' in SIDEBAR
    mode_switch = (ROOT / "streamlit_opensea_sales" / "ui" / "mode_switch.py").read_text(encoding="utf-8")
    for label in ("ITEM", "MARKET", "TOP ITEMS", "TOP TRADERS", "ROADMAP"):
        assert label in mode_switch

def test_trader_guide_uses_shared_panel_and_css_is_not_local():
    trader = TRADER
    assert "render_section_guide_panel" in trader
    assert "trusted_html=True" in trader
    assert ".trader-metric-guide {{" not in trader
    assert "otg-section-guide-panel" in GUIDE
    assert "trusted_html" in GUIDE


def test_guides_describe_current_responsive_interactions():
    item = (ROOT / "streamlit_opensea_sales" / "ui" / "item_overview.py").read_text(encoding="utf-8")
    top_items = (ROOT / "streamlit_opensea_sales" / "ui" / "top_items_overview.py").read_text(encoding="utf-8")
    trader = TRADER
    assert "TREND LINE</b> adds the prepared price trend to the CHART" in item
    assert "MOBILE VIEW</b> On mobile, ITEM ANALYTICS displays the Item Card and CHART only" in item
    assert "ITEM PROFILE</b> On desktop, hover over an item's IMAGE" in top_items
    assert "standalone Item Profile Cards" in top_items
    assert "PROFILE CARD</b> The card shows FILTERED RANK" in top_items
    assert "TRADER PROFILE</b> On desktop, hover over a trader's IMAGE" in trader
    assert "standalone Trader Profile Cards" in trader
    assert "DESKTOP TABLE</b> COVERAGE" in trader
    assert "MATCHED SALES" in trader
    assert "Hover over a trader to open" not in trader


def test_market_guide_is_untouched_by_guide_content_audit():
    market = (ROOT / "streamlit_opensea_sales" / "ui" / "market_overview.py").read_text(encoding="utf-8")
    assert "MARKET SUMMARY" in market
    assert "UNIQUE WALLETS" in market
