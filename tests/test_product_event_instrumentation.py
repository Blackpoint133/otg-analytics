from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "streamlit_opensea_sales"
SIDEBAR = (APP / "ui/sidebar.py").read_text(encoding="utf-8")
APPLICATION = (APP / "app_opensea_sales.py").read_text(encoding="utf-8")
DASHBOARD = (APP / "visitor_dashboard.py").read_text(encoding="utf-8")


def test_surface_open_is_after_session_record_and_canonical_only():
    assert "from site_product_events import record_product_event" in APPLICATION
    assert APPLICATION.index("record_current_session_once(") < APPLICATION.index('record_product_event(current_mode, "surface_open")')
    assert 'if current_mode in {"item", "market", "top_items", "trader"}' in APPLICATION


def test_sidebar_has_safe_wrapper_and_privacy_safe_mappings():
    assert "def _record_product_event_safe" in SIDEBAR
    assert "except Exception:" in SIDEBAR
    assert '"wallet_filter"' in SIDEBAR and '"filter_apply"' in SIDEBAR and '"filter_clear"' in SIDEBAR
    assert '"trader_filter"' in SIDEBAR


def test_toggle_view_period_sort_instrumentation_is_present():
    for token in ("usd_price", "trend_line", "token_price", "unique_wallets", "view_change", "period_change", "sort_change", "market_strength", "total_supply", "item_class_filter"):
        assert token in SIDEBAR
    assert "if current_item_view != 'chart'" in SIDEBAR
    assert "if current_period != 'all'" in SIDEBAR
    assert "if current_mode != 'market_strength'" in SIDEBAR
    assert "if st.session_state.trader_sort_by != option" in SIDEBAR


def test_product_usage_dashboard_is_separate_and_isolated():
    assert "from product_event_queries import load_product_event_aggregates" in DASHBOARD
    assert "@st.cache_data(ttl=120, show_spinner=False)" in DASHBOARD
    assert "def _cached_product_event_data" in DASHBOARD
    assert "_cached_product_event_data.clear()" in DASHBOARD
    assert 'st.subheader("Product Usage")' in DASHBOARD
    assert "Privacy-safe categorical interaction events. Wallets, usernames, search text, IPs and browser identifiers are not stored in product-event rows. Item selections remain in Item Activity." in DASHBOARD
    assert 'st.info("No product usage events in this period.")' in DASHBOARD
    assert 'st.markdown("**Product Interaction Detail**")' in DASHBOARD
    assert '"Product Events"' in DASHBOARD and '"Surface Opens"' in DASHBOARD and '"Feature Interactions"' in DASHBOARD and '"Latest Product Event"' in DASHBOARD
    assert '"Unique Sessions"' in DASHBOARD and '"Unique Visitors"' in DASHBOARD
    render_source = DASHBOARD[DASHBOARD.index("def _render_dashboard"):]
    assert render_source.index('st.subheader("Post Performance")') < render_source.index("_render_product_usage(product_data)") < render_source.index('st.subheader("Item Interest")')
