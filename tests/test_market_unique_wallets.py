import json
import sys
from pathlib import Path

import pandas as pd

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

import market_data_access as mda  # noqa: E402
from charts_market import build_daily_liquidity_chart, build_monthly_liquidity_chart  # noqa: E402
from scripts.build_market_expansion_metrics import build_payload  # noqa: E402


def _sales():
    return pd.DataFrame([
        {"sale_date": "2026-01-01 01:00", "seller": "wallet-a", "buyer": "wallet-b"},
        {"sale_date": "2026-01-01 02:00", "seller": "wallet-b", "buyer": "wallet-a"},
        {"sale_date": "2026-02-01 01:00", "seller": "wallet-c", "buyer": "wallet-c"},
    ])


def test_daily_monthly_union_and_self_trade_count_once():
    daily = pd.DataFrame({"date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-02-01"]), "transactions_count": [2, 0, 1]})
    monthly = pd.DataFrame({"month": ["2026-01", "2026-02"], "month_start": pd.to_datetime(["2026-01-01", "2026-02-01"]), "month_end": pd.to_datetime(["2026-01-31", "2026-02-28"]), "transactions_count": [2, 1]})
    payload = build_payload(_sales(), daily, monthly, "build")
    assert [r["unique_wallets"] for r in payload["unique_wallets"]["daily"]] == [2, 0, 1]
    assert [r["unique_wallets"] for r in payload["unique_wallets"]["monthly"]] == [2, 1]


def test_liquidity_overlays_use_yellow_right_axis_and_integer_tooltip():
    daily = pd.DataFrame({"date": pd.to_datetime(["2026-01-01"]), "transactions_count": [2]})
    wallet_daily = pd.DataFrame({"date": pd.to_datetime(["2026-01-01"]), "unique_wallets": [2]})
    fig = build_daily_liquidity_chart(daily, unique_wallets_df=wallet_daily, show_unique_wallets=True)
    assert len(fig.data) == 2 and fig.data[1].name == "Unique Wallets"
    assert fig.data[1].line.color == "#FFD400"
    assert fig.layout.yaxis2.showline is False and fig.layout.yaxis2.tickfont.color == "#FFD400"
    assert ":,.0f" in fig.data[1].hovertemplate


def test_monthly_wallet_overlay_is_optional_and_secondary():
    monthly = pd.DataFrame({"month": ["2026-01"], "transactions_count": [2]})
    wallet_monthly = pd.DataFrame({"month": ["2026-01"], "unique_wallets": [2]})
    off = build_monthly_liquidity_chart(monthly)
    on = build_monthly_liquidity_chart(monthly, unique_wallets_df=wallet_monthly, show_unique_wallets=True)
    assert len(off.data) == 1
    assert len(on.data) == 2 and on.data[1].yaxis == "y2"
    assert on.layout.yaxis2.showline is False and on.layout.yaxis2.ticks == ""


def test_expansion_loader_rejects_stale_identity(tmp_path, monkeypatch):
    payload = {"schema_version": 1, "source_market_build_id": "old", "source_latest_date": "2026-01-01", "unique_wallets": {"daily": [], "monthly": []}}
    path = tmp_path / "market_expansion_metrics.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(mda, "_get_market_expansion_metrics_path", lambda: path)
    assert mda.load_market_expansion_metrics.__wrapped__(cache_buster="current", expected_source_latest_date="2026-01-01") is None
