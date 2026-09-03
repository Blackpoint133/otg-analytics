import sys
from pathlib import Path

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

from charts_market import (  # noqa: E402
    build_daily_liquidity_chart,
    build_daily_volume_chart,
    build_monthly_liquidity_chart,
    build_monthly_volume_chart,
)
import pandas as pd  # noqa: E402


def _daily():
    return pd.DataFrame({
        "date": pd.to_datetime(["2026-01-01"]),
        "transactions_count": [1], "volume_gun": [2.0],
        "volume_usd": [3.0], "token_price_usd": [0.03],
    })


def _monthly():
    return pd.DataFrame({
        "month": ["2026-01"], "month_start": pd.to_datetime(["2026-01-01"]),
        "month_end": pd.to_datetime(["2026-01-31"]),
        "transactions_count": [1], "volume_gun": [2.0],
        "volume_usd": [3.0], "token_price_usd_avg": [0.03],
    })


def test_market_titles_are_white_and_token_price_axis_line_is_hidden():
    figures = [
        build_daily_liquidity_chart(_daily()),
        build_daily_volume_chart(_daily(), show_token_price=True),
        build_monthly_liquidity_chart(_monthly()),
        build_monthly_volume_chart(_monthly(), show_token_price=True),
    ]
    assert all(fig is not None and fig.layout.title.font.color == "#FFFFFF" for fig in figures)
    for fig in figures:
        assert fig.layout.xaxis.tickfont.color == "#FFFFFF"
        assert fig.layout.yaxis.tickfont.color == "#FFFFFF"
        assert fig.layout.xaxis.showline is False
        assert fig.layout.yaxis.showline is False
        assert fig.layout.yaxis.zeroline is False
    for fig in (figures[1], figures[3]):
        assert fig.layout.yaxis2.showline is False
        assert fig.layout.yaxis2.ticks == ""
        assert fig.layout.yaxis2.tickfont.color == "#AFFF01"
        assert any(trace.name.startswith("GUN/USD") for trace in fig.data)


def test_market_spacing_uses_compact_divider_and_sell_palette_is_updated():
    source = (APP / "ui" / "market_overview.py").read_text(encoding="utf-8")
    charts = (APP / "charts.py").read_text(encoding="utf-8")
    assert 'market-section-divider' in source
    assert source.count('st.markdown("---")') == 2
    assert "SELL_COLOR = '#67C77A'" in charts
    assert "SELL_OUTLINE_COLOR = '#356B44'" in charts


def test_selectbox_outer_border_removed_inner_outline_preserved():
    source = (APP / "ui" / "styles.py").read_text(encoding="utf-8")
    assert '[data-testid="stSelectbox"] {{\n            border-bottom: none !important;' in source
    assert '[data-testid="stSelectbox"] [data-baseweb="select"] > div' in source
    assert 'border-color: var(--otg-border) !important' in source
