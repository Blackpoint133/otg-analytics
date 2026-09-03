import sys
from pathlib import Path

import pandas as pd

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

import charts
import ui.sidebar as sidebar


def sales_fixture():
    return pd.DataFrame([
        {"sale_date": "2026-01-01", "formatted_date": "2026-01-01", "price_gun": 1.0, "type": "GUN", "buyer": "0xBUY", "seller": "0xSELL"},
        {"sale_date": "2026-01-02", "formatted_date": "2026-01-02", "price_gun": 2.0, "type": "WGUN", "buyer": "0xOTHER", "seller": "0xBUY"},
        {"sale_date": "2026-01-03", "formatted_date": "2026-01-03", "price_gun": 3.0, "type": "GUN", "buyer": "0xSELL", "seller": "0xSELL"},
        {"sale_date": "2026-01-04", "formatted_date": "2026-01-04", "price_gun": 4.0, "type": "WGUN", "buyer": None, "seller": " "},
    ])


def test_wallet_options_union_activity_sort_and_blank_exclusion(monkeypatch, tmp_path):
    path = tmp_path / "item.csv"
    path.write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(sidebar, "load_item_data", lambda *_: sales_fixture())
    result = sidebar._wallet_options_for_item({"file_path": str(path)})
    assert result == ["0xBUY", "0xSELL", "0xOTHER"]


def test_short_wallet_label_keeps_full_value_internal():
    assert sidebar._short_wallet_label("0x1234567890abcdef") == "0x1234…cdef"


def test_default_colors_and_selected_role_colors():
    df = sales_fixture()
    assert charts.wallet_point_colors(df.iloc[[0]], "GUN") == charts.OTG_THEME.accent
    assert charts.wallet_point_colors(df.iloc[[1]], "WGUN") == "#FFD700"
    assert charts.wallet_point_colors(df, "GUN", "0xBUY") == ["#A477C7", "#78B887", "#6B6B73", "#6B6B73"]


def test_selected_role_outlines_are_darker_and_follow_role_family():
    df = sales_fixture()
    assert charts.wallet_point_outline_colors(df, "GUN", "0xBUY") == [
        "#5D397A", "#3F704A", "#3F3F46", "#3F3F46"
    ]
    assert charts.wallet_point_outline_colors(df.iloc[[1]], "WGUN", "0xBUY") == ["#3F704A"]


def test_role_precedence_and_self_trade():
    df = sales_fixture()
    assert charts.classify_wallet_role(df.iloc[0], "0xBUY") == "BUY"
    assert charts.classify_wallet_role(df.iloc[1], "0xBUY") == "SELL"
    assert charts.classify_wallet_role(df.iloc[2], "0xSELL") == "SELF_TRADE"
    assert charts.classify_wallet_role(df.iloc[3], "0xBUY") == "OTHER"


def test_selected_wallet_does_not_filter_points_and_adds_role_tooltip():
    df = sales_fixture()
    fig = charts.build_sales_chart(df, False, False, 0.03, highlight_wallet="0xBUY")
    assert len(fig.data) == 2
    assert sum(len(trace.x) for trace in fig.data) == len(df)
    assert "ROLE: BUY" in str(fig.data[0].customdata[0])
    assert "ROLE: SELL" in str(fig.data[1].customdata[0])
    assert "Token type: WGUN" in str(fig.data[1].customdata[0])


def test_self_trade_tooltip_and_usd_trend_trace_preserved():
    df = sales_fixture()
    trend = pd.DataFrame([{"start_date": "2026-01-01", "end_date": "2026-01-04", "trend_start_price_gun": 1.0, "trend_end_price_gun": 4.0}])
    fig = charts.build_sales_chart(df, False, False, 0.03, show_trend_line=True, trend_df=trend, highlight_wallet="0xSELL")
    assert len(fig.data) == 3
    assert "ROLE: SELF-TRADE" in str(fig.data[0].customdata[1])


def test_chart_source_has_no_external_client_or_table_mutation():
    source = (APP / "charts.py").read_text(encoding="utf-8")
    assert "requests" not in source
    assert "highlight_wallet" in source


def test_chart_ui_theme_and_legend_contract():
    source = (APP / "ui" / "item_overview.py").read_text(encoding="utf-8")
    styles = (APP / "ui" / "sidebar.py").read_text(encoding="utf-8")
    assert "wallet-highlight-legend" not in source
    assert "#080808" in styles
