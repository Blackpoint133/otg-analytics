"""Pure Sales by Price Range contract and prepared-artifact helpers."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd


PRICE_RANGE_CONTRACT_VERSION = 1
PRICE_RANGE_CANONICAL_VALUE = "price_usd_at_sale"

PRICE_RANGE_BUCKETS = (
    {"id": "B0", "label": "<$0.50", "lower": 0.00, "upper": 0.50, "color": "#5B616A"},
    {"id": "B1", "label": "$0.50-$0.99", "lower": 0.50, "upper": 1.00, "color": "#808894"},
    {"id": "B2", "label": "$1-$4.99", "lower": 1.00, "upper": 5.00, "color": "#AEB5BD"},
    {"id": "B3", "label": "$5-$9.99", "lower": 5.00, "upper": 10.00, "color": "#D9DDE2"},
    {"id": "B4", "label": "$10-$24.99", "lower": 10.00, "upper": 25.00, "color": "#FF7A92"},
    {"id": "B5", "label": "$25-$99.99", "lower": 25.00, "upper": 100.00, "color": "#FF3D66"},
    {"id": "B6", "label": "$100+", "lower": 100.00, "upper": None, "color": "#FF003A"},
)
PRICE_RANGE_BUCKET_IDS = tuple(bucket["id"] for bucket in PRICE_RANGE_BUCKETS)


def public_bucket_metadata() -> list[dict[str, str]]:
    """Return only the stable public bucket metadata persisted in the artifact."""
    return [
        {"id": bucket["id"], "label": bucket["label"], "color": bucket["color"]}
        for bucket in PRICE_RANGE_BUCKETS
    ]


def classify_price_usd_at_sale(value: Any) -> str | None:
    """Classify one finite, non-negative historical USD value, or return None."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric < 0:
        return None
    for bucket in PRICE_RANGE_BUCKETS:
        lower = bucket["lower"]
        upper = bucket["upper"]
        if numeric >= lower and (upper is None or numeric < upper):
            return bucket["id"]
    return None


def _empty_bucket_counts() -> dict[str, int]:
    return {bucket_id: 0 for bucket_id in PRICE_RANGE_BUCKET_IDS}


def _row_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts = _empty_bucket_counts()
    for bucket_id, count in frame.get("bucket_id", pd.Series(dtype=str)).value_counts().items():
        if bucket_id in counts:
            counts[bucket_id] = int(count)
    counts["total_sales"] = int(sum(counts.values()))
    return counts


def _build_daily_rows(valid: pd.DataFrame, daily_df: pd.DataFrame) -> list[dict[str, Any]]:
    axis = pd.to_datetime(daily_df["date"], errors="coerce", utc=True).dropna()
    if axis.empty:
        raise ValueError("MARKET_DAILY_AXIS_DATE_MISSING")
    days = pd.date_range(axis.min().normalize(), axis.max().normalize(), freq="D", tz="UTC")
    grouped = valid.groupby(["sale_day", "bucket_id"], dropna=False).size()
    rows = []
    for day in days:
        counts = _empty_bucket_counts()
        for bucket_id in PRICE_RANGE_BUCKET_IDS:
            counts[bucket_id] = int(grouped.get((day, bucket_id), 0))
        counts["date"] = day.strftime("%Y-%m-%d")
        counts["total_sales"] = int(sum(counts[bucket_id] for bucket_id in PRICE_RANGE_BUCKET_IDS))
        rows.append({"date": counts.pop("date"), **counts})
    return rows


def _build_monthly_rows(valid: pd.DataFrame, monthly_df: pd.DataFrame) -> list[dict[str, Any]]:
    starts = pd.to_datetime(monthly_df["month_start"], errors="coerce", utc=True).dropna()
    if starts.empty:
        raise ValueError("MARKET_MONTHLY_AXIS_MISSING")
    first = starts.min().tz_convert("UTC").tz_localize(None).to_period("M").to_timestamp()
    last = starts.max().tz_convert("UTC").tz_localize(None).to_period("M").to_timestamp()
    months = pd.date_range(first, last, freq="MS")
    grouped = valid.groupby(["sale_month", "bucket_id"], dropna=False).size()
    rows = []
    for month_start in months:
        counts = _empty_bucket_counts()
        for bucket_id in PRICE_RANGE_BUCKET_IDS:
            counts[bucket_id] = int(grouped.get((month_start, bucket_id), 0))
        month_end = month_start + pd.offsets.MonthEnd(1)
        rows.append({
            "month": month_start.strftime("%Y-%m"),
            "month_start": month_start.strftime("%Y-%m-%d"),
            "month_end": month_end.strftime("%Y-%m-%d"),
            **counts,
            "total_sales": int(sum(counts[bucket_id] for bucket_id in PRICE_RANGE_BUCKET_IDS)),
        })
    return rows


def build_sales_by_price_range(
    sales_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    monthly_df: pd.DataFrame,
) -> dict[str, Any]:
    """Build the small prepared daily/monthly price-range artifact."""
    sales = sales_df.copy()
    if "sale_date" not in sales.columns:
        raise ValueError("PRICE_RANGE_SALE_DATE_MISSING")
    sale_dates = pd.to_datetime(sales["sale_date"], errors="coerce", utc=True)
    if sale_dates.isna().any():
        raise ValueError("PRICE_RANGE_SALE_DATE_INVALID")

    if PRICE_RANGE_CANONICAL_VALUE in sales.columns:
        canonical = pd.to_numeric(sales[PRICE_RANGE_CANONICAL_VALUE], errors="coerce")
    else:
        canonical = pd.Series(float("nan"), index=sales.index)
    valid_price = canonical.notna() & canonical.map(math.isfinite) & (canonical >= 0)
    valid = pd.DataFrame({
        "sale_day": sale_dates.dt.normalize(),
        "sale_month": sale_dates.dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("M").dt.to_timestamp(),
        "bucket_id": canonical.map(classify_price_usd_at_sale),
    })[valid_price].copy()

    daily_rows = _build_daily_rows(valid, daily_df)
    monthly_rows = _build_monthly_rows(valid, monthly_df)
    valid_count = int(valid_price.sum())
    invalid_count = int(len(sales) - valid_count)
    daily_total = int(sum(row["total_sales"] for row in daily_rows))
    monthly_total = int(sum(row["total_sales"] for row in monthly_rows))
    if daily_total != valid_count or monthly_total != valid_count:
        raise ValueError("PRICE_RANGE_TOTAL_RECONCILIATION_FAILED")

    return {
        "contract_version": PRICE_RANGE_CONTRACT_VERSION,
        "canonical_value": PRICE_RANGE_CANONICAL_VALUE,
        "buckets": public_bucket_metadata(),
        "coverage": {
            "total_sales": int(len(sales)),
            "valid_sales": valid_count,
            "invalid_or_missing_sales": invalid_count,
        },
        "daily": daily_rows,
        "monthly": monthly_rows,
    }


def validate_sales_by_price_range_payload(
    payload: Any,
    *,
    expected_source_latest_date: str = "",
) -> bool:
    """Fail-closed validation for the prepared price-range section."""
    if not isinstance(payload, dict):
        return False
    if payload.get("contract_version") != PRICE_RANGE_CONTRACT_VERSION:
        return False
    if payload.get("canonical_value") != PRICE_RANGE_CANONICAL_VALUE:
        return False
    if payload.get("buckets") != public_bucket_metadata():
        return False
    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        return False
    coverage_keys = {"total_sales", "valid_sales", "invalid_or_missing_sales"}
    if set(coverage) != coverage_keys:
        return False
    if any(not isinstance(coverage[key], int) or isinstance(coverage[key], bool) or coverage[key] < 0 for key in coverage_keys):
        return False
    if coverage["valid_sales"] + coverage["invalid_or_missing_sales"] != coverage["total_sales"]:
        return False

    daily = payload.get("daily")
    monthly = payload.get("monthly")
    if not isinstance(daily, list) or not isinstance(monthly, list) or not daily or not monthly:
        return False
    if expected_source_latest_date and daily[-1].get("date") != expected_source_latest_date:
        return False

    def valid_count(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0

    def validate_rows(rows: list[dict[str, Any]], required: tuple[str, ...]) -> bool:
        previous = ""
        total = 0
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(required):
                return False
            ordering_key = str(row[required[0]])
            if not ordering_key or ordering_key <= previous:
                return False
            previous = ordering_key
            if any(not valid_count(row[bucket_id]) for bucket_id in PRICE_RANGE_BUCKET_IDS):
                return False
            if not valid_count(row["total_sales"]):
                return False
            if row["total_sales"] != sum(row[bucket_id] for bucket_id in PRICE_RANGE_BUCKET_IDS):
                return False
            total += row["total_sales"]
        return total == coverage["valid_sales"]

    daily_required = ("date", *PRICE_RANGE_BUCKET_IDS, "total_sales")
    monthly_required = ("month", "month_start", "month_end", *PRICE_RANGE_BUCKET_IDS, "total_sales")
    return validate_rows(daily, daily_required) and validate_rows(monthly, monthly_required)


def payload_to_frames(payload: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convert a validated prepared section into chart-ready small frames."""
    daily = pd.DataFrame(payload.get("daily", []))
    monthly = pd.DataFrame(payload.get("monthly", []))
    if not daily.empty:
        daily["date"] = pd.to_datetime(daily["date"], errors="coerce", utc=True).dt.tz_localize(None)
    if not monthly.empty:
        monthly["month_start"] = pd.to_datetime(monthly["month_start"], errors="coerce", utc=True).dt.tz_localize(None)
        monthly["month_end"] = pd.to_datetime(monthly["month_end"], errors="coerce", utc=True).dt.tz_localize(None)
    return daily, monthly
