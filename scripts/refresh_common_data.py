"""Synchronize approved OpenSea sales inputs and rebuild dependent snapshots."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

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
    source_dir, target_dir = source / "sales_enriched", target / "sales_enriched"
    if not source_dir.is_dir(): raise FileNotFoundError(source_dir)
    changed = 0
    for item in sorted(source_dir.glob("*.csv")):
        changed += publish_file(item, target_dir / item.name)
    return changed


def run(source: Path, target: Path) -> int:
    source, target = source.resolve(), target.resolve()
    if source == target: raise ValueError("source and target must differ")
    if not source.is_dir(): raise FileNotFoundError(source)
    if not target.is_dir(): raise FileNotFoundError(target)
    changed = sync_sales(source, target)
    py = sys.executable
    stages = [
        [py, str(ROOT / "scripts" / "build_market_period_summaries.py"), "--data-dir", str(target)],
        [py, str(ROOT / "scripts" / "build_market_expansion_metrics.py"), "--data-dir", str(target)],
        [py, str(ROOT / "scripts" / "build_trader_analytics.py"), "--data-dir", str(target)],
    ]
    for command in stages:
        subprocess.run(command, cwd=ROOT, check=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"sync_success source={source} target={target} files_changed={changed}\n")
    return changed


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
