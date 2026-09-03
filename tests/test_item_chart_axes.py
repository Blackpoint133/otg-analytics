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
    assert "ROLE: BUY" in str(fig.data[0].customdata[0])
    assert charts.wallet_point_outline_colors(_sales().iloc[[1]], "WGUN") == "#B8860B"
