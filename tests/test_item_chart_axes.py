import sys
from pathlib import Path

import pandas as pd

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

import charts  # noqa: E402


def _sales():
    return pd.DataFrame([
        {"id": 1, "sale_date": "2026-01-01", "parsed_date": "2026-01-01", "formatted_date": "2026-01-01", "price_gun": 1.0, "price_usd_at_sale": 3.0, "gun_usd_price_at_sale": 3.0, "type": "GUN", "buyer": "a", "seller": "b", "name": "Item", "token_id": "1"},
        {"id": 2, "sale_date": "2026-01-02", "parsed_date": "2026-01-02", "formatted_date": "2026-01-02", "price_gun": 2.0, "price_usd_at_sale": 6.0, "gun_usd_price_at_sale": 3.0, "type": "WGUN", "buyer": "b", "seller": "a", "name": "Item", "token_id": "2"},
    ])


def test_usd_and_gun_axes_are_unlabeled_white_and_spine_free():
    for show_usd in (False, True):
        fig = charts.build_sales_chart(_sales(), False, show_usd, 0.03)
        assert fig.layout.yaxis.title.text is None
        assert fig.layout.xaxis.tickfont.color == "#FFFFFF"
        assert fig.layout.yaxis.tickfont.color == "#FFFFFF"
        assert fig.layout.yaxis.showline is False
        assert len(fig.data) == 2


def test_axis_polish_preserves_wallet_highlight_and_trend_trace():
    trend = pd.DataFrame([{"start_date": "2026-01-01", "end_date": "2026-01-02", "trend_start_price_gun": 1.0, "trend_end_price_gun": 2.0}])
    fig = charts.build_sales_chart(_sales(), False, False, 0.03, show_trend_line=True, trend_df=trend, highlight_wallet="a")
    assert len(fig.data) == 3
    assert "ROLE:" not in str(fig.data[0].customdata[0])
    assert fig.layout.meta["otg_chart_id"] == "item-sales-chart"
    assert charts.wallet_point_outline_colors(_sales().iloc[[1]], "WGUN") == "#B8860B"


def _domain_sales(include_wgun=True, extreme=False):
    rows = [
        {"sale_date": "2026-01-01", "price_gun": 1.0 if not extreme else 1, "type": "GUN", "buyer": "a", "seller": "b"},
        {"sale_date": "2026-01-06", "price_gun": 2.0 if not extreme else 5000, "type": "GUN", "buyer": "b", "seller": "a"},
    ]
    if include_wgun:
        rows.append({"sale_date": "2026-01-11", "price_gun": 3.0 if not extreme else 3, "type": "WGUN", "buyer": "a", "seller": "b"})
    return pd.DataFrame(rows)


def test_trade_domain_includes_gun_and_wgun_and_has_five_percent_padding():
    fig = charts.build_sales_chart(_domain_sales(), False, False, 0.03)
    start, end = fig.layout.xaxis.range
    assert pd.Timestamp(start) == pd.Timestamp("2025-12-31 12:00:00")
    assert pd.Timestamp(end) == pd.Timestamp("2026-01-11 12:00:00")
    without_wgun = charts.build_sales_chart(_domain_sales(False), False, False, 0.03)
    assert pd.Timestamp(without_wgun.layout.xaxis.range[1]) < pd.Timestamp(end)


def test_single_date_and_invalid_trade_dates_are_safe():
    single = pd.DataFrame([{"sale_date": "2026-01-01", "price_gun": 1, "type": "GUN"}, {"sale_date": "2026-01-01", "price_gun": 2, "type": "WGUN"}])
    fig = charts.build_sales_chart(single, False, False, 0.03)
    assert pd.Timestamp(fig.layout.xaxis.range[0]) == pd.Timestamp("2025-12-31")
    assert pd.Timestamp(fig.layout.xaxis.range[1]) == pd.Timestamp("2026-01-02")
    invalid = pd.DataFrame([{"sale_date": "not-a-date", "price_gun": 1, "type": "GUN"}])
    charts.build_sales_chart(invalid, False, False, 0.03)


def test_trend_extrapolates_backend_slope_to_exact_visible_domain_in_both_modes():
    trend = pd.DataFrame([{"start_date": "2026-01-03", "end_date": "2026-01-07", "trend_start_price_gun": 100, "trend_end_price_gun": 140, "trend_start_price_usd": 10, "trend_end_price_usd": 20}])
    for usd in (False, True):
        fig = charts.build_sales_chart(_domain_sales(True, True), False, usd, 0.03, show_trend_line=True, trend_df=trend)
        trace = next(t for t in fig.data if t.name == "Trend Line")
        assert trace.x[0] == fig.layout.xaxis.range[0]
        assert trace.x[-1] == fig.layout.xaxis.range[1]
        slope = (float(trace.y[-1]) - float(trace.y[0])) / ((pd.Timestamp(trace.x[-1]) - pd.Timestamp(trace.x[0])).total_seconds() / 86400)
        assert abs(slope - (10 if not usd else 2.5)) < 1e-9
        assert len(trace.customdata) == 2


def test_trend_invalid_or_zero_duration_produces_no_trend_trace_and_toggle_is_stable():
    base = _domain_sales()
    valid = pd.DataFrame([{"start_date": "2026-01-03", "end_date": "2026-01-07", "trend_start_price_gun": 100, "trend_end_price_gun": 140}])
    assert charts.build_sales_chart(base, False, False, 0.03).layout.xaxis.range == charts.build_sales_chart(base, False, False, 0.03, True, valid).layout.xaxis.range
    for bad in (pd.DataFrame([{"start_date": "2026-01-01", "end_date": "2026-01-01", "trend_start_price_gun": 1, "trend_end_price_gun": 2}]), pd.DataFrame([{"start_date": "bad", "end_date": "2026-01-01", "trend_start_price_gun": 1, "trend_end_price_gun": 2}]), pd.DataFrame([{"start_date": "2026-01-01", "end_date": "2026-01-02", "trend_start_price_gun": float('nan'), "trend_end_price_gun": 2}])):
        fig = charts.build_sales_chart(base, False, False, 0.03, True, bad)
        assert all(t.name != "Trend Line" for t in fig.data)
