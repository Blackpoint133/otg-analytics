"""Pure Sales by Price Range contracts and prepared-artifact helpers."""

from __future__ import annotations

import copy
import math
from typing import Any

import pandas as pd


PRICE_RANGE_CONTRACT_VERSION = 2
PRICE_RANGE_CANONICAL_VALUE = "price_usd_at_sale"  # Backward-compatible USD alias.
PRICE_RANGE_MODES = ("usd", "gun")
PRICE_RANGE_COLORS = (
    "#5B616A", "#808894", "#AEB5BD", "#D9DDE2",
    "#FF7A92", "#FF3D66", "#FF003A",
)

USD_PRICE_RANGE_BUCKETS = (
    {"id": "B0", "label": "<$0.50", "lower": 0.00, "upper": 0.50, "color": PRICE_RANGE_COLORS[0]},
    {"id": "B1", "label": "$0.50-$0.99", "lower": 0.50, "upper": 1.00, "color": PRICE_RANGE_COLORS[1]},
    {"id": "B2", "label": "$1-$4.99", "lower": 1.00, "upper": 5.00, "color": PRICE_RANGE_COLORS[2]},
    {"id": "B3", "label": "$5-$9.99", "lower": 5.00, "upper": 10.00, "color": PRICE_RANGE_COLORS[3]},
    {"id": "B4", "label": "$10-$24.99", "lower": 10.00, "upper": 25.00, "color": PRICE_RANGE_COLORS[4]},
    {"id": "B5", "label": "$25-$99.99", "lower": 25.00, "upper": 100.00, "color": PRICE_RANGE_COLORS[5]},
    {"id": "B6", "label": "$100+", "lower": 100.00, "upper": None, "color": PRICE_RANGE_COLORS[6]},
)

# Fixed round thresholds selected from the current DEV distribution.  These
# are recorded transaction values, not conversions using the current token
# price.
GUN_PRICE_RANGE_BUCKETS = (
    {"id": "B0", "label": "<5 GUN", "lower": 0.00, "upper": 5.00, "color": PRICE_RANGE_COLORS[0]},
    {"id": "B1", "label": "5-24 GUN", "lower": 5.00, "upper": 25.00, "color": PRICE_RANGE_COLORS[1]},
    {"id": "B2", "label": "25-99 GUN", "lower": 25.00, "upper": 100.00, "color": PRICE_RANGE_COLORS[2]},
    {"id": "B3", "label": "100-499 GUN", "lower": 100.00, "upper": 500.00, "color": PRICE_RANGE_COLORS[3]},
    {"id": "B4", "label": "500-999 GUN", "lower": 500.00, "upper": 1000.00, "color": PRICE_RANGE_COLORS[4]},
    {"id": "B5", "label": "1K-4.9K GUN", "lower": 1000.00, "upper": 5000.00, "color": PRICE_RANGE_COLORS[5]},
    {"id": "B6", "label": "5K+ GUN", "lower": 5000.00, "upper": None, "color": PRICE_RANGE_COLORS[6]},
)

# Existing imports use these names. USD remains the default when no mode is
# explicitly supplied, while mode-specific accessors are authoritative.
PRICE_RANGE_BUCKETS = USD_PRICE_RANGE_BUCKETS
PRICE_RANGE_BUCKET_IDS = tuple(bucket["id"] for bucket in USD_PRICE_RANGE_BUCKETS)
_MODE_DEFINITIONS = {
    "usd": {"canonical_value": "price_usd_at_sale", "buckets": USD_PRICE_RANGE_BUCKETS},
    "gun": {"canonical_value": "price_gun", "buckets": GUN_PRICE_RANGE_BUCKETS},
}


def get_price_range_buckets(mode: str = "usd") -> tuple[dict[str, Any], ...]:
    if mode not in _MODE_DEFINITIONS:
        raise ValueError(f"PRICE_RANGE_MODE_INVALID:{mode}")
    return _MODE_DEFINITIONS[mode]["buckets"]


def get_price_range_canonical_value(mode: str = "usd") -> str:
    if mode not in _MODE_DEFINITIONS:
        raise ValueError(f"PRICE_RANGE_MODE_INVALID:{mode}")
    return _MODE_DEFINITIONS[mode]["canonical_value"]


def _bucket_ids(mode: str = "usd") -> tuple[str, ...]:
    return tuple(bucket["id"] for bucket in get_price_range_buckets(mode))


def public_bucket_metadata(mode: str = "usd") -> list[dict[str, str]]:
    """Return only stable public metadata persisted in the artifact."""
    return [
        {"id": bucket["id"], "label": bucket["label"], "color": bucket["color"]}
        for bucket in get_price_range_buckets(mode)
    ]


def _classify(value: Any, buckets: tuple[dict[str, Any], ...]) -> str | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric < 0:
        return None
    for bucket in buckets:
        lower = bucket["lower"]
        upper = bucket["upper"]
        if numeric >= lower and (upper is None or numeric < upper):
            return bucket["id"]
    return None


def classify_price_usd_at_sale(value: Any) -> str | None:
    """Classify one finite, non-negative historical USD value."""
    return _classify(value, USD_PRICE_RANGE_BUCKETS)


def classify_price_gun(value: Any) -> str | None:
    """Classify one finite, non-negative recorded GUN transaction value."""
    return _classify(value, GUN_PRICE_RANGE_BUCKETS)


def _empty_bucket_counts(bucket_ids: tuple[str, ...]) -> dict[str, int]:
    return {bucket_id: 0 for bucket_id in bucket_ids}


def _build_daily_rows(valid: pd.DataFrame, daily_df: pd.DataFrame, bucket_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    axis = pd.to_datetime(daily_df["date"], errors="coerce", utc=True).dropna()
    if axis.empty:
        raise ValueError("MARKET_DAILY_AXIS_DATE_MISSING")
    days = pd.date_range(axis.min().normalize(), axis.max().normalize(), freq="D", tz="UTC")
    grouped = valid.groupby(["sale_day", "bucket_id"], dropna=False).size()
    rows = []
    for day in days:
        counts = _empty_bucket_counts(bucket_ids)
        for bucket_id in bucket_ids:
            counts[bucket_id] = int(grouped.get((day, bucket_id), 0))
        rows.append({"date": day.strftime("%Y-%m-%d"), **counts, "total_sales": int(sum(counts.values()))})
    return rows


def _build_monthly_rows(valid: pd.DataFrame, monthly_df: pd.DataFrame, bucket_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    starts = pd.to_datetime(monthly_df["month_start"], errors="coerce", utc=True).dropna()
    if starts.empty:
        raise ValueError("MARKET_MONTHLY_AXIS_MISSING")
    first = starts.min().tz_convert("UTC").tz_localize(None).to_period("M").to_timestamp()
    last = starts.max().tz_convert("UTC").tz_localize(None).to_period("M").to_timestamp()
    months = pd.date_range(first, last, freq="MS")
    grouped = valid.groupby(["sale_month", "bucket_id"], dropna=False).size()
    rows = []
    for month_start in months:
        counts = _empty_bucket_counts(bucket_ids)
        for bucket_id in bucket_ids:
            counts[bucket_id] = int(grouped.get((month_start, bucket_id), 0))
        month_end = month_start + pd.offsets.MonthEnd(1)
        rows.append({
            "month": month_start.strftime("%Y-%m"),
            "month_start": month_start.strftime("%Y-%m-%d"),
            "month_end": month_end.strftime("%Y-%m-%d"),
            **counts,
            "total_sales": int(sum(counts.values())),
        })
    return rows


def _build_mode(sales: pd.DataFrame, sale_dates: pd.Series, daily_df: pd.DataFrame, monthly_df: pd.DataFrame, mode: str) -> dict[str, Any]:
    canonical_name = get_price_range_canonical_value(mode)
    bucket_ids = _bucket_ids(mode)
    canonical = pd.to_numeric(sales.get(canonical_name, pd.Series(float("nan"), index=sales.index)), errors="coerce")
    valid_price = canonical.notna() & canonical.map(math.isfinite) & (canonical >= 0)
    classifier = classify_price_usd_at_sale if mode == "usd" else classify_price_gun
    valid = pd.DataFrame({
        "sale_day": sale_dates.dt.normalize(),
        "sale_month": sale_dates.dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("M").dt.to_timestamp(),
        "bucket_id": canonical.map(classifier),
    })[valid_price].copy()
    daily_rows = _build_daily_rows(valid, daily_df, bucket_ids)
    monthly_rows = _build_monthly_rows(valid, monthly_df, bucket_ids)
    valid_count = int(valid_price.sum())
    invalid_count = int(len(sales) - valid_count)
    if sum(row["total_sales"] for row in daily_rows) != valid_count or sum(row["total_sales"] for row in monthly_rows) != valid_count:
        raise ValueError(f"PRICE_RANGE_TOTAL_RECONCILIATION_FAILED:{mode}")
    return {
        "canonical_value": canonical_name,
        "buckets": public_bucket_metadata(mode),
        "coverage": {"total_sales": int(len(sales)), "valid_sales": valid_count, "invalid_or_missing_sales": invalid_count},
        "daily": daily_rows,
        "monthly": monthly_rows,
    }


def build_sales_by_price_range(sales_df: pd.DataFrame, daily_df: pd.DataFrame, monthly_df: pd.DataFrame) -> dict[str, Any]:
    """Build both stable historical USD and recorded-GUN price families."""
    sales = sales_df.copy()
    if "sale_date" not in sales.columns:
        raise ValueError("PRICE_RANGE_SALE_DATE_MISSING")
    sale_dates = pd.to_datetime(sales["sale_date"], errors="coerce", utc=True)
    if sale_dates.isna().any():
        raise ValueError("PRICE_RANGE_SALE_DATE_INVALID")
    return {
        "contract_version": PRICE_RANGE_CONTRACT_VERSION,
        "modes": {mode: _build_mode(sales, sale_dates, daily_df, monthly_df, mode) for mode in PRICE_RANGE_MODES},
    }


def _valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate_mode_payload(payload: Any, mode: str, *, expected_source_latest_date: str = "") -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("canonical_value") != get_price_range_canonical_value(mode):
        return False
    if payload.get("buckets") != public_bucket_metadata(mode):
        return False
    coverage = payload.get("coverage")
    if not isinstance(coverage, dict) or set(coverage) != {"total_sales", "valid_sales", "invalid_or_missing_sales"}:
        return False
    if any(not _valid_count(coverage[key]) for key in coverage):
        return False
    if coverage["valid_sales"] + coverage["invalid_or_missing_sales"] != coverage["total_sales"]:
        return False
    daily = payload.get("daily")
    monthly = payload.get("monthly")
    if not isinstance(daily, list) or not isinstance(monthly, list) or not daily or not monthly:
        return False
    if expected_source_latest_date and (
        not isinstance(daily[-1], dict) or daily[-1].get("date") != expected_source_latest_date
    ):
        return False
    bucket_ids = _bucket_ids(mode)

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
            if any(not _valid_count(row[bucket_id]) for bucket_id in bucket_ids):
                return False
            if not _valid_count(row["total_sales"]):
                return False
            if row["total_sales"] != sum(row[bucket_id] for bucket_id in bucket_ids):
                return False
            total += row["total_sales"]
        return total == coverage["valid_sales"]

    daily_required = ("date", *bucket_ids, "total_sales")
    monthly_required = ("month", "month_start", "month_end", *bucket_ids, "total_sales")
    return validate_rows(daily, daily_required) and validate_rows(monthly, monthly_required)


def _validate_legacy_payload(payload: Any, *, expected_source_latest_date: str = "") -> bool:
    if not isinstance(payload, dict) or payload.get("contract_version") != 1:
        return False
    return _validate_mode_payload(payload, "usd", expected_source_latest_date=expected_source_latest_date)


def validate_price_range_modes(payload: Any, *, expected_source_latest_date: str = "") -> dict[str, bool]:
    """Return independent validation results for each v2 mode."""
    if not isinstance(payload, dict) or payload.get("contract_version") != PRICE_RANGE_CONTRACT_VERSION:
        return {mode: False for mode in PRICE_RANGE_MODES}
    modes = payload.get("modes")
    if not isinstance(modes, dict):
        return {mode: False for mode in PRICE_RANGE_MODES}
    return {mode: _validate_mode_payload(modes.get(mode), mode, expected_source_latest_date=expected_source_latest_date) for mode in PRICE_RANGE_MODES}


def sanitize_sales_by_price_range_payload(payload: Any, *, expected_source_latest_date: str = "") -> dict[str, Any] | None:
    """Keep only independently valid modes, preserving fail-soft expansion data."""
    if _validate_legacy_payload(payload, expected_source_latest_date=expected_source_latest_date):
        return payload
    results = validate_price_range_modes(payload, expected_source_latest_date=expected_source_latest_date)
    if not any(results.values()):
        return None
    sanitized = copy.deepcopy(payload)
    sanitized["modes"] = {mode: payload["modes"][mode] for mode, valid in results.items() if valid}
    return sanitized


def validate_sales_by_price_range_payload(payload: Any, *, expected_source_latest_date: str = "") -> bool:
    """Fail-closed validation requiring every published v2 mode to be valid."""
    if _validate_legacy_payload(payload, expected_source_latest_date=expected_source_latest_date):
        return True
    return all(validate_price_range_modes(payload, expected_source_latest_date=expected_source_latest_date).values())


def payload_to_frames(payload: dict[str, Any], mode: str = "usd") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convert one validated prepared mode into chart-ready small frames."""
    if payload.get("contract_version") == 1:
        if mode != "usd" or not _validate_legacy_payload(payload):
            raise ValueError("PRICE_RANGE_MODE_UNAVAILABLE")
        selected = payload
    else:
        selected = payload.get("modes", {}).get(mode)
        if selected is None or not _validate_mode_payload(selected, mode):
            raise ValueError("PRICE_RANGE_MODE_UNAVAILABLE")
    daily = pd.DataFrame(selected.get("daily", []))
    monthly = pd.DataFrame(selected.get("monthly", []))
    if not daily.empty:
        daily["date"] = pd.to_datetime(daily["date"], errors="coerce", utc=True).dt.tz_localize(None)
    if not monthly.empty:
        monthly["month_start"] = pd.to_datetime(monthly["month_start"], errors="coerce", utc=True).dt.tz_localize(None)
        monthly["month_end"] = pd.to_datetime(monthly["month_end"], errors="coerce", utc=True).dt.tz_localize(None)
    return daily, monthly
