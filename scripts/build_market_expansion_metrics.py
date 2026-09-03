"""Build prepared Market Analytics expansion metrics from local sales data."""
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1] / 'streamlit_opensea_sales'))
from market_data_access import get_market_build_id_from_manifest  # noqa: E402


def _wallets(frame):
    values = set(frame['seller'].dropna().unique()) | set(frame['buyer'].dropna().unique())
    return len(values)


def build_payload(sales_df: pd.DataFrame, daily_df: pd.DataFrame, monthly_df: pd.DataFrame, build_id: str) -> dict:
    sales = sales_df.copy()
    sales['sale_date'] = pd.to_datetime(sales['sale_date'])
    daily_axis = daily_df.copy()
    daily_axis['date'] = pd.to_datetime(daily_axis['date']).dt.normalize()
    daily_rows = []
    for date in daily_axis['date']:
        daily_rows.append({'date': date.strftime('%Y-%m-%d'), 'unique_wallets': _wallets(sales[sales['sale_date'].dt.normalize() == date])})
    monthly_axis = monthly_df.copy()
    monthly_axis['month_start'] = pd.to_datetime(monthly_axis['month_start'])
    monthly_axis['month_end'] = pd.to_datetime(monthly_axis['month_end'])
    sales['month_start'] = sales['sale_date'].dt.to_period('M').dt.to_timestamp()
    monthly_rows = []
    for _, row in monthly_axis.iterrows():
        frame = sales[sales['month_start'] == row['month_start']]
        monthly_rows.append({'month': str(row.get('month', row['month_start'].strftime('%Y-%m'))),
                             'month_start': row['month_start'].strftime('%Y-%m-%d'),
                             'month_end': row['month_end'].strftime('%Y-%m-%d'),
                             'unique_wallets': _wallets(frame)})
    latest = daily_axis['date'].max().strftime('%Y-%m-%d')
    return {'schema_version': 1, 'built_at_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'source_market_build_id': build_id, 'source_latest_date': latest,
            'unique_wallets': {'daily': daily_rows, 'monthly': monthly_rows}}


def build_from_directory(data_dir: Path):
    sales_dir = data_dir / 'sales_enriched'
    overview = data_dir / 'market_overview_enriched'
    frames = [pd.read_csv(p) for p in sorted(sales_dir.glob('*.csv'))]
    sales = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=['sale_date', 'seller', 'buyer'])
    daily = pd.read_csv(overview / 'daily_market_metrics.csv')
    monthly = pd.read_csv(overview / 'monthly_market_metrics.csv')
    manifest = json.loads((overview / 'market_overview_enriched_manifest.json').read_text(encoding='utf-8'))
    build_id = get_market_build_id_from_manifest(manifest)
    if not build_id:
        raise RuntimeError('Market manifest has no build identity')
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


if __name__ == '__main__':
    data_dir = Path(__file__).parents[1] / 'streamlit_opensea_sales' / 'data_opensea_sales'
    output = data_dir / 'market_overview_enriched' / 'market_expansion_metrics.json'
    publish_atomic(build_from_directory(data_dir), output)
    print(output)
