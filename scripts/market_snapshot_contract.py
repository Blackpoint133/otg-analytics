"""Shared freshness contract for the enriched Market snapshot.

The Market chart axis and the derived KPI artifacts must be produced from the
same enriched-sales snapshot.  Keep this validation independent of the
Streamlit readers so refresh and release preparation can fail before any
derived artifact is published.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


MARKET_OVERVIEW_DIRNAME = "market_overview_enriched"
REQUIRED_BASE_FILES = (
    "daily_market_metrics.csv",
    "monthly_market_metrics.csv",
    "market_summary.json",
    "market_overview_enriched_manifest.json",
)
DERIVED_FILES = {
    "market_period_summaries.json",
    "market_expansion_metrics.json",
}


def _raw_latest(data_dir: Path) -> tuple[pd.Timestamp, str]:
    values: list[pd.Timestamp] = []
    for path in sorted((data_dir / "sales_enriched").glob("*.csv")):
        try:
            frame = pd.read_csv(path, usecols=["sale_date"])
            parsed = pd.to_datetime(frame["sale_date"], errors="coerce", utc=True).dropna()
        except (OSError, ValueError, KeyError, pd.errors.ParserError):
            continue
        if not parsed.empty:
            values.append(parsed.max())
    if not values:
        raise ValueError("MARKET_RAW_SALES_DATE_MISSING")
    timestamp = max(values).to_pydatetime()
    return pd.Timestamp(timestamp), timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_date(frame: pd.DataFrame, column: str, error: str) -> pd.Series:
    if column not in frame.columns:
        raise ValueError(error)
    parsed = pd.to_datetime(frame[column], errors="coerce", utc=True).dropna()
    if parsed.empty:
        raise ValueError(error)
    return parsed.dt.normalize()


def inspect_market_snapshot(data_dir: Path) -> dict[str, str]:
    """Return and validate the base Market snapshot's freshness metadata."""

    data_dir = Path(data_dir)
    overview = data_dir / MARKET_OVERVIEW_DIRNAME
    missing = [name for name in REQUIRED_BASE_FILES if not (overview / name).is_file()]
    if missing:
        raise FileNotFoundError("MARKET_BASE_FILE_MISSING:" + ",".join(missing))

    raw_timestamp, raw_timestamp_text = _raw_latest(data_dir)
    raw_date = raw_timestamp.date().isoformat()
    daily = pd.read_csv(overview / "daily_market_metrics.csv")
    daily_dates = _require_date(daily, "date", "MARKET_DAILY_AXIS_DATE_MISSING")
    daily_date = daily_dates.max().date().isoformat()

    monthly = pd.read_csv(overview / "monthly_market_metrics.csv")
    monthly_start = _require_date(monthly, "month_start", "MARKET_MONTHLY_AXIS_MISSING")
    monthly_end = _require_date(monthly, "month_end", "MARKET_MONTHLY_COVERAGE_MISSING")
    raw_day = pd.Timestamp(raw_date, tz="UTC")
    coverage = ((monthly_start <= raw_day) & (monthly_end >= raw_day)).any()
    monthly_coverage_end = monthly_end.max().date().isoformat()
    if not coverage:
        raise ValueError("MARKET_MONTHLY_COVERAGE_MISSING_RAW_LATEST")

    try:
        market_manifest = json.loads(
            (overview / "market_overview_enriched_manifest.json").read_text(encoding="utf-8")
        )
        market_summary = json.loads((overview / "market_summary.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("MARKET_BASE_METADATA_INVALID") from exc
    build_id = str(market_manifest.get("created_at_utc") or market_manifest.get("built_at") or "").strip()
    if not build_id:
        raise ValueError("MARKET_BUILD_ID_MISSING")
    summary_max = str((market_summary.get("date_range") or {}).get("max_sale_date") or "")
    if summary_max and summary_max != raw_date:
        raise ValueError("MARKET_SUMMARY_RAW_DATE_MISMATCH")
    if daily_date != raw_date:
        raise ValueError(
            f"MARKET_BASE_SNAPSHOT_STALE:raw_latest_date={raw_date}:daily_latest_date={daily_date}"
        )

    return {
        "raw_latest_timestamp": raw_timestamp_text,
        "raw_latest_date": raw_date,
        "daily_latest_date": daily_date,
        "monthly_coverage_end": monthly_coverage_end,
        "market_build_id": build_id,
    }


def market_base_files(overview_dir: Path) -> list[Path]:
    """Return all source base files, excluding derived outputs.

    The manifest is deliberately returned last: it is the commit marker for a
    coherent base snapshot after the other files have been published.
    """

    overview_dir = Path(overview_dir)
    files = [
        path
        for path in sorted(overview_dir.iterdir())
        if path.is_file() and path.name not in DERIVED_FILES
    ]
    manifest = overview_dir / "market_overview_enriched_manifest.json"
    if manifest in files:
        files.remove(manifest)
        files.append(manifest)
    return files
