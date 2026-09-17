"""Validate the immutable raw/base/derived data snapshot of a release.

This read-only gate is used against the exact final prepared tree.  It catches
data copied or regenerated after an earlier canary and verifies the hashes and
freshness values recorded in the prepared manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd


INTEGRITY_FILES = {
    "daily_market_metrics": "market_overview_enriched/daily_market_metrics.csv",
    "monthly_market_metrics": "market_overview_enriched/monthly_market_metrics.csv",
    "market_summary": "market_overview_enriched/market_summary.json",
    "market_manifest": "market_overview_enriched/market_overview_enriched_manifest.json",
    "market_period_summaries": "market_overview_enriched/market_period_summaries.json",
    "market_expansion_metrics": "market_overview_enriched/market_expansion_metrics.json",
    "trader_analytics": "trader_analytics_snapshot.json",
    "item_class": "item_class_snapshot.json",
    "supply_v3": "gunzscope_supply_snapshot_v3_provider.json",
    "profiles": "opensea_account_profiles_snapshot.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _raw_values(data_dir: Path) -> tuple[pd.Timestamp, str]:
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
        raise ValueError("PREPARED_RAW_SALES_DATE_MISSING")
    timestamp = max(values).to_pydatetime()
    return pd.Timestamp(timestamp), timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def sales_enriched_snapshot_sha256(data_dir: Path) -> str:
    """Hash sorted relative file names and file hashes, not absolute paths."""

    rows = []
    for path in sorted((data_dir / "sales_enriched").glob("*.csv")):
        rows.append(f"{path.name}\t{sha256_file(path)}\n")
    if not rows:
        raise ValueError("PREPARED_SALES_ENRICHED_EMPTY")
    return hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()


def validate(manifest_path: Path, repo_root: Path, data_dir: Path) -> dict[str, object]:
    sys.path.insert(0, str(Path(repo_root) / "scripts"))
    from market_snapshot_contract import inspect_market_snapshot  # noqa: PLC0415

    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    expected = manifest.get("prepared_data_integrity")
    if not isinstance(expected, dict):
        raise ValueError("PREPARED_DATA_INTEGRITY_MISSING")

    contract = inspect_market_snapshot(data_dir)
    raw_date = contract["raw_latest_date"]
    daily_date = contract["daily_latest_date"]
    monthly_end = contract["monthly_coverage_end"]
    build_id = contract["market_build_id"]
    observed = {
        "prepared_raw_max_sale_timestamp": contract["raw_latest_timestamp"],
        "prepared_raw_max_sale_date": raw_date,
        "prepared_daily_market_max_date": daily_date,
        "prepared_monthly_market_coverage_end": monthly_end,
        "prepared_market_build_id": build_id,
        "sales_enriched_snapshot_sha256": sales_enriched_snapshot_sha256(data_dir),
        "files": {
            name: sha256_file(data_dir / relative_path)
            for name, relative_path in INTEGRITY_FILES.items()
        },
    }
    if observed != expected:
        raise ValueError("PREPARED_DATA_INTEGRITY_MISMATCH")
    if raw_date != daily_date:
        raise ValueError("PREPARED_MARKET_BASE_SNAPSHOT_STALE")
    if not repo_root.is_dir():
        raise FileNotFoundError(repo_root)
    return observed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.manifest, args.repo_root, args.data_dir)
    print(json.dumps({"prepared_data_integrity": result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
