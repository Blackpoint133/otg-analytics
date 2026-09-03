"""Build compact Market Analytics KPI summaries from local enriched sales."""

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parents[1] / 'streamlit_opensea_sales'))
from market_data_access import get_market_build_id_from_manifest  # noqa: E402


PERIOD_MONTHS = {'3m': 3, '6m': 6, '12m': 12}


def build_period_summary(sales_df: pd.DataFrame) -> dict:
    required = {'price_gun', 'seller', 'buyer', 'name'}
    if sales_df.empty or not required.issubset(sales_df.columns):
        return {'totals': {'transactions': 0, 'volume_gun': 0.0, 'unique_wallets': 0, 'items_traded': 0},
                'usd_pricing': {'total_volume_usd': 0.0}}
    sellers = set(sales_df['seller'].dropna().unique())
    buyers = set(sales_df['buyer'].dropna().unique())
    usd = sales_df['price_usd_at_sale'].dropna().sum() if 'price_usd_at_sale' in sales_df else 0.0
    return {
        'totals': {
            'transactions': int(len(sales_df)),
            'volume_gun': float(sales_df['price_gun'].sum()),
            'unique_wallets': int(len(sellers | buyers)),
            'items_traded': int(sales_df['name'].nunique()),
        },
        'usd_pricing': {'total_volume_usd': float(usd)},
    }


def build_payload(sales_df: pd.DataFrame, daily_df: pd.DataFrame, source_market_build_id: str = '') -> dict:
    daily_dates = pd.to_datetime(daily_df['date'])
    latest_date = daily_dates.max().normalize()
    periods = {'all': build_period_summary(sales_df)}
    dated = sales_df.copy()
    dated['sale_date'] = pd.to_datetime(dated['sale_date'])
    for period, months in PERIOD_MONTHS.items():
        start = latest_date - pd.DateOffset(months=months)
        filtered = dated[(dated['sale_date'] >= start) & (dated['sale_date'] < latest_date + pd.Timedelta(days=1))]
        periods[period] = build_period_summary(filtered)
    return {
        'schema_version': 1,
        'built_at_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'source_latest_date': latest_date.strftime('%Y-%m-%d'),
        'source_market_build_id': source_market_build_id,
        'periods': periods,
    }


def build_from_directory(data_dir: Path) -> dict:
    sales_dir = data_dir / 'sales_enriched'
    overview_dir = data_dir / 'market_overview_enriched'
    frames = [pd.read_csv(path) for path in sorted(sales_dir.glob('*.csv'))]
    sales_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    daily_df = pd.read_csv(overview_dir / 'daily_market_metrics.csv')
    manifest = json.loads((overview_dir / 'market_overview_enriched_manifest.json').read_text(encoding='utf-8'))
    build_id = get_market_build_id_from_manifest(manifest)
    if not build_id:
        raise RuntimeError('Market manifest has no build identity')
    return build_payload(sales_df, daily_df, build_id)


def publish_atomic(payload: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=output_path.name + '.', suffix='.tmp', dir=output_path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, output_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parents[1] / 'streamlit_opensea_sales' / 'data_opensea_sales')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    payload = build_from_directory(args.data_dir)
    output = args.output or args.data_dir / 'market_overview_enriched' / 'market_period_summaries.json'
    publish_atomic(payload, output)
    print(json.dumps({'output': str(output), 'periods': list(payload['periods'])}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
