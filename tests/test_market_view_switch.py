from pathlib import Path
import sys


APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

from ui.market_overview import (  # noqa: E402
    get_market_view_chart_plan,
    normalize_market_view as normalize_overview_view,
)
from ui.sidebar import (  # noqa: E402
    MARKET_VIEW_VALUES,
    normalize_market_view as normalize_sidebar_view,
)


ROOT = Path(__file__).parents[1]
SIDEBAR = ROOT / "streamlit_opensea_sales" / "ui" / "sidebar.py"
OVERVIEW = ROOT / "streamlit_opensea_sales" / "ui" / "market_overview.py"
APP_SOURCE = ROOT / "streamlit_opensea_sales" / "app_opensea_sales.py"
ROADMAP = ROOT / "roadmap" / "otg_analytics_roadmap_english_cta.html"


def test_market_view_has_exact_allowed_values_and_daily_default():
    assert MARKET_VIEW_VALUES == ("daily", "monthly")
    assert normalize_sidebar_view(None) == "daily"
    assert normalize_sidebar_view("unsupported") == "daily"
    assert normalize_sidebar_view("daily") == "daily"
    assert normalize_sidebar_view("monthly") == "monthly"
    assert normalize_overview_view("unsupported") == "daily"


def test_market_view_chart_plan_renders_exactly_four_selected_charts():
    assert get_market_view_chart_plan("daily") == (
        "daily_liquidity",
        "daily_volume",
        "daily_price_range",
        "daily_item_class",
    )
    assert get_market_view_chart_plan("monthly") == (
        "monthly_liquidity",
        "monthly_volume",
        "monthly_price_range",
        "monthly_item_class",
    )
    assert len(get_market_view_chart_plan("daily")) == 4
    assert len(get_market_view_chart_plan("monthly")) == 4
    assert not set(get_market_view_chart_plan("daily")) & set(get_market_view_chart_plan("monthly"))


def test_sidebar_view_control_is_top_level_between_value_display_and_period():
    source = SIDEBAR.read_text(encoding="utf-8")
    value_display = source.index('_render_sidebar_section_start("VALUE DISPLAY", transition=False)')
    view = source.index('_render_sidebar_section_start("VIEW")', value_display)
    period = source.index('_render_sidebar_section_start("PERIOD")', view)
    assert value_display < view < period
    assert 'key="market_view_daily"' in source
    assert 'key="market_view_monthly"' in source
    assert 'type="primary" if current_view == \'daily\'' in source
    assert 'type="primary" if current_view == \'monthly\'' in source
    view_block_end = source.index("if 'market_time_range' not in st.session_state", view)
    assert "st.session_state.market_time_range" not in source[view:view_block_end]


def test_view_is_explicitly_passed_to_market_overview_and_other_state_is_not_reset():
    app_source = APP_SOURCE.read_text(encoding="utf-8")
    sidebar_source = SIDEBAR.read_text(encoding="utf-8")
    overview_source = OVERVIEW.read_text(encoding="utf-8")
    assert "view_mode=market_controls['view']" in app_source
    assert "view_mode: str = \"daily\"" in overview_source
    assert "Changing VIEW does not change the selected PERIOD." in overview_source
    assert "market_time_range = st.session_state.get('market_time_range', '12m')" in overview_source
    assert "market_show_usd" in sidebar_source
    assert "market_show_token_price" in sidebar_source
    assert "market_show_unique_wallets" in sidebar_source


def test_market_renderer_constructs_only_selected_temporal_family():
    source = OVERVIEW.read_text(encoding="utf-8")
    selected_block = source[source.index("if view_mode == \"daily\":"):source.index("if selected_price_range is None:")]
    assert '"daily_liquidity"' in selected_block
    assert '"daily_volume"' in selected_block
    assert '"daily_price_range"' in selected_block
    assert '"daily_item_class"' in selected_block
    assert '"monthly_liquidity"' in selected_block
    assert '"monthly_volume"' in selected_block
    assert '"monthly_price_range"' in selected_block
    assert '"monthly_item_class"' in selected_block
    assert "selected_figures[:2]" in selected_block
    assert "selected_figures[2:]" in selected_block


def test_market_guide_documents_view_without_changing_period():
    source = OVERVIEW.read_text(encoding="utf-8")
    assert "<b>VIEW</b> DAILY shows the daily versions of all four Market charts." in source
    assert "MONTHLY shows the monthly versions." in source
    assert "Changing VIEW does not change the selected PERIOD." in source


def test_roadmap_marks_market_expansion_items_one_through_five_complete():
    source = ROADMAP.read_text(encoding="utf-8")
    expansion = source[source.index("<h3>Market Analytics Expansion</h3>"):source.index("<section class=\"stage s2\"", source.index("<h3>Market Analytics Expansion</h3>"))]
    assert "5 / 5 completed" in expansion
    assert expansion.count('class="card-status completed"') >= 5
    assert "03 / Chart set" in expansion
    assert "04 / Chart set" in expansion
    assert "05 / Mode switch" in expansion
