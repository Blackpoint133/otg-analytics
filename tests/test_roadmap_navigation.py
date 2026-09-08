from pathlib import Path


ROOT = Path(__file__).parents[1]
MODE_SWITCH = ROOT / "streamlit_opensea_sales" / "ui" / "mode_switch.py"
APP = ROOT / "streamlit_opensea_sales" / "app_opensea_sales.py"


def test_roadmap_is_caddy_link_not_streamlit_mode():
    source = MODE_SWITCH.read_text(encoding="utf-8")
    assert 'href="/?mode=roadmap"' in source
    assert 'target="_self"' in source
    assert "disabled" not in source
    assert "#FF9D2E" in source
    assert "otg-roadmap-pulse" in source
    assert "prefers-reduced-motion" in source
    contract = source.split("def render_mode_switch", 1)[1].split("# Determine active classes", 1)[0]
    assert "roadmap" not in contract


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
