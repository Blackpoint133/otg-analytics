from pathlib import Path


APP = Path(__file__).parents[1] / "streamlit_opensea_sales"


def test_item_analytics_uses_shared_desktop_panel_height_without_changing_generic_chart():
    item_source = (APP / "ui" / "item_overview.py").read_text(encoding="utf-8")
    chart_source = (APP / "charts.py").read_text(encoding="utf-8")
    assert "ITEM_ANALYTICS_DESKTOP_PANEL_HEIGHT = 720" in item_source
    assert "height: 720px" in item_source
    assert "min-height: 720px" in item_source
    assert "box-sizing: border-box" in item_source
    assert "fig.update_layout(height=ITEM_ANALYTICS_DESKTOP_PANEL_HEIGHT)" in item_source
    assert "chart_height = 240 if mobile_layout else 690" in chart_source


def test_item_analytics_panel_preserves_complete_content_and_mobile_flow():
    source = (APP / "ui" / "item_overview.py").read_text(encoding="utf-8")
    assert "SUPPLY" in source and "SUPPLY RANK" in source
    card_css = source[source.index(".item-analytics-card {"):source.index(".item-card-header {")]
    assert "overflow" not in card_css
    assert "overflow:auto" not in source
    assert "mobile_layout" in source
