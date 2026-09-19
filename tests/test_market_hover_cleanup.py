import sys
from pathlib import Path

import pandas as pd

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

from charts_market import (  # noqa: E402
    build_daily_item_class_chart,
    build_daily_liquidity_chart,
    build_daily_price_range_chart,
    build_daily_volume_chart,
    build_monthly_item_class_chart,
    build_monthly_liquidity_chart,
    build_monthly_price_range_chart,
    build_monthly_volume_chart,
)


def _daily():
    return pd.DataFrame({
        "date": pd.to_datetime(["2026-06-26"]),
        "transactions_count": [24],
        "volume_gun": [12.5],
        "volume_usd": [49.14],
        "token_price_usd": [0.004805],
    })


def _monthly():
    return pd.DataFrame({
        "month": ["2026-06"],
        "month_start": pd.to_datetime(["2026-06-01"]),
        "month_end": pd.to_datetime(["2026-06-30"]),
        "transactions_count": [94],
        "volume_gun": [40.0],
        "volume_usd": [120.0],
        "token_price_usd_avg": [0.004805],
    })


def _price_range_daily():
    return pd.DataFrame({
        "date": pd.to_datetime(["2026-06-26"]),
        "total_sales": [10],
        **{f"B{i}": [i] for i in range(7)},
    })


def _price_range_monthly():
    return pd.DataFrame({
        "month": ["2026-06"],
        "total_sales": [10],
        **{f"B{i}": [i] for i in range(7)},
    })


def _classes_daily():
    return pd.DataFrame({
        "date": pd.to_datetime(["2026-06-26"]),
        "total_sales": [3],
        "customization_item": [1],
        "weapon": [2],
    })


def _classes_monthly():
    return pd.DataFrame({
        "month": ["2026-06"],
        "total_sales": [3],
        "customization_item": [1],
        "weapon": [2],
    })


CLASSES = [
    {"id": "customization_item", "name": "Customization Item", "color": "#FF003A"},
    {"id": "weapon", "name": "Weapon", "color": "#FF8A65"},
]


def test_market_liquidity_hovers_use_only_unified_date_header():
    wallets = pd.DataFrame({"date": _daily()["date"], "unique_wallets": [13]})
    daily = build_daily_liquidity_chart(_daily(), unique_wallets_df=wallets, show_unique_wallets=True)
    monthly = build_monthly_liquidity_chart(
        _monthly(),
        unique_wallets_df=pd.DataFrame({"month": ["2026-06"], "unique_wallets": [13]}),
        show_unique_wallets=True,
    )
    assert all("%{x" not in (trace.hovertemplate or "") for trace in daily.data)
    assert all("%{x" not in (trace.hovertemplate or "") for trace in monthly.data)
    assert "Liquidity:" in daily.data[0].hovertemplate
    assert "Unique Wallets:" in daily.data[1].hovertemplate


def test_market_volume_hovers_only_show_selected_currency_and_optional_token_trace():
    for builder, frame in ((build_daily_volume_chart, _daily()), (build_monthly_volume_chart, _monthly())):
        usd = builder(frame, show_usd=True, show_token_price=False)
        gun = builder(frame, show_usd=False, show_token_price=False)
        usd_token = builder(frame, show_usd=True, show_token_price=True)
        gun_token = builder(frame, show_usd=False, show_token_price=True)

        assert "USD:" in usd.data[0].hovertemplate
        assert "GUN:" not in usd.data[0].hovertemplate
        assert "GUN:" in gun.data[0].hovertemplate
        assert "USD:" not in gun.data[0].hovertemplate
        assert len(usd_token.data) == 2
        assert len(gun_token.data) == 2
        assert "GUN/USD" in usd_token.data[1].hovertemplate
        assert "GUN/USD" in gun_token.data[1].hovertemplate
        assert all("%{x" not in (trace.hovertemplate or "") for trace in usd_token.data + gun_token.data)
        assert len(builder(frame, show_usd=True, show_token_price=False).data) == 1


def test_lower_chart_y_axis_titles_are_removed_but_ticks_remain():
    figures = [
        build_daily_price_range_chart(_price_range_daily()),
        build_monthly_price_range_chart(_price_range_monthly()),
        build_daily_item_class_chart(_classes_daily(), CLASSES),
        build_monthly_item_class_chart(_classes_monthly(), CLASSES),
    ]
    assert all(fig.layout.yaxis.title.text in (None, "") for fig in figures)
    assert all(fig.layout.yaxis.showticklabels is not False for fig in figures)


def test_price_range_and_item_class_unified_hover_contracts_remain_clean():
    price_figures = [
        build_daily_price_range_chart(_price_range_daily()),
        build_monthly_price_range_chart(_price_range_monthly()),
    ]
    class_figures = [
        build_daily_item_class_chart(_classes_daily(), CLASSES),
        build_monthly_item_class_chart(_classes_monthly(), CLASSES),
    ]
    for figure in price_figures + class_figures:
        visible = [trace for trace in figure.data if trace.name != "Total sales"]
        assert len(visible) in (2, 7)
        assert all("%{x" not in (trace.hovertemplate or "") for trace in visible)
        assert all("Total sales" not in (trace.hovertemplate or "") for trace in visible)
        assert sum("Total sales" in (trace.hovertemplate or "") for trace in figure.data) == 1
        assert figure.layout.hovermode == "x unified"
