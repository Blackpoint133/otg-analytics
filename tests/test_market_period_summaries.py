import json
import sys
from pathlib import Path

import pandas as pd

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

import market_data_access as mda  # noqa: E402
from ui.market_overview import (  # noqa: E402
    _build_period_market_summary,
    _filter_market_sales_data,
    _get_market_period_bounds,
    _resolve_period_kpi_summary,
)
from scripts.build_market_period_summaries import build_payload  # noqa: E402


def _sales():
    return pd.DataFrame([
        {"sale_date": "2026-01-01", "price_gun": 10, "seller": "s1", "buyer": "b1", "name": "A", "price_usd_at_sale": 1.5},
        {"sale_date": "2025-07-01", "price_gun": 20, "seller": "s2", "buyer": "b1", "name": "B", "price_usd_at_sale": None},
        {"sale_date": "2025-01-01", "price_gun": 30, "seller": "s3", "buyer": "b3", "name": "C", "price_usd_at_sale": 3.0},
    ])


def _daily():
    return pd.DataFrame({"date": pd.to_datetime(["2026-01-01", "2026-01-15"])})


def test_period_bounds_and_payload_match_frontend_semantics():
    sales = _sales()
    sales['sale_date'] = pd.to_datetime(sales['sale_date'])
    daily = _daily()
    payload = build_payload(sales, daily)
    fallback = {"totals": {}, "usd_pricing": {}}
    for period in ("all", "12m", "6m", "3m"):
        start, end, all_time = _get_market_period_bounds(daily, period)
        old = _build_period_market_summary(_filter_market_sales_data(sales, start, end, all_time), fallback)
        assert payload["periods"][period] == old


def test_unique_wallet_union_and_non_null_usd_sum():
    result = build_payload(_sales(), _daily())["periods"]["all"]
    assert result["totals"]["unique_wallets"] == 5
    assert result["usd_pricing"]["total_volume_usd"] == 4.5


def test_summary_loader_validates_schema_and_required_periods(tmp_path, monkeypatch):
    valid = {"schema_version": 1, "source_market_build_id": "build-1", "source_latest_date": "2026-01-15", "periods": {p: {"totals": {"transactions": 1, "volume_gun": 1, "unique_wallets": 1, "items_traded": 1}, "usd_pricing": {"total_volume_usd": 1}} for p in ("all", "12m", "6m", "3m")}}
    path = tmp_path / "market_period_summaries.json"
    path.write_text(json.dumps(valid), encoding="utf-8")
    monkeypatch.setattr(mda, "_get_market_period_summaries_path", lambda: path)
    assert mda.load_market_period_summaries.__wrapped__(cache_buster="build-1", expected_source_latest_date="2026-01-15") == valid
    path.write_text("{bad", encoding="utf-8")
    assert mda.load_market_period_summaries.__wrapped__(cache_buster="build-1", expected_source_latest_date="2026-01-15") is None


def test_fast_path_does_not_call_transaction_loader(monkeypatch):
    valid = {"periods": {"12m": {"totals": {"transactions": 7}, "usd_pricing": {}}}}
    def fail_loader():
        raise AssertionError("slow loader called")
    assert _resolve_period_kpi_summary(valid, "12m", fail_loader, {})["totals"]["transactions"] == 7


def test_stale_summary_uses_fallback():
    fallback = {"totals": {"transactions": 9}, "usd_pricing": {}}
    assert _resolve_period_kpi_summary({"periods": {}}, "12m", lambda: pd.DataFrame(), fallback) == {
        "totals": {"transactions": 0, "volume_gun": 0.0, "unique_wallets": 0, "items_traded": 0},
        "usd_pricing": {"total_volume_usd": 0.0},
    }


def test_summary_file_version_changes_after_replacement(tmp_path, monkeypatch):
    path = tmp_path / "market_period_summaries.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(mda, "_get_market_period_summaries_path", lambda: path)
    first = mda.get_market_period_summaries_file_version()
    path.write_text('{"changed": true, "padding": "x"}', encoding="utf-8")
    assert mda.get_market_period_summaries_file_version() != first
