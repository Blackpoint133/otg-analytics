from pathlib import Path


ROOT = Path(__file__).parents[1]
MODE_SWITCH = ROOT / "streamlit_opensea_sales" / "ui" / "mode_switch.py"
APP = ROOT / "streamlit_opensea_sales" / "app_opensea_sales.py"


def test_roadmap_is_caddy_link_not_streamlit_mode():
    source = MODE_SWITCH.read_text(encoding="utf-8")
    assert 'href="/?mode=roadmap"' in source
    assert "otg-top-nav" in source
    assert "otg-nav-analytics" in source
    assert "otg-mode-switch" not in source
    assert "otg-roadmap-pulse" not in source
    assert "#FF9D2E" not in source
    assert "prefers-reduced-motion" in source
    assert 'href="/?mode=item"' in source
    assert 'href="/?mode=market"' in source
    assert 'href="/?mode=top_items"' in source
    assert 'href="/?mode=top_traders"' in source


def test_streamlit_has_no_roadmap_iframe_route():
    source = APP.read_text(encoding="utf-8")
    assert "render_roadmap" not in source
    assert "components.html" not in source
    assert "?mode=roadmap" not in source


def test_caddy_preview_is_local_and_production_route_remains_query_based():
    caddy = Path(r"C:\caddy\Caddyfile").read_text(encoding="utf-8")
    assert "http://127.0.0.1:8085" in caddy
    assert "C:/VAMBAM/Projects/OTG/staging/opensea_sales/roadmap" in caddy
    assert "query mode=roadmap" in caddy
    assert "otgos.run.place" in caddy


def test_top_navigation_has_exact_disabled_controls_and_dropdown_contract():
    source = MODE_SWITCH.read_text(encoding="utf-8")
    assert "st.sidebar.markdown" not in source
    assert "<details class=\"otg-nav-analytics\">" in source
    assert "<summary class=\"otg-top-nav-control\">ANALYTICS" in source
    assert 'title="Coming soon">FEEDBACK' in source
    assert 'title="Coming soon">LOG IN' in source
    assert "otg-nav-disabled" in source
    assert ".otg-nav-analytics:hover .otg-nav-dropdown" in source
    assert ".otg-nav-analytics:focus-within .otg-nav-dropdown" in source
    assert ".otg-nav-analytics[open] .otg-nav-dropdown" in source
    assert "@media(max-width:768px)" in source
    assert "width:176px" in source
    assert "in-game" not in source
    assert "<script" not in source
