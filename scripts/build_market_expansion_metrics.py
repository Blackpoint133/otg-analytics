"""Build prepared Market Analytics expansion metrics from local sales data."""
import json
import os
import sys
import tempfile
import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1] / 'streamlit_opensea_sales'))
from market_data_access import get_market_build_id_from_manifest  # noqa: E402
from market_price_ranges import build_sales_by_price_range  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from market_snapshot_contract import inspect_market_snapshot  # noqa: E402


def _wallets(frame):
    values = set(frame['seller'].dropna().unique()) | set(frame['buyer'].dropna().unique())
    return len(values)


def build_payload(sales_df: pd.DataFrame, daily_df: pd.DataFrame, monthly_df: pd.DataFrame, build_id: str) -> dict:
    sales = sales_df.copy()
    sales['sale_date'] = pd.to_datetime(sales['sale_date'], errors='coerce', utc=True)
    raw_dates = sales['sale_date'].dropna()
    daily_dates = pd.to_datetime(daily_df['date'], errors='coerce', utc=True).dropna()
    if raw_dates.empty:
        raise ValueError('MARKET_RAW_SALES_DATE_MISSING')
    if daily_dates.empty:
        raise ValueError('MARKET_DAILY_AXIS_DATE_MISSING')
    raw_latest = raw_dates.max().date()
    daily_latest = daily_dates.max().date()
    if raw_latest != daily_latest:
        raise ValueError(
            f'MARKET_BASE_SNAPSHOT_STALE:raw_latest_date={raw_latest}:daily_latest_date={daily_latest}'
        )
    daily_axis = daily_df.copy()
    daily_axis['date'] = pd.to_datetime(daily_axis['date'], errors='coerce', utc=True).dt.normalize()
    daily_rows = []
    for date in daily_axis['date']:
        daily_rows.append({'date': date.strftime('%Y-%m-%d'), 'unique_wallets': _wallets(sales[sales['sale_date'].dt.normalize() == date])})
    monthly_axis = monthly_df.copy()
    monthly_axis['month_start'] = pd.to_datetime(monthly_axis['month_start'], errors='coerce', utc=True).dt.tz_localize(None)
    monthly_axis['month_end'] = pd.to_datetime(monthly_axis['month_end'], errors='coerce', utc=True).dt.tz_localize(None)
    sales['month_start'] = sales['sale_date'].dt.tz_convert('UTC').dt.tz_localize(None).dt.to_period('M').dt.to_timestamp()
    monthly_rows = []
    for _, row in monthly_axis.iterrows():
        frame = sales[sales['month_start'] == row['month_start']]
        monthly_rows.append({'month': str(row.get('month', row['month_start'].strftime('%Y-%m'))),
                             'month_start': row['month_start'].strftime('%Y-%m-%d'),
                             'month_end': row['month_end'].strftime('%Y-%m-%d'),
                             'unique_wallets': _wallets(frame)})
    latest = daily_axis['date'].max().strftime('%Y-%m-%d')
    sales_by_price_range = build_sales_by_price_range(sales, daily_df, monthly_df)
    return {'schema_version': 1, 'built_at_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'source_market_build_id': build_id, 'source_latest_date': latest,
            'unique_wallets': {'daily': daily_rows, 'monthly': monthly_rows},
            'sales_by_price_range': sales_by_price_range}


def build_from_directory(data_dir: Path):
    contract = inspect_market_snapshot(data_dir)
    sales_dir = data_dir / 'sales_enriched'
    overview = data_dir / 'market_overview_enriched'
    frames = [pd.read_csv(p) for p in sorted(sales_dir.glob('*.csv'))]
    sales = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=['sale_date', 'seller', 'buyer'])
    daily = pd.read_csv(overview / 'daily_market_metrics.csv')
    monthly = pd.read_csv(overview / 'monthly_market_metrics.csv')
    manifest = json.loads((overview / 'market_overview_enriched_manifest.json').read_text(encoding='utf-8'))
    build_id = get_market_build_id_from_manifest(manifest)
    if not build_id or build_id != contract['market_build_id']:
        raise RuntimeError('MARKET_BUILD_ID_MISSING')
    return build_payload(sales, daily, monthly, build_id)


def publish_atomic(payload, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=output.name + '.', suffix='.tmp', dir=output.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, output)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parents[1] / 'streamlit_opensea_sales' / 'data_opensea_sales')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    data_dir = args.data_dir
    output = args.output or data_dir / 'market_overview_enriched' / 'market_expansion_metrics.json'
    publish_atomic(build_from_directory(data_dir), output)
    print(output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
