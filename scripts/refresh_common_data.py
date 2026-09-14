"""Synchronize approved OpenSea sales inputs and rebuild dependent snapshots."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "streamlit_opensea_sales"
LOG = ROOT.parent.parent / "DEV" / "staging_runtime" / "common_data_sync.log"


def publish_file(source: Path, target: Path) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and source.stat().st_size == target.stat().st_size and source.read_bytes() == target.read_bytes():
        return False
    fd, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as out, source.open("rb") as src:
            shutil.copyfileobj(src, out)
            out.flush(); os.fsync(out.fileno())
        os.replace(name, target)
    finally:
        if os.path.exists(name): os.unlink(name)
    return True


def sync_sales(source: Path, target: Path) -> int:
    source_dir, target_dir = source / "sales", target / "sales"
    enriched_source_dir, enriched_target_dir = source / "sales_enriched", target / "sales_enriched"
    if not source_dir.is_dir(): raise FileNotFoundError(source_dir)
    if not enriched_source_dir.is_dir(): raise FileNotFoundError(enriched_source_dir)
    changed = 0
    target_dir.mkdir(parents=True, exist_ok=True)
    enriched_target_dir.mkdir(parents=True, exist_ok=True)
    for item in sorted(source_dir.glob("*.csv")):
        changed += publish_file(item, target_dir / item.name)
    for item in sorted(enriched_source_dir.glob("*.csv")):
        changed += publish_file(item, enriched_target_dir / item.name)
    return changed


def get_sales_date_max(data_dir: Path):
    """Return the maximum valid, timezone-aware sale_date in enriched sales."""
    values = []
    for path in sorted((data_dir / "sales_enriched").glob("*.csv")):
        try:
            frame = pd.read_csv(path, usecols=["sale_date"])
        except (OSError, ValueError, pd.errors.ParserError):
            continue
        parsed = pd.to_datetime(frame["sale_date"], errors="coerce", utc=True).dropna()
        if not parsed.empty:
            values.append(parsed.max())
    return max(values) if values else None


def validate_snapshot(target: Path, target_date) -> None:
    path = target / "trader_analytics_snapshot.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    snapshot_date = pd.to_datetime(payload.get("date_max"), errors="coerce", utc=True)
    if pd.isna(snapshot_date) or snapshot_date < target_date:
        raise ValueError("trader snapshot is older than refreshed sales")


def write_log(*, status: str, duration: float, source_date=None, target_date=None,
              changed=None, stage=None, error_type=None) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    if status == "success":
        line = (f"status=success source_date_max={source_date.isoformat()} "
                f"target_date_max={target_date.isoformat()} files_changed={changed} "
                f"duration_seconds={duration:.3f}\n")
    else:
        line = (f"status=failed stage={stage} error_type={error_type} "
                f"duration_seconds={duration:.3f}\n")
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(line)


def run(source: Path, target: Path) -> int:
    started = time.monotonic()
    source, target = source.resolve(), target.resolve()
    stage = "source_freshness"
    try:
        if source == target: raise ValueError("source and target must differ")
        if not source.is_dir(): raise FileNotFoundError(source)
        if not target.is_dir(): raise FileNotFoundError(target)
        source_date = get_sales_date_max(source)
        if source_date is None: raise ValueError("source has no parseable sale dates")
        stage = "sync"
        changed = sync_sales(source, target)
        stage = "target_freshness"
        target_date = get_sales_date_max(target)
        if target_date is None or target_date < source_date:
            raise ValueError("target sales are older than source")
        py = sys.executable
        stages = [
            ("market_period", "build_market_period_summaries.py"),
            ("market_expansion", "build_market_expansion_metrics.py"),
            ("trader", "build_trader_analytics.py"),
        ]
        for stage, builder in stages:
            subprocess.run([py, str(ROOT / "scripts" / builder), "--data-dir", str(target)], cwd=ROOT, check=True)
        stage = "snapshot_validation"
        validate_snapshot(target, target_date)
        write_log(status="success", source_date=source_date, target_date=target_date,
                  changed=changed, duration=time.monotonic() - started)
        return changed
    except Exception as exc:
        write_log(status="failed", stage=stage, error_type=type(exc).__name__,
                  duration=time.monotonic() - started)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args.source, args.target)
    except Exception as exc:
        print(f"refresh_common_data failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
