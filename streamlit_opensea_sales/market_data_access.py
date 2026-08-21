"""
Market Data Access Layer.

technical diagnostic text technical diagnostic text market overview outputs technical diagnostic text data_opensea_sales/market_overview/ technical diagnostic text market_overview_enriched/.
technical diagnostic text technical diagnostic text technical diagnostic text:
  - USE_ENRICHED_MARKET_OVERVIEW = True: technical diagnostic text technical diagnostic text market_overview_enriched/ (technical diagnostic text technical diagnostic text USD)
  - USE_ENRICHED_MARKET_OVERVIEW = False: technical diagnostic text technical diagnostic text market_overview/ (technical diagnostic text technical diagnostic text)

technical diagnostic text technical diagnostic text, technical diagnostic text technical diagnostic text, technical diagnostic text technical diagnostic text frontend consumption.

technical diagnostic text @st.cache_data technical diagnostic text cache buster technical diagnostic text manifest technical diagnostic text technical diagnostic text.

technical diagnostic text technical diagnostic text:
  ✅ Read-only technical diagnostic text
  ✅ Controlled error state technical diagnostic text missing files
  ✅ @st.cache_data technical diagnostic text manifest built_at technical diagnostic text cache key
  ✅ NO imports technical diagnostic text backend (import_opensea_sales_market_overview.py)
  ✅ NO Streamlit dependencies technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text (technical diagnostic text testability)
"""

import json
from pathlib import Path
from typing import Optional, Dict, List
import pandas as pd
import streamlit as st

from config import get_data_dir, USE_ENRICHED_MARKET_OVERVIEW


def get_market_overview_dir() -> Path:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text market_overview technical diagnostic text.
    
    technical diagnostic text technical diagnostic text market_overview_enriched/ technical diagnostic text market_overview/ technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Returns:
        Path technical diagnostic text market_overview technical diagnostic text market_overview_enriched
    """
    data_dir = get_data_dir()
    if USE_ENRICHED_MARKET_OVERVIEW:
        enriched_dir = data_dir / "market_overview_enriched"
        # Fallback to original if enriched doesn't exist
        if enriched_dir.exists():
            return enriched_dir
    
    return data_dir / "market_overview"


def _get_manifest_path() -> Path:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text manifest technical diagnostic text.
    
    technical diagnostic text enriched: market_overview_enriched_manifest.json
    technical diagnostic text technical diagnostic text: market_manifest.json
    
    Fallback logic: technical diagnostic text USE_ENRICHED_MARKET_OVERVIEW=True technical diagnostic text enriched technical diagnostic text technical diagnostic text,
    technical diagnostic text original market_manifest.json technical diagnostic text original market_overview/ directory.
    """
    data_dir = get_data_dir()
    
    if USE_ENRICHED_MARKET_OVERVIEW:
        enriched_dir = data_dir / "market_overview_enriched"
        enriched_manifest = enriched_dir / "market_overview_enriched_manifest.json"
        if enriched_manifest.exists():
            return enriched_manifest
        # Fallback: technical implementation note enriched technical implementation note technical implementation note technical implementation note, use original
    
    # Either USE_ENRICHED_MARKET_OVERVIEW=False or enriched manifest doesn't exist
    return data_dir / "market_overview" / "market_manifest.json"


def _get_daily_metrics_path() -> Path:
    """technical documentation technical documentation technical documentation daily_market_metrics.csv."""
    return get_market_overview_dir() / "daily_market_metrics.csv"


def _get_monthly_metrics_path() -> Path:
    """technical documentation technical documentation technical documentation monthly_market_metrics.csv."""
    return get_market_overview_dir() / "monthly_market_metrics.csv"


def _get_market_summary_path() -> Path:
    """technical documentation technical documentation technical documentation market_summary.json."""
    return get_market_overview_dir() / "market_summary.json"


def _get_enriched_sales_dir() -> Path:
    """Return the read-only transaction-level enriched sales directory."""
    return get_data_dir() / "sales_enriched"


def _get_top_items_path() -> Path:
    """technical documentation technical documentation technical documentation top_items_by_volume.csv."""
    return get_market_overview_dir() / "top_items_by_volume.csv"


def _get_top_items_by_volume_ranking_path() -> Path:
    """technical documentation technical documentation technical documentation top_items_by_volume_ranking.csv."""
    return get_market_overview_dir() / "top_items_by_volume_ranking.csv"


def _get_top_items_by_liquidity_path() -> Path:
    """technical documentation technical documentation technical documentation top_items_by_liquidity.csv."""
    return get_market_overview_dir() / "top_items_by_liquidity.csv"


def _get_top_items_by_market_strength_path() -> Path:
    """technical documentation technical documentation technical documentation top_items_by_market_strength.csv."""
    return get_market_overview_dir() / "top_items_by_market_strength.csv"


def _is_enriched_manifest(manifest: Dict) -> bool:
    """
    technical diagnostic text, technical diagnostic text technical diagnostic text technical diagnostic text enriched technical diagnostic text legacy.
    
    Enriched manifest technical diagnostic text:
    - files_created
    - data_validation
    - integrity_checks
    
    Legacy manifest technical diagnostic text:
    - status
    - built_at
    - files
    """
    return 'files_created' in manifest or 'integrity_checks' in manifest or 'data_validation' in manifest


def load_market_manifest() -> Optional[Dict]:
    """
    technical diagnostic text market_manifest.json.
    
    technical diagnostic text technical diagnostic text technical diagnostic text: legacy technical diagnostic text enriched.
    
    Returns:
        dict technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text JSON
        None technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    """
    manifest_path = _get_manifest_path()
    
    if not manifest_path.exists():
        return None
    
    try:
        with open(manifest_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load market manifest: {e}")
        return None


@st.cache_data(ttl=3600)
def load_daily_market_metrics(cache_buster: str = None) -> Optional[pd.DataFrame]:
    """
    technical diagnostic text daily_market_metrics.csv.
    
    Args:
        cache_buster: technical diagnostic text technical diagnostic text invalidating cache (technical diagnostic text manifest built_at)
    
    Returns:
        DataFrame technical diagnostic text None technical diagnostic text technical diagnostic text technical diagnostic text
    """
    daily_path = _get_daily_metrics_path()
    
    if not daily_path.exists():
        return None
    
    try:
        df = pd.read_csv(daily_path)
        # Convert date column to datetime
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        st.error(f"Failed to load daily market metrics: {e}")
        return None


@st.cache_data(ttl=3600)
def load_monthly_market_metrics(cache_buster: str = None) -> Optional[pd.DataFrame]:
    """
    technical diagnostic text monthly_market_metrics.csv.
    
    Args:
        cache_buster: technical diagnostic text technical diagnostic text invalidating cache
    
    Returns:
        DataFrame technical diagnostic text None technical diagnostic text technical diagnostic text technical diagnostic text
    """
    monthly_path = _get_monthly_metrics_path()
    
    if not monthly_path.exists():
        return None
    
    try:
        df = pd.read_csv(monthly_path)
        # Convert month date columns
        df['month_start'] = pd.to_datetime(df['month_start'])
        df['month_end'] = pd.to_datetime(df['month_end'])
        return df
    except Exception as e:
        st.error(f"Failed to load monthly market metrics: {e}")
        return None


@st.cache_data(ttl=3600)
def load_market_summary(cache_buster: str = None) -> Optional[Dict]:
    """
    technical diagnostic text market_summary.json.
    
    Args:
        cache_buster: technical diagnostic text technical diagnostic text invalidating cache
    
    Returns:
        dict technical diagnostic text None technical diagnostic text technical diagnostic text technical diagnostic text
    """
    summary_path = _get_market_summary_path()
    
    if not summary_path.exists():
        return None
    
    try:
        with open(summary_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load market summary: {e}")
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def load_enriched_market_sales(cache_buster: str = None) -> Optional[pd.DataFrame]:
    """
    Read transaction-level enriched sales CSV files for exact period KPI metrics.

    This is read-only frontend access to prepared files in data_opensea_sales/sales_enriched/.
    """
    sales_dir = _get_enriched_sales_dir()

    if not sales_dir.exists():
        return None

    csv_files = sorted(sales_dir.glob("*.csv"))
    if not csv_files:
        return None

    try:
        frames = [pd.read_csv(csv_file) for csv_file in csv_files]
        if not frames:
            return None

        df = pd.concat(frames, ignore_index=True)
        if 'sale_date' in df.columns:
            df['sale_date'] = pd.to_datetime(df['sale_date'])
        return df
    except Exception as e:
        st.error(f"Failed to load enriched market sales: {e}")
        return None


@st.cache_data(ttl=3600)
def load_top_items_by_volume(cache_buster: str = None, limit: int = 100) -> Optional[pd.DataFrame]:
    """
    technical diagnostic text top_items_by_volume.csv.
    
    Args:
        cache_buster: technical diagnostic text technical diagnostic text invalidating cache
        limit: technical diagnostic text technical diagnostic text rows (default 100)
    
    Returns:
        DataFrame technical diagnostic text None technical diagnostic text technical diagnostic text technical diagnostic text
    """
    top_items_path = _get_top_items_path()
    
    if not top_items_path.exists():
        return None
    
    try:
        df = pd.read_csv(top_items_path)
        return df.head(limit)
    except Exception as e:
        st.error(f"Failed to load top items: {e}")
        return None


@st.cache_data(ttl=3600)
def load_top_items_by_volume_ranking(cache_buster: str = None, limit: int = 20) -> Optional[pd.DataFrame]:
    """
    technical diagnostic text top_items_by_volume_ranking.csv.
    
    technical diagnostic text technical diagnostic text total_volume_gun (technical diagnostic text items, technical diagnostic text technical diagnostic text top 20).
    
    Args:
        cache_buster: technical diagnostic text technical diagnostic text invalidating cache
        limit: technical diagnostic text technical diagnostic text rows (default 20)
    
    Returns:
        DataFrame technical diagnostic text None technical diagnostic text technical diagnostic text technical diagnostic text
    """
    ranking_path = _get_top_items_by_volume_ranking_path()
    
    if not ranking_path.exists():
        return None
    
    try:
        df = pd.read_csv(ranking_path)
        return df.head(limit)
    except Exception as e:
        st.error(f"Failed to load volume ranking: {e}")
        return None


@st.cache_data(ttl=3600)
def load_top_items_by_liquidity(cache_buster: str = None, limit: int = 20) -> Optional[pd.DataFrame]:
    """
    technical diagnostic text top_items_by_liquidity.csv.
    
    technical diagnostic text technical diagnostic text liquidity_score (recency-weighted unique item events).
    
    Args:
        cache_buster: technical diagnostic text technical diagnostic text invalidating cache
        limit: technical diagnostic text technical diagnostic text rows (default 20)
    
    Returns:
        DataFrame technical diagnostic text None technical diagnostic text technical diagnostic text technical diagnostic text
    """
    ranking_path = _get_top_items_by_liquidity_path()
    
    if not ranking_path.exists():
        return None
    
    try:
        df = pd.read_csv(ranking_path)
        return df.head(limit)
    except Exception as e:
        st.error(f"Failed to load liquidity ranking: {e}")
        return None


@st.cache_data(ttl=3600)
def load_top_items_by_market_strength(cache_buster: str = None, limit: int = 20) -> Optional[pd.DataFrame]:
    """
    technical diagnostic text top_items_by_market_strength.csv.
    
    technical diagnostic text technical diagnostic text market_strength_score (sqrt(volume_norm * liquidity_norm)).
    
    Args:
        cache_buster: technical diagnostic text technical diagnostic text invalidating cache
        limit: technical diagnostic text technical diagnostic text rows (default 20)
    
    Returns:
        DataFrame technical diagnostic text None technical diagnostic text technical diagnostic text technical diagnostic text
    """
    ranking_path = _get_top_items_by_market_strength_path()
    
    if not ranking_path.exists():
        return None
    
    try:
        df = pd.read_csv(ranking_path)
        return df.head(limit)
    except Exception as e:
        st.error(f"Failed to load market strength ranking: {e}")
        return None


def _get_top_items_ranking_path(ranking_mode: str, period: str = "all") -> Path:
    """
    Resolve filename from static mapping of (mode, period) -> filename.
    
    Whitelist both parameters and return safe filepath.
    
    Args:
        ranking_mode: 'volume', 'liquidity', or 'market_strength'
        period: 'all', '30d', '7d', or '1d'
    
    Returns:
        Path to ranking CSV
        
    Raises:
        ValueError if ranking_mode or period are invalid
    """
    # Whitelist ranking modes
    valid_modes = {'volume', 'liquidity', 'market_strength'}
    if ranking_mode not in valid_modes:
        raise ValueError(f"Invalid ranking_mode: {ranking_mode}. Must be one of {valid_modes}")
    
    # Whitelist periods
    valid_periods = {'all', '30d', '7d', '1d'}
    if period not in valid_periods:
        raise ValueError(f"Invalid period: {period}. Must be one of {valid_periods}")
    
    # Static filename mapping: (mode, period) -> filename
    mapping = {
        ('volume', 'all'): 'top_items_by_volume_ranking.csv',
        ('volume', '30d'): 'top_items_by_volume_30d.csv',
        ('volume', '7d'): 'top_items_by_volume_7d.csv',
        ('volume', '1d'): 'top_items_by_volume_1d.csv',
        ('liquidity', 'all'): 'top_items_by_liquidity.csv',
        ('liquidity', '30d'): 'top_items_by_liquidity_30d.csv',
        ('liquidity', '7d'): 'top_items_by_liquidity_7d.csv',
        ('liquidity', '1d'): 'top_items_by_liquidity_1d.csv',
        ('market_strength', 'all'): 'top_items_by_market_strength.csv',
        ('market_strength', '30d'): 'top_items_by_market_strength_30d.csv',
        ('market_strength', '7d'): 'top_items_by_market_strength_7d.csv',
        ('market_strength', '1d'): 'top_items_by_market_strength_1d.csv',
    }
    
    filename = mapping[(ranking_mode, period)]
    return get_market_overview_dir() / filename


@st.cache_data(ttl=3600)
def load_top_items_ranking(
    ranking_mode: str = "volume",
    period: str = "all",
    cache_buster: str = None,
    limit: int = 20
) -> Optional[pd.DataFrame]:
    """
    Load top items ranking for a specific mode and time period.
    
    Features:
    - Whitelist both ranking_mode and period
    - Resolve filename from static mapping only (no dynamic construction)
    - Read prepared CSV only (no calculation or filtering in frontend)
    - Return head(limit)
    - No sorting, no filtering, no raw sales access
    - If invalid mode/period, safely fallback to volume + all
    - If file missing, return None (no silent fallback)
    
    Args:
        ranking_mode: 'volume', 'liquidity', 'market_strength' (default 'volume')
        period: 'all', '30d', '7d', '1d' (default 'all')
        cache_buster: cache invalidation (typically manifest built_at)
        limit: max rows to return (default 20)
    
    Returns:
        DataFrame with head(limit) rows, or None if file not found
    """
    # Sanitize inputs: whitelist and fallback to safe defaults
    valid_modes = {'volume', 'liquidity', 'market_strength'}
    valid_periods = {'all', '30d', '7d', '1d'}
    
    if ranking_mode not in valid_modes:
        ranking_mode = 'volume'
    
    if period not in valid_periods:
        period = 'all'
    
    try:
        ranking_path = _get_top_items_ranking_path(ranking_mode, period)
    except ValueError:
        # Fallback to volume + all if mapping fails
        ranking_path = _get_top_items_ranking_path('volume', 'all')
    
    if not ranking_path.exists():
        return None
    
    try:
        df = pd.read_csv(ranking_path)
        return df.head(limit)
    except Exception as e:
        st.error(f"Failed to load {ranking_mode} {period} ranking: {e}")
        return None


def verify_market_data_available() -> bool:
    """
    technical diagnostic text, technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text market data files.
    
    technical diagnostic text technical diagnostic text technical diagnostic text-technical diagnostic text: legacy technical diagnostic text enriched.
    
    Returns:
        True technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text manifest valid
        False technical diagnostic text
    """
    manifest = load_market_manifest()
    if manifest is None:
        return False
    
    overview_dir = get_market_overview_dir()
    
    # Check if this is enriched manifest
    if _is_enriched_manifest(manifest):
        # Enriched manifest validation
        # 1. Check integrity_checks: technical implementation note technical implementation note technical implementation note True
        integrity = manifest.get('integrity_checks', {})
        if not all(integrity.values()):
            return False
        
        # 2. Check required files exist and are non-empty
        required_files = [
            'daily_market_metrics.csv',
            'monthly_market_metrics.csv',
            'top_items_by_volume.csv',
            'market_summary.json'
        ]
        for file_name in required_files:
            file_path = overview_dir / file_name
            if not file_path.exists() or file_path.stat().st_size == 0:
                return False
        
        return True
    else:
        # Legacy manifest validation
        if manifest.get('status') != 'success':
            return False
        
        # Check required files from manifest
        required_files = ['daily_market_metrics', 'monthly_market_metrics', 'market_summary']
        for file_key in required_files:
            if file_key not in manifest.get('files', {}):
                return False
        
        return True


def get_market_data_status() -> Dict[str, str]:
    """
    technical diagnostic text status market data.
    
    technical diagnostic text technical diagnostic text technical diagnostic text-technical diagnostic text: legacy technical diagnostic text enriched.
    
    Returns:
        dict technical diagnostic text keys: status (OK/MISSING/ERROR), built_at, message
    """
    manifest = load_market_manifest()
    
    if manifest is None:
        return {
            'status': 'MISSING',
            'built_at': None,
            'message': 'Market data technical diagnostic text technical diagnostic text. Backend builder technical diagnostic text technical diagnostic text technical diagnostic text outputs technical diagnostic text.'
        }
    
    # Check if this is enriched manifest
    if _is_enriched_manifest(manifest):
        # Enriched manifest validation
        overview_dir = get_market_overview_dir()
        
        # 1. Check integrity_checks
        integrity = manifest.get('integrity_checks', {})
        if not all(integrity.values()):
            return {
                'status': 'ERROR',
                'built_at': manifest.get('created_at_utc'),
                'message': f'Market data integrity check failed'
            }
        
        # 2. Check required files exist
        required_files = [
            'daily_market_metrics.csv',
            'monthly_market_metrics.csv',
            'top_items_by_volume.csv',
            'market_summary.json'
        ]
        for file_name in required_files:
            file_path = overview_dir / file_name
            if not file_path.exists():
                return {
                    'status': 'ERROR',
                    'built_at': manifest.get('created_at_utc'),
                    'message': f'Market data file missing: {file_name}'
                }
        
        # All checks passed
        return {
            'status': 'OK',
            'built_at': manifest.get('created_at_utc'),
            'message': f"Market data available (enriched), created at {manifest.get('created_at_utc')}"
        }
    else:
        # Legacy manifest validation
        status = manifest.get('status', 'UNKNOWN')
        if status != 'success':
            return {
                'status': 'ERROR',
                'built_at': manifest.get('built_at'),
                'message': f'Market data build failed: status={status}'
            }
        
        return {
            'status': 'OK',
            'built_at': manifest.get('built_at'),
            'message': f"Market data available, built at {manifest.get('built_at')}"
        }


def get_market_date_range() -> Optional[tuple]:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text market data.
    
    Returns:
        (min_date, max_date) technical diagnostic text strings technical diagnostic text technical diagnostic text YYYY-MM-DD
        technical diagnostic text None technical diagnostic text data technical diagnostic text technical diagnostic text
    """
    summary = load_market_summary(cache_buster=_get_cache_buster())
    if summary is None:
        return None
    
    date_range = summary.get('date_range', {})
    return (date_range.get('min_sale_date'), date_range.get('max_sale_date'))


def get_market_totals() -> Optional[Dict]:
    """
    technical diagnostic text technical diagnostic text KPI technical diagnostic text.
    
    Returns:
        dict technical diagnostic text keys: transactions, volume_gun, unique_buyers, unique_sellers, unique_wallets, items_traded
        technical diagnostic text None technical diagnostic text data technical diagnostic text technical diagnostic text
    """
    summary = load_market_summary(cache_buster=_get_cache_buster())
    if summary is None:
        return None
    
    return summary.get('totals', {})


def get_market_price_stats() -> Optional[Dict]:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Returns:
        dict technical diagnostic text keys: avg_price_gun, median_price_gun, min_price_gun, max_price_gun
        technical diagnostic text None technical diagnostic text data technical diagnostic text technical diagnostic text
    """
    summary = load_market_summary(cache_buster=_get_cache_buster())
    if summary is None:
        return None
    
    return summary.get('price', {})


def get_market_token_split() -> Optional[Dict]:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text (GUN vs WGUN).
    
    Returns:
        dict technical diagnostic text technical diagnostic text GUN, WGUN, technical diagnostic text technical diagnostic text volume_gun, transactions, percent_of_volume
        technical diagnostic text None technical diagnostic text data technical diagnostic text technical diagnostic text
    """
    summary = load_market_summary(cache_buster=_get_cache_buster())
    if summary is None:
        return None
    
    return summary.get('token_type', {})


def get_recent_windows() -> Optional[Dict]:
    """
    technical diagnostic text recent market activity windows (last 24h, last 7d).
    
    Returns:
        dict technical diagnostic text technical diagnostic text last_24h, last_7d
        technical diagnostic text None technical diagnostic text data technical diagnostic text technical diagnostic text
    """
    summary = load_market_summary(cache_buster=_get_cache_buster())
    if summary is None:
        return None
    
    return summary.get('recent_windows', {})


def _get_cache_buster() -> str:
    """
    technical diagnostic text cache buster technical diagnostic text manifest technical diagnostic text invalidation Streamlit cache.
    
    technical diagnostic text technical diagnostic text technical diagnostic text-technical diagnostic text:
    - Legacy: technical diagnostic text built_at
    - Enriched: technical diagnostic text created_at_utc
    
    Returns:
        manifest timestamp (built_at technical diagnostic text created_at_utc) technical diagnostic text empty string technical diagnostic text technical diagnostic text technical diagnostic text
    """
    manifest = load_market_manifest()
    if manifest is None:
        return ""
    
    # Check if this is enriched manifest
    if _is_enriched_manifest(manifest):
        return manifest.get('created_at_utc', "")
    else:
        # Legacy manifest
        return manifest.get('built_at', "")
