from pathlib import Path
import sys

import pandas as pd

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

from ui.item_overview import _build_item_card_metrics


def test_item_analytics_uses_shared_desktop_panel_height_without_changing_generic_chart():
    item_source = (APP / "ui" / "item_overview.py").read_text(encoding="utf-8")
    chart_source = (APP / "charts.py").read_text(encoding="utf-8")
    assert "ITEM_ANALYTICS_DESKTOP_CARD_HEIGHT = 720" in item_source
    assert "ITEM_ANALYTICS_DESKTOP_CHART_HEIGHT = 750" in item_source
    assert "height: 720px" in item_source
    assert "min-height: 720px" in item_source
    assert "box-sizing: border-box" in item_source
    assert "fig.update_layout(height=ITEM_ANALYTICS_DESKTOP_CHART_HEIGHT)" in item_source
    assert "chart_height = 240 if mobile_layout else 690" in chart_source


def test_item_analytics_panel_preserves_complete_content_and_mobile_flow():
    source = (APP / "ui" / "item_overview.py").read_text(encoding="utf-8")
    assert "SUPPLY" in source and "SUPPLY RANK" in source
    card_css = source[source.index(".item-analytics-card {"):source.index(".item-card-header {")]
    assert "overflow" not in card_css
    assert "overflow:auto" not in source
    assert "mobile_layout" in source


def test_last_sale_price_comes_from_latest_valid_transaction_row():
    frame = pd.DataFrame([
        {"sale_date": "2026-01-01", "price_gun": 999, "price_usd_at_sale": 99},
        {"sale_date": "not-a-date", "price_gun": 777, "price_usd_at_sale": 77},
        {"sale_date": "2026-02-01", "price_gun": 12.5, "price_usd_at_sale": 1.25},
    ])
    frame["seller"] = ["s1", "s2", "s3"]
    frame["buyer"] = ["b1", "b2", "b3"]
    metrics = _build_item_card_metrics(frame, frame, False, 999.0)
    assert metrics["last_sale_price_gun"] == 12.5
    assert metrics["last_sale_price_usd"] == 1.25


def test_last_sale_price_uses_same_row_for_usd_and_handles_missing_usd():
    frame = pd.DataFrame([
        {"sale_date": "2026-01-01", "price_gun": 10, "price_usd_at_sale": 1},
        {"sale_date": "2026-02-01", "price_gun": 20, "price_usd_at_sale": None},
    ])
    frame["seller"] = ["s1", "s2"]
    frame["buyer"] = ["b1", "b2"]
    metrics = _build_item_card_metrics(frame, frame, True, 999.0)
    assert metrics["last_sale_price_gun"] == 20
    assert metrics["last_sale_price_usd"] is None


def test_last_sale_price_card_label_replaces_date_display():
    source = (APP / "ui" / "item_overview.py").read_text(encoding="utf-8")
    assert "LAST SALE PRICE" in source
    assert "<span class=\"item-card-metric-label\">LAST SALE</span>" not in source
    assert "strftime('%Y-%m-%d %H:%M')" not in source


def test_final_item_and_market_guide_copy_is_present():
    item_source = (APP / "ui" / "item_overview.py").read_text(encoding="utf-8")
    market_source = (APP / "ui" / "market_overview.py").read_text(encoding="utf-8")
    assert "PRICING shows average, minimum, maximum and last sale price" in item_source
    assert "GUN sales represent direct purchases of listed items" in item_source
    assert "WGUN sales represent accepted offers" in item_source
    assert "buyer proposed a price" in item_source
    assert "seller accepted the offer" in item_source
    assert "show how many completed sales occurred over time" in market_source
    assert "Liquidity means completed trading activity" in market_source
    assert "not the number or depth of active listings or offers" in market_source
    assert "number of distinct wallets active in those sales" in market_source
    assert "&mdash;" in (market_source + (APP / "ui" / "top_items_overview.py").read_text(encoding="utf-8"))
    assert "&times;" in (APP / "ui" / "top_items_overview.py").read_text(encoding="utf-8")
