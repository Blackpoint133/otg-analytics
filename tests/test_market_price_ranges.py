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
    GUN_PRICE_RANGE_BUCKETS,
    PRICE_RANGE_BUCKETS,
    PRICE_RANGE_BUCKET_IDS,
    PRICE_RANGE_COLORS,
    PRICE_RANGE_CONTRACT_VERSION,
    build_sales_by_price_range,
    classify_price_gun,
    classify_price_usd_at_sale,
    payload_to_frames,
    validate_price_range_modes,
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
        {"sale_date": "2026-01-01T00:00:00Z", "price_usd_at_sale": 0.0, "price_gun": 0.0},
        {"sale_date": "2026-01-01T01:00:00Z", "price_usd_at_sale": 0.5, "price_gun": 5.0},
        {"sale_date": "2026-01-02T00:00:00Z", "price_usd_at_sale": 5.0, "price_gun": 25.0},
        {"sale_date": "2026-02-01T00:00:00Z", "price_usd_at_sale": 100.0, "price_gun": 100.0},
        {"sale_date": "2026-02-01T01:00:00Z", "price_usd_at_sale": -1.0, "price_gun": -1.0},
        {"sale_date": "2026-02-01T02:00:00Z", "price_usd_at_sale": float("nan"), "price_gun": float("nan")},
    ])


def test_usd_classification_boundaries_and_invalid_values():
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


def test_gun_classification_boundaries_are_fixed_and_readable():
    cases = [
        (0, "B0"), (4.999999, "B0"), (5, "B1"), (24.999999, "B1"),
        (25, "B2"), (99.999999, "B2"), (100, "B3"), (499.999999, "B3"),
        (500, "B4"), (999.999999, "B4"), (1000, "B5"), (4999.999999, "B5"),
        (5000, "B6"), (320000, "B6"),
    ]
    for value, bucket_id in cases:
        assert classify_price_gun(value) == bucket_id
    assert all("GUN" in bucket["label"] and "$" not in bucket["label"] for bucket in GUN_PRICE_RANGE_BUCKETS)
    assert classify_price_gun(-1) is None
    assert classify_price_gun(float("nan")) is None


def test_prepared_payload_contains_independent_v2_modes_and_reconciles():
    daily, monthly = _axes()
    payload = build_sales_by_price_range(_sales(), daily, monthly)
    assert payload["contract_version"] == PRICE_RANGE_CONTRACT_VERSION == 2
    assert set(payload["modes"]) == {"usd", "gun"}
    for mode in ("usd", "gun"):
        section = payload["modes"][mode]
        assert section["coverage"] == {"total_sales": 6, "valid_sales": 4, "invalid_or_missing_sales": 2}
        assert sum(row["total_sales"] for row in section["daily"]) == 4
        assert sum(row["total_sales"] for row in section["monthly"]) == 4
    assert payload["modes"]["usd"]["canonical_value"] == "price_usd_at_sale"
    assert payload["modes"]["gun"]["canonical_value"] == "price_gun"
    assert validate_sales_by_price_range_payload(payload)


def test_contract_uses_same_ordinal_colors_for_both_modes():
    assert [bucket["color"] for bucket in PRICE_RANGE_BUCKETS] == list(PRICE_RANGE_COLORS)
    assert [bucket["color"] for bucket in GUN_PRICE_RANGE_BUCKETS] == list(PRICE_RANGE_COLORS)


def test_daily_and_monthly_charts_select_same_currency_mode_and_clean_hover():
    daily, monthly = _axes()
    payload = build_sales_by_price_range(_sales(), daily, monthly)
    usd_daily, usd_monthly = payload_to_frames(payload, mode="usd")
    gun_daily, gun_monthly = payload_to_frames(payload, mode="gun")
    usd_daily_fig = build_daily_price_range_chart(usd_daily, mode="usd")
    usd_monthly_fig = build_monthly_price_range_chart(usd_monthly, mode="usd")
    gun_daily_fig = build_daily_price_range_chart(gun_daily, mode="gun")
    gun_monthly_fig = build_monthly_price_range_chart(gun_monthly, mode="gun")
    assert usd_daily_fig.layout.title.text == "Daily Sales by Price Range"
    assert usd_monthly_fig.layout.title.text == "Monthly Sales by Price Range"
    assert gun_daily_fig.layout.title.text == "Daily Sales by Price Range"
    assert gun_monthly_fig.layout.title.text == "Monthly Sales by Price Range"
    assert "USD AT SALE" not in usd_daily_fig.layout.title.text
    for fig, buckets in ((usd_daily_fig, PRICE_RANGE_BUCKETS), (usd_monthly_fig, PRICE_RANGE_BUCKETS),
                         (gun_daily_fig, GUN_PRICE_RANGE_BUCKETS), (gun_monthly_fig, GUN_PRICE_RANGE_BUCKETS)):
        visible = [trace for trace in fig.data if trace.name != "Total sales"]
        assert len(visible) == 7
        assert [trace.name for trace in visible] == [bucket["label"] for bucket in buckets]
        assert [trace.line.color if trace.type == "scatter" else trace.marker.color for trace in visible] == [bucket["color"] for bucket in buckets]
        assert all("Total sales" not in (trace.hovertemplate or "") for trace in visible)
        assert all("%{x" not in (trace.hovertemplate or "") for trace in visible)
        assert all(bucket["label"] in (trace.hovertemplate or "") and "sales" in (trace.hovertemplate or "") for trace, bucket in zip(visible, buckets))
        helpers = [trace for trace in fig.data if trace.name == "Total sales"]
        assert len(helpers) == 1
        assert helpers[0].hovertemplate.count("Total sales") == 1
        assert list(helpers[0].y) == list(fig.data[-1].y)
    assert all(trace.stackgroup == "price_ranges" for trace in usd_daily_fig.data[:7])
    assert all(trace.type == "bar" for trace in gun_monthly_fig.data[:7])
    assert gun_daily_fig.layout.showlegend is False and gun_monthly_fig.layout.showlegend is False


def test_current_snapshot_reconciles_both_price_modes():
    data_dir = Path(__file__).parents[1] / "streamlit_opensea_sales" / "data_opensea_sales"
    payload = build_from_directory(data_dir)["sales_by_price_range"]
    expected = {
        "usd": [4852, 5931, 5608, 1543, 1557, 1932, 874],
        "gun": [204, 6300, 5385, 5168, 1677, 2608, 955],
    }
    for mode in ("usd", "gun"):
        section = payload["modes"][mode]
        assert section["coverage"]["valid_sales"] == 22297
        assert section["coverage"]["invalid_or_missing_sales"] == 0
        totals = {bucket_id: sum(row[bucket_id] for row in section["daily"]) for bucket_id in PRICE_RANGE_BUCKET_IDS}
        assert [totals[bucket_id] for bucket_id in PRICE_RANGE_BUCKET_IDS] == expected[mode]
        assert sum(row["total_sales"] for row in section["monthly"]) == 22297
    assert validate_sales_by_price_range_payload(payload)


def test_loader_preserves_unrelated_expansion_when_one_mode_is_malformed(tmp_path, monkeypatch):
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
    malformed["sales_by_price_range"]["modes"]["gun"]["daily"][0]["B0"] = -1
    path.write_text(json.dumps(malformed), encoding="utf-8")
    loaded = mda.load_market_expansion_metrics.__wrapped__(cache_buster="build", expected_source_latest_date="2026-02-01")
    assert loaded is not None
    assert "sales_by_price_range" in loaded
    assert set(loaded["sales_by_price_range"]["modes"]) == {"usd"}
    assert validate_price_range_modes(loaded["sales_by_price_range"]) == {"usd": True, "gun": False}


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


def test_validator_rejects_extra_row_schema_and_bucket_order():
    daily, monthly = _axes()
    payload = build_sales_by_price_range(_sales(), daily, monthly)
    payload["modes"]["usd"]["daily"][0]["unexpected_bucket"] = 0
    assert not validate_sales_by_price_range_payload(payload)
    payload = build_sales_by_price_range(_sales(), daily, monthly)
    payload["modes"]["gun"]["buckets"] = list(reversed(payload["modes"]["gun"]["buckets"]))
    assert not validate_sales_by_price_range_payload(payload)
