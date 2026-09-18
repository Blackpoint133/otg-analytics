import json
import math
import sys
from pathlib import Path

import pandas as pd

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

import market_data_access as mda  # noqa: E402
from charts_market import build_daily_price_range_chart, build_monthly_price_range_chart  # noqa: E402
from market_price_ranges import (  # noqa: E402
    PRICE_RANGE_BUCKETS,
    PRICE_RANGE_BUCKET_IDS,
    PRICE_RANGE_CANONICAL_VALUE,
    build_sales_by_price_range,
    classify_price_usd_at_sale,
    validate_sales_by_price_range_payload,
)
from scripts.build_market_expansion_metrics import build_from_directory  # noqa: E402


def _axes():
    daily = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03", "2026-02-01"]),
    })
    monthly = pd.DataFrame({
        "month": ["2026-01", "2026-02"],
        "month_start": pd.to_datetime(["2026-01-01", "2026-02-01"]),
        "month_end": pd.to_datetime(["2026-01-31", "2026-02-28"]),
    })
    return daily, monthly


def _sales():
    return pd.DataFrame([
        {"sale_date": "2026-01-01T00:00:00Z", "price_usd_at_sale": 0.0},
        {"sale_date": "2026-01-01T01:00:00Z", "price_usd_at_sale": 0.5},
        {"sale_date": "2026-01-02T00:00:00Z", "price_usd_at_sale": 5.0},
        {"sale_date": "2026-02-01T00:00:00Z", "price_usd_at_sale": 100.0},
        {"sale_date": "2026-02-01T01:00:00Z", "price_usd_at_sale": -1.0},
        {"sale_date": "2026-02-01T02:00:00Z", "price_usd_at_sale": float("nan")},
    ])


def test_classification_boundaries_and_invalid_values():
    cases = [
        (0, "B0"), (0.499999, "B0"), (0.50, "B1"), (0.999999, "B1"),
        (1.00, "B2"), (4.999999, "B2"), (5.00, "B3"), (9.999999, "B3"),
        (10.00, "B4"), (24.999999, "B4"), (25.00, "B5"), (99.999999, "B5"),
        (100.00, "B6"), (10_000_000, "B6"),
    ]
    for value, bucket_id in cases:
        assert classify_price_usd_at_sale(value) == bucket_id
    for value in (-0.01, None, "not-a-price", math.nan, math.inf, -math.inf):
        assert classify_price_usd_at_sale(value) is None


def test_prepared_payload_is_zero_filled_and_reconciles():
    daily, monthly = _axes()
    payload = build_sales_by_price_range(_sales(), daily, monthly)
    assert payload["canonical_value"] == PRICE_RANGE_CANONICAL_VALUE
    assert [bucket["id"] for bucket in payload["buckets"]] == list(PRICE_RANGE_BUCKET_IDS)
    assert payload["coverage"] == {
        "total_sales": 6,
        "valid_sales": 4,
        "invalid_or_missing_sales": 2,
    }
    assert [row["date"] for row in payload["daily"]][:3] == ["2026-01-01", "2026-01-02", "2026-01-03"]
    assert payload["daily"][2]["total_sales"] == 0
    assert sum(row["total_sales"] for row in payload["daily"]) == 4
    assert sum(row["total_sales"] for row in payload["monthly"]) == 4
    assert validate_sales_by_price_range_payload(payload)


def test_contract_uses_fixed_colors_and_is_invariant_to_render_toggles():
    assert [bucket["color"] for bucket in PRICE_RANGE_BUCKETS] == [
        "#5B616A", "#808894", "#AEB5BD", "#D9DDE2", "#FF7A92", "#FF3D66", "#FF003A"
    ]
    first = classify_price_usd_at_sale(5.0)
    second = classify_price_usd_at_sale(5.0)
    assert first == second == "B3"


def test_daily_and_monthly_charts_have_same_fixed_series_contract():
    daily, monthly = _axes()
    payload = build_sales_by_price_range(_sales(), daily, monthly)
    daily_frame = pd.DataFrame(payload["daily"])
    monthly_frame = pd.DataFrame(payload["monthly"])
    daily_fig = build_daily_price_range_chart(daily_frame)
    monthly_fig = build_monthly_price_range_chart(monthly_frame)
    assert len(daily_fig.data) == len(monthly_fig.data) == 7
    assert all(trace.type == "scatter" and trace.stackgroup == "price_ranges" for trace in daily_fig.data)
    assert all(trace.type == "bar" for trace in monthly_fig.data)
    assert monthly_fig.layout.barmode == "stack"
    assert [trace.name for trace in daily_fig.data] == [bucket["label"] for bucket in PRICE_RANGE_BUCKETS]
    assert [trace.name for trace in monthly_fig.data] == [bucket["label"] for bucket in PRICE_RANGE_BUCKETS]
    assert "USD AT SALE" in daily_fig.layout.title.text
    assert "USD AT SALE" in monthly_fig.layout.title.text
    assert "volume" not in (daily_fig.data[0].hovertemplate or "").lower()


def test_current_snapshot_reconciles_expected_counts():
    data_dir = Path(__file__).parents[1] / "streamlit_opensea_sales" / "data_opensea_sales"
    payload = build_from_directory(data_dir)["sales_by_price_range"]
    assert payload["coverage"]["valid_sales"] == 22286
    assert payload["coverage"]["invalid_or_missing_sales"] == 0
    totals = {
        bucket_id: sum(row[bucket_id] for row in payload["daily"])
        for bucket_id in PRICE_RANGE_BUCKET_IDS
    }
    assert [totals[bucket_id] for bucket_id in PRICE_RANGE_BUCKET_IDS] == [4850, 5931, 5599, 1543, 1557, 1932, 874]
    assert validate_sales_by_price_range_payload(payload)


def test_loader_accepts_legacy_expansion_without_price_ranges(tmp_path, monkeypatch):
    payload = {
        "schema_version": 1,
        "source_market_build_id": "build",
        "source_latest_date": "2026-01-01",
        "unique_wallets": {"daily": [], "monthly": []},
    }
    path = tmp_path / "market_expansion_metrics.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(mda, "_get_market_expansion_metrics_path", lambda: path)
    assert mda.load_market_expansion_metrics.__wrapped__(cache_buster="build", expected_source_latest_date="2026-01-01") == payload


def test_loader_rejects_malformed_or_stale_price_range_payload(tmp_path, monkeypatch):
    daily, monthly = _axes()
    price_ranges = build_sales_by_price_range(_sales(), daily, monthly)
    base = {
        "schema_version": 1,
        "source_market_build_id": "build",
        "source_latest_date": "2026-02-01",
        "unique_wallets": {"daily": [], "monthly": []},
        "sales_by_price_range": price_ranges,
    }
    path = tmp_path / "market_expansion_metrics.json"
    monkeypatch.setattr(mda, "_get_market_expansion_metrics_path", lambda: path)
    malformed = json.loads(json.dumps(base))
    malformed["sales_by_price_range"]["daily"][0]["B0"] = -1
    path.write_text(json.dumps(malformed), encoding="utf-8")
    assert mda.load_market_expansion_metrics.__wrapped__(cache_buster="build", expected_source_latest_date="2026-03-01") is None
    path.write_text(json.dumps(base), encoding="utf-8")
    assert mda.load_market_expansion_metrics.__wrapped__(cache_buster="build", expected_source_latest_date="2026-02-01") == base
