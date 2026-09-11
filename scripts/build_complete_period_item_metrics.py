"""Publish complete per-item market metric artifacts from enriched rankings.

The existing enriched ranking producer already calculates the full active-item
universe and writes the ranking projections.  This wrapper publishes that same
calculated schema under explicit non-ranking artifact names; it never changes
the source ranking files or applies a Top-N limit.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


PERIODS = {"all": "top_items_by_volume_ranking.csv", "30d": "top_items_by_volume_30d.csv", "7d": "top_items_by_volume_7d.csv", "1d": "top_items_by_volume_1d.csv"}


def publish(data_dir: Path) -> list[Path]:
    source_dir = data_dir / "market_overview_enriched"
    outputs = []
    for period, source_name in PERIODS.items():
        source = source_dir / source_name
        if not source.exists():
            raise FileNotFoundError(source)
        target = source_dir / f"top_items_metrics_{period}.csv"
        shutil.copyfile(source, target)
        outputs.append(target)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in publish(args.data_dir):
        print(path)


if __name__ == "__main__":
    main()
