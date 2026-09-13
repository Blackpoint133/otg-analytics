from pathlib import Path

ROOT = Path(__file__).parents[1]
APP = ROOT / "streamlit_opensea_sales"


def test_all_analytics_containers_use_one_desktop_alignment_rule():
    source = (APP / "ui" / "styles.py").read_text(encoding="utf-8")
    selector = source[source.index(".st-key-item_main_content"):source.index("/* technical diagnostic text", source.index(".st-key-item_main_content"))]
    assert selector.count(".st-key-") == 4
    assert "margin-top: -44px !important" in selector
    assert "@media (min-width: 769px)" in source


def test_navigation_remains_top_right_without_content_redesign():
    source = (APP / "ui" / "mode_switch.py").read_text(encoding="utf-8")
    assert "otg-top-nav" in source
    assert "ANALYTICS" in source and "ROADMAP" in source
    assert "FEEDBACK" in source and "LOG IN" in source
    assert "justify-content:flex-end" in source
    assert "min-height:36px" in source


def test_mobile_navigation_has_separate_spacing_rule():
    source = (APP / "ui" / "mode_switch.py").read_text(encoding="utf-8")
    assert "@media(max-width:768px)" in source
    assert "min-height:32px" in source and "margin-bottom:8px" in source


def test_sidebar_section_gap_is_seven_pixels_and_label_gap_stays_ten():
    source = (APP / "ui" / "sidebar.py").read_text(encoding="utf-8")
    gap = source[source.index(".otg-sidebar-section-gap"):source.index("</style>", source.index(".otg-sidebar-section-gap"))]
    assert "height: 7px" in gap and "min-height: 7px" in gap
    label = source[source.index(".otg-sidebar-label"):source.index("[data-testid=", source.index(".otg-sidebar-label"))]
    assert "margin: 0 0 10px 0" in label


def test_each_sidebar_uses_shared_section_gap():
    source = (APP / "ui" / "sidebar.py").read_text(encoding="utf-8")
    assert source.count("otg-sidebar-section-gap") >= 12
    assert "height: 14px" not in source


def test_accepted_components_and_frozen_values_remain_intact():
    trader = (APP / "ui" / "trader_search_component" / "index.html").read_bytes()
    item = (APP / "ui" / "item_search_component" / "index.html").read_bytes()
    wallet = (APP / "ui" / "item_wallet_search_component" / "index.html").read_bytes()
    assert trader and item and wallet
    assert "TRADES_COLOR = \"#8F78C6\"" in (APP / "ui" / "trader_overview.py").read_text(encoding="utf-8")
    assert "border-top: 1px solid" in (APP / "ui" / "styles.py").read_text(encoding="utf-8")
