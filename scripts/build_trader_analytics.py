"""Build the ignored offline trader analytics snapshot from prepared sales."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import os
import sys
import tempfile

import pandas as pd

APP_DIR = Path(__file__).resolve().parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP_DIR))
from trader_analytics import build_snapshot, normalize_trade_events


def load_sales(data_dir: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    sales_dir = data_dir / "sales_enriched"
    frames = []
    unreadable = 0
    for path in sorted(sales_dir.glob("*.csv")):
        try:
            frames.append(pd.read_csv(path))
        except (OSError, ValueError, pd.errors.ParserError):
            unreadable += 1
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()), {"unreadable_files": unreadable, "source_files": len(frames)}


def publish_atomic(payload: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, output)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=APP_DIR / "data_opensea_sales")
    parser.add_argument("--output", type=Path, default=APP_DIR / "data_opensea_sales" / "trader_analytics_snapshot.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    frame, file_diag = load_sales(args.data_dir)
    events, event_diag = normalize_trade_events(frame)
    diagnostics = {**file_diag, **event_diag}
    payload = build_snapshot(events, diagnostics)
    print(json.dumps({"event_count": payload["event_count"], "wallet_count": payload["wallet_count"], "date_min": payload["date_min"], "date_max": payload["date_max"], "coverage": payload["coverage"], "pnl_supported": payload["pnl_supported"]}, sort_keys=True))
    if not args.dry_run:
        publish_atomic(payload, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
