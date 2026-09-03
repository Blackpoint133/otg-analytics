"""
Item Analytics Overview Page.

ÐŸÐµÑ€ÐµÑ€Ð°Ð±Ð¾Ñ‚Ð°Ð½Ð½Ð°Ñ ÑÑ‚Ñ€Ð°Ð½Ð¸Ñ†Ð° Ñ€ÐµÐ¶Ð¸Ð¼Ð° ITEM ANALYTICS Ñ Ð»ÐµÐ²Ð¾Ð¹ card Ð¸ right pane.

ÐžÑ‚Ð¾Ð±Ñ€Ð°Ð¶Ð°ÐµÑ‚:
- Ð›ÐµÐ²Ð°Ñ ÐºÐ¾Ð»Ð¾Ð½ÐºÐ° (35%): ÐºÐ¾Ð¼Ð¿Ð°ÐºÑ‚Ð½Ñ‹Ð¹ item card ÑÐ¾ ÑÑ‚Ð¸Ð»ÐµÐ¼ Top Items
- ÐŸÑ€Ð°Ð²Ð°Ñ ÐºÐ¾Ð»Ð¾Ð½ÐºÐ° (65%): chart Ð¸Ð»Ð¸ Ñ‚Ð°Ð±Ð»Ð¸Ñ†Ð° Ð¿Ñ€Ð¾Ð´Ð°Ð¶ (controlled by sidebar)
"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict
from html import escape
import os
from pathlib import Path

from formatters import format_number, format_metric_value, format_historical_metric_pair, get_rarity_style
from charts import build_sales_chart
from ui.tables import render_sales_table, paginate_dataframe, get_current_page
from gunzscope_supply import ATTRIBUTION, get_item_supply_with_rank


# Image URL normalization
IMAGE_CDN_BASE = "https://cdne-g01-livepc-wu-itemsthumbnails.azureedge.net"


def _normalize_item_image_url(image_url):
    """ÐÐ¾Ñ€Ð¼Ð°Ð»Ð¸Ð·ÑƒÐµÑ‚ URL Ð¸Ð·Ð¾Ð±Ñ€Ð°Ð¶ÐµÐ½Ð¸Ð¹ Ð´Ð»Ñ Item Card."""
    if image_url is None or pd.isna(image_url):
        return ""
    value = str(image_url).strip()
    if not value:
        return ""
    if value.startswith("/ExportedAssets/"):
        return IMAGE_CDN_BASE + value
    return value


def _normalize_item_key(name: str, rarity: str) -> str:
    """Ð“ÐµÐ½ÐµÑ€Ð¸Ñ€ÑƒÐµÑ‚ Ð½Ð¾Ñ€Ð¼Ð°Ð»Ð¸Ð·Ð¾Ð²Ð°Ð½Ð½Ñ‹Ð¹ item key Ð´Ð»Ñ lookup Ð² ranking CSV."""
    norm_name = str(name).lower().strip()
    norm_rarity = str(rarity).lower().strip()
    return f"{norm_name}|{norm_rarity}"


def _load_item_market_ranking_metrics(item_name: str, rarity: str, period: str = "all") -> Optional[Dict]:
    """
    Ð—Ð°Ð³Ñ€ÑƒÐ¶Ð°ÐµÑ‚ ranking metrics Ð´Ð»Ñ item Ð¸Ð· prepared CSV.
    
    Ð˜Ñ‰ÐµÑ‚ item Ð² streamlit_opensea_sales/data_opensea_sales/market_overview_enriched/top_items_by_volume_ranking.csv
    
    Args:
        item_name: Ð˜Ð¼Ñ item
        rarity: Ð ÐµÐ´ÐºÐ¾ÑÑ‚ÑŒ item
        period: ÐŸÐµÑ€Ð¸Ð¾Ð´ Ð´Ð»Ñ ranking ('all')
        
    Returns:
        dict Ñ ranking metrics Ð¸Ð»Ð¸ None ÐµÑÐ»Ð¸ item Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½
    """
    try:
        # Correct path: streamlit_opensea_sales/data_opensea_sales/market_overview_enriched/
        # From item_overview.py (streamlit_opensea_sales/ui/item_overview.py), go up to streamlit_opensea_sales/
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ranking_csv_path = os.path.join(
            base_path,
            'data_opensea_sales',
            'market_overview_enriched',
            'top_items_by_volume_ranking.csv'
        )
        
        if not os.path.exists(ranking_csv_path):
            return None
        
        ranking_df = _load_ranking_csv_cached(ranking_csv_path)
        if ranking_df is None or ranking_df.empty:
            return None
        
        item_key = _normalize_item_key(item_name, rarity)
        
        # Normalize rows for comparison
        ranking_df['normalized_key'] = ranking_df.apply(
            lambda row: _normalize_item_key(
                str(row.get('item_name', '')),
                str(row.get('rarity', ''))
            ),
            axis=1
        )
        matching_rows = ranking_df[ranking_df['normalized_key'] == item_key]
        
        if matching_rows.empty:
            return None
        
        row = matching_rows.iloc[0]
        metrics = {}
        
        # Ranking positions (top priority for display)
        if 'rank_volume' in row and pd.notna(row['rank_volume']):
            metrics['rank_volume'] = int(row['rank_volume'])
        if 'rank_liquidity' in row and pd.notna(row['rank_liquidity']):
            metrics['rank_liquidity'] = int(row['rank_liquidity'])
        if 'rank_market_strength' in row and pd.notna(row['rank_market_strength']):
            metrics['rank_market_strength'] = int(row['rank_market_strength'])
        
        # Market metrics
        if 'market_strength_score' in row and pd.notna(row['market_strength_score']):
            metrics['market_strength_score'] = float(row['market_strength_score'])
        if 'liquidity_score' in row and pd.notna(row['liquidity_score']):
            metrics['liquidity_score'] = float(row['liquidity_score'])
        if 'weighted_volume_gun' in row and pd.notna(row['weighted_volume_gun']):
            metrics['weighted_volume_gun'] = float(row['weighted_volume_gun'])
        
        # Trading activity
        if 'active_trading_days' in row and pd.notna(row['active_trading_days']):
            metrics['active_trading_days'] = int(row['active_trading_days'])
        if 'unique_item_events' in row and pd.notna(row['unique_item_events']):
            metrics['unique_item_events'] = int(row['unique_item_events'])
        
        return metrics if metrics else None
    
    except Exception as e:
        return None


@st.cache_data(ttl=3600)
def _load_ranking_csv_cached(csv_path: str) -> Optional[pd.DataFrame]:
    """Ð—Ð°Ð³Ñ€ÑƒÐ¶Ð°ÐµÑ‚ ranking CSV Ñ ÐºÐµÑˆÐ¸Ñ€Ð¾Ð²Ð°Ð½Ð¸ÐµÐ¼."""
    try:
        if os.path.exists(csv_path):
            return pd.read_csv(csv_path)
        return None
    except Exception:
        return None


@st.cache_data(ttl=3600)
def _load_item_trend_csv_cached(csv_path: str, file_mtime: float) -> pd.DataFrame:
    """Load backend-prepared item trend CSV rows."""
    try:
        if not os.path.exists(csv_path):
            return pd.DataFrame()
        return pd.read_csv(csv_path)
    except Exception:
        return pd.DataFrame()


def _load_item_trend_data(item_record: Dict) -> pd.DataFrame:
    """Resolve and load item_trends/<same item filename>.csv from the selected item record."""
    if not item_record:
        return pd.DataFrame()

    file_path = item_record.get('file_path')
    if not file_path:
        return pd.DataFrame()

    original_path = Path(file_path)
    trend_path = original_path.parent.parent / 'item_trends' / original_path.name

    if not trend_path.exists():
        return pd.DataFrame()

    return _load_item_trend_csv_cached(str(trend_path), trend_path.stat().st_mtime)


def _calculate_liquidity_trade_per_day(df: pd.DataFrame) -> float:
    """
    Ð’Ñ‹Ñ‡Ð¸ÑÐ»ÑÐµÑ‚ liquidity ÐºÐ°Ðº trades per day (Ð²ÑÐµ-Ð²Ñ€ÐµÐ¼Ñ Ð¸ÑÑ‚Ð¾Ñ€Ð¸ÑŽ).
    
    Ð¤Ð¾Ñ€Ð¼ÑƒÐ»Ð°:
    liquidity_trade_per_day = total_transactions_all_time / lifetime_days
    
    Ð³Ð´Ðµ:
    lifetime_days = (last_sale_date - first_sale_date) + 1
    
    Args:
        df: DataFrame Ñ Ð¿Ð¾Ð»Ð½Ð¾Ð¹ Ð¸ÑÑ‚Ð¾Ñ€Ð¸ÐµÐ¹ item (Ð²ÑÐµ-Ð²Ñ€ÐµÐ¼Ñ)
    
    Returns:
        float: trades per day (Ð¸Ð»Ð¸ 0 ÐµÑÐ»Ð¸ Ð´Ð°Ñ‚Ð° Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½Ð°)
    """
    if df.empty or 'sale_date' not in df.columns:
        return 0.0
    
    try:
        sale_dates = pd.to_datetime(df['sale_date'])
        first_date = sale_dates.min()
        last_date = sale_dates.max()
        
        if pd.isna(first_date) or pd.isna(last_date):
            return 0.0
        
        lifetime_days = (last_date - first_date).days + 1
        if lifetime_days <= 0:
            lifetime_days = 1
        
        total_transactions = len(df)
        liquidity = total_transactions / lifetime_days
        
        return float(liquidity)
    except Exception:
        return 0.0


def _build_item_card_metrics(
    filtered_df: pd.DataFrame,
    df: pd.DataFrame,
    show_usd: bool,
    current_gun_price: float
) -> Dict:
    """Ð¡Ñ‚Ñ€Ð¾Ð¸Ñ‚ metrics Ð´Ð»Ñ item card Ð¸Ð· filtered_df."""
    metrics = {
        'transactions': 0,
        'avg_price_gun': 0,
        'avg_price_usd': None,
        'total_volume_gun': 0,
        'total_volume_usd': None,
        'min_price_gun': 0,
        'min_price_usd': None,
        'max_price_gun': 0,
        'max_price_usd': None,
        'unique_buyers': 0,
        'unique_sellers': 0,
        'unique_wallets': 0,
        'last_sale': None,
        'liquidity_trade_per_day': 0.0,
        'historical_usd_available': False,
    }
    
    if filtered_df.empty:
        return metrics
    
    metrics['transactions'] = len(filtered_df)
    metrics['total_volume_gun'] = float(filtered_df['price_gun'].sum())
    metrics['avg_price_gun'] = float(filtered_df['price_gun'].mean())
    metrics['min_price_gun'] = float(filtered_df['price_gun'].min())
    metrics['max_price_gun'] = float(filtered_df['price_gun'].max())
    
    # Calculate liquidity from full item history (df), not filtered_df
    metrics['liquidity_trade_per_day'] = _calculate_liquidity_trade_per_day(df)
    
    has_historical_usd = 'price_usd_at_sale' in filtered_df.columns and 'gun_usd_price_at_sale' in filtered_df.columns
    if show_usd:
        if has_historical_usd and filtered_df['price_usd_at_sale'].notna().any():
            valid_usd = filtered_df[filtered_df['price_usd_at_sale'].notna()]
            if not valid_usd.empty:
                metrics['historical_usd_available'] = True
                metrics['total_volume_usd'] = float(valid_usd['price_usd_at_sale'].sum())
                metrics['avg_price_usd'] = float(valid_usd['price_usd_at_sale'].mean())
                metrics['min_price_usd'] = float(valid_usd['price_usd_at_sale'].min())
                metrics['max_price_usd'] = float(valid_usd['price_usd_at_sale'].max())
    
    metrics['unique_sellers'] = int(filtered_df['seller'].nunique())
    metrics['unique_buyers'] = int(filtered_df['buyer'].nunique())
    unique_wallets_set = set(filtered_df['seller'].unique()) | set(filtered_df['buyer'].unique())
    metrics['unique_wallets'] = len(unique_wallets_set)
    
    if 'sale_date' in filtered_df.columns:
        try:
            last_sale_date = pd.to_datetime(filtered_df['sale_date']).max()
            metrics['last_sale'] = last_sale_date
        except Exception:
            metrics['last_sale'] = None
    
    return metrics


def _render_item_card(
    df: pd.DataFrame,
    filtered_df: pd.DataFrame,
    item_name: str,
    rarity: str,
    metrics: Dict,
    ranking_metrics: Optional[Dict],
    show_usd: bool,
    current_gun_price: float,
    supply_record: Optional[Dict] = None,
    supply_rank: Optional[int] = None,
):
    """
    Ð ÐµÐ½Ð´ÐµÑ€Ð¸Ñ‚ left column item card.
    
    Ð¡Ñ‚Ñ€ÑƒÐºÑ‚ÑƒÑ€Ð° ÑÐµÐºÑ†Ð¸Ð¹:
    - Header (image, name, rarity with color, rank)
    - Market Position (volume rank, liquidity rank)
    - Market Metrics (volume, liquidity trade/day, transactions)
    - Pricing (avg, min, max, last sale)
    - Participants (buyers, sellers, wallets)
    
    Removed sections:
    - Market Strength, Liquidity Score, Weighted Volume (hidden from UI)
    - Trading Activity (events, active days)
    """
    
    # CSS Ð´Ð»Ñ item card Ñ ÑƒÐ»ÑƒÑ‡ÑˆÐµÐ½Ð½Ð¾Ð¹ Ñ‚Ð¸Ð¿Ð¾Ð³Ñ€Ð°Ñ„Ð¸ÐºÐ¾Ð¹
    st.markdown("""
        <style>
        .item-analytics-card-shell {
            min-height: 600px;
            display: flex;
            flex-direction: column;
        }

        .item-analytics-card {
            background-color: #000000;
            border: 1px solid #1a1a1a;
            padding: 9px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            min-height: 600px;
        }
        
        .item-card-header {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            margin-bottom: 4px;
        }
        
        .item-card-image-container {
            width: 100%;
            height: 140px;
            background-color: #0a0a0a;
            border: 1px solid #1a1a1a;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            margin-bottom: 4px;
        }
        
        .item-card-image {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }
        
        .item-card-placeholder {
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
            color: #555;
            font-family: 'Space Mono', monospace;
            letter-spacing: 0.8px;
        }
        
        .item-card-name {
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
            font-size: 14px;
            font-weight: 700;
            color: var(--otg-text-primary);
            line-height: 1.2;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            text-align: center;
        }
        
        .item-card-rarity {
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.7px;
            text-align: center;
        }
        
        .item-card-rank {
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.7px;
            color: var(--otg-accent);
            text-align: center;
        }
        
        .item-card-section {
            display: flex;
            flex-direction: column;
            gap: 3px;
            padding: 5px 0;
            border-top: 1px solid #1a1a1a;
        }
        
        .item-card-section:first-of-type {
            border-top: none;
            padding-top: 0;
        }
        
        .item-card-section-title {
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--otg-accent);
            margin-bottom: 2px;
            border-bottom: 1px solid #1a1a1a;
            padding-bottom: 2px;
        }
        
        .item-card-metric-row {
            display: flex;
            justify-content: space-between;
            font-family: 'Space Mono', monospace;
            font-size: 12px;
            align-items: center;
        }
        
        .item-card-metric-label {
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            color: var(--otg-text-secondary);
            flex: 1.4;
            font-size: 12px;
            white-space: nowrap;
        }
        
        .item-card-metric-value {
            font-weight: 700;
            color: var(--otg-text-primary);
            text-align: right;
            flex: 0.6;
            font-size: 12px;
            white-space: nowrap;
        }
        
        .item-card-accent-value {
            color: var(--otg-text-primary);
        }
        </style>
    """, unsafe_allow_html=True)
    card_html = '<div class="item-analytics-card">'
    
    # ====== HEADER ======
    card_html += '<div class="item-card-header">'
    
    # Image
    if 'image_url' in df.columns and not df.empty:
        image_url = df['image_url'].iloc[0]
        normalized_url = _normalize_item_image_url(image_url)
        if normalized_url:
            safe_image_url = escape(normalized_url, quote=True)
            card_html += f'<div class="item-card-image-container"><img src="{safe_image_url}" class="item-card-image" alt="Item"></div>'
        else:
            card_html += '<div class="item-card-image-container"><div class="item-card-placeholder">NO IMAGE</div></div>'
    else:
        card_html += '<div class="item-card-image-container"><div class="item-card-placeholder">NO IMAGE</div></div>'
    
    # Name
    item_name_safe = escape(item_name, quote=True)
    card_html += f'<div class="item-card-name">{item_name_safe}</div>'
    
    # Rarity with color
    rarity_safe = escape(rarity, quote=True)
    rarity_color, _ = get_rarity_style(rarity)
    card_html += f'<div class="item-card-rarity" style="color: {rarity_color};">{rarity_safe}</div>'
    
    # Rank (if available)
    if ranking_metrics and 'rank_market_strength' in ranking_metrics:
        rank_value = ranking_metrics['rank_market_strength']
        card_html += f'<div class="item-card-rank">RANK #{rank_value}</div>'
    
    card_html += '</div>'  # end header

    # ====== GUNZSCOPE SUPPLY ======
    card_html += '<div class="item-card-section">'
    card_html += '<div class="item-card-section-title">SUPPLY</div>'
    supply_value = supply_record.get('supply') if supply_record else None
    supply_text = f"{supply_value:,}" if isinstance(supply_value, int) and supply_value >= 0 else 'N/A'
    rank_text = f"#{supply_rank}" if isinstance(supply_rank, int) else 'N/A'
    if supply_record and supply_record.get('status') == 'stale':
        supply_text += ' (STALE)'
    card_html += f'<div class="item-card-metric-row"><span class="item-card-metric-label">SUPPLY</span><span class="item-card-metric-value item-card-accent-value">{supply_text}</span></div>'
    card_html += f'<div class="item-card-metric-row"><span class="item-card-metric-label">SUPPLY RANK</span><span class="item-card-metric-value item-card-accent-value">{rank_text}</span></div>'
    card_html += (
        f'<div style="font-size:10px;margin-top:4px;text-align:right;">'
        f'<a href="{ATTRIBUTION["url"]}" target="_blank" rel="noopener noreferrer" '
        f'style="color:var(--otg-text-secondary);text-decoration:none;">'
        f'<img src="{ATTRIBUTION["logoUrl"]}" alt="GUNZscope" width="18" height="18" '
        f'style="vertical-align:middle;margin-right:4px;">{ATTRIBUTION["text"]}</a></div>'
    )
    card_html += '</div>'
    
    # ====== MARKET POSITION (Ranks) ======
    if ranking_metrics and any(k in ranking_metrics for k in ['rank_volume', 'rank_liquidity']):
        card_html += '<div class="item-card-section">'
        card_html += '<div class="item-card-section-title">MARKET POSITION</div>'
        
        if 'rank_volume' in ranking_metrics:
            card_html += (
                f'<div class="item-card-metric-row">'
                '<span class="item-card-metric-label">VOLUME RANK</span>'
                f'<span class="item-card-metric-value item-card-accent-value">#{ranking_metrics["rank_volume"]}</span>'
                '</div>'
            )
        if 'rank_liquidity' in ranking_metrics:
            card_html += (
                f'<div class="item-card-metric-row">'
                '<span class="item-card-metric-label">LIQUIDITY RANK</span>'
                f'<span class="item-card-metric-value item-card-accent-value">#{ranking_metrics["rank_liquidity"]}</span>'
                '</div>'
            )
        
        card_html += '</div>'
    
    # ====== MARKET METRICS ======
    card_html += '<div class="item-card-section">'
    card_html += '<div class="item-card-section-title">MARKET METRICS</div>'
    
    # VOLUME (GUN or USD based on toggle)
    if show_usd:
        if metrics.get('historical_usd_available') and metrics.get('total_volume_usd') is not None:
            volume_fmt = format_number(metrics['total_volume_usd'], True, 1.0, currency='USD')
        else:
            volume_fmt = 'N/A'
        volume_label = 'VOLUME (USD)'
    else:
        volume_fmt = format_number(metrics['total_volume_gun'], False, current_gun_price, currency='GUN')
        volume_label = 'VOLUME (GUN)'
    
    card_html += (
        f'<div class="item-card-metric-row">'
        f'<span class="item-card-metric-label">{volume_label}</span>'
        f'<span class="item-card-metric-value item-card-accent-value">{volume_fmt}</span>'
        '</div>'
    )
    
    # LIQUIDITY (TRADE/DAY)
    liquidity_fmt = f"{metrics['liquidity_trade_per_day']:.2f}"
    card_html += (
        f'<div class="item-card-metric-row">'
        '<span class="item-card-metric-label">LIQUIDITY (TRADE/DAY)</span>'
        f'<span class="item-card-metric-value">{liquidity_fmt}</span>'
        '</div>'
    )
    
    # TRANSACTIONS
    card_html += (
        f'<div class="item-card-metric-row">'
        '<span class="item-card-metric-label">TRANSACTIONS</span>'
        f'<span class="item-card-metric-value">{metrics["transactions"]}</span>'
        '</div>'
    )
    
    card_html += '</div>'
    
    # ====== PRICING ======
    card_html += '<div class="item-card-section">'
    card_html += '<div class="item-card-section-title">PRICING</div>'
    
    if show_usd:
        avg_fmt = (
            format_number(metrics['avg_price_usd'], True, 1.0, currency='USD')
            if metrics.get('historical_usd_available') and metrics.get('avg_price_usd') is not None
            else 'N/A'
        )
    else:
        avg_fmt = format_number(metrics['avg_price_gun'], False, 1.0, currency='GUN')
    
    card_html += (
        f'<div class="item-card-metric-row">'
        '<span class="item-card-metric-label">AVERAGE PRICE</span>'
        f'<span class="item-card-metric-value item-card-accent-value">{avg_fmt}</span>'
        '</div>'
    )
    
    if show_usd:
        min_fmt = (
            format_number(metrics['min_price_usd'], True, 1.0, currency='USD')
            if metrics.get('historical_usd_available') and metrics.get('min_price_usd') is not None
            else 'N/A'
        )
        max_fmt = (
            format_number(metrics['max_price_usd'], True, 1.0, currency='USD')
            if metrics.get('historical_usd_available') and metrics.get('max_price_usd') is not None
            else 'N/A'
        )
    else:
        min_fmt = format_number(metrics['min_price_gun'], False, 1.0, currency='GUN')
        max_fmt = format_number(metrics['max_price_gun'], False, 1.0, currency='GUN')
    
    card_html += (
        f'<div class="item-card-metric-row">'
        '<span class="item-card-metric-label">MIN PRICE</span>'
        f'<span class="item-card-metric-value">{min_fmt}</span>'
        '</div>'
    )
    
    card_html += (
        f'<div class="item-card-metric-row">'
        '<span class="item-card-metric-label">MAX PRICE</span>'
        f'<span class="item-card-metric-value">{max_fmt}</span>'
        '</div>'
    )
    
    if metrics['last_sale']:
        last_sale_str = metrics['last_sale'].strftime('%Y-%m-%d %H:%M')
        card_html += (
            f'<div class="item-card-metric-row">'
            '<span class="item-card-metric-label">LAST SALE</span>'
            f'<span class="item-card-metric-value">{last_sale_str}</span>'
            '</div>'
        )
    
    card_html += '</div>'
    
    # ====== PARTICIPANTS ======
    card_html += '<div class="item-card-section">'
    card_html += '<div class="item-card-section-title">PARTICIPANTS</div>'
    
    card_html += (
        f'<div class="item-card-metric-row">'
        '<span class="item-card-metric-label">UNIQUE BUYERS</span>'
        f'<span class="item-card-metric-value">{metrics["unique_buyers"]}</span>'
        '</div>'
    )
    
    card_html += (
        f'<div class="item-card-metric-row">'
        '<span class="item-card-metric-label">UNIQUE SELLERS</span>'
        f'<span class="item-card-metric-value">{metrics["unique_sellers"]}</span>'
        '</div>'
    )
    
    card_html += (
        f'<div class="item-card-metric-row">'
        '<span class="item-card-metric-label">UNIQUE WALLETS</span>'
        f'<span class="item-card-metric-value">{metrics["unique_wallets"]}</span>'
        '</div>'
    )
    
    card_html += '</div>'
    
    card_html += '</div>'  # end card
    
    st.markdown(f'<div class="item-analytics-card-shell">{card_html}</div>', unsafe_allow_html=True)


def _render_item_chart(
    filtered_df: pd.DataFrame,
    show_volume: bool,
    show_usd: bool,
    current_gun_price: float,
    show_trend_line: bool,
    trend_df: pd.DataFrame,
    mobile_layout: bool,
    highlight_wallet: Optional[str] = None
):
    fig = build_sales_chart(
        filtered_df,
        show_volume,
        show_usd,
        current_gun_price,
        show_trend_line=show_trend_line,
        trend_df=trend_df,
        mobile_layout=mobile_layout,
        compact_vertical_margins=not mobile_layout
        , highlight_wallet=highlight_wallet
    )
    if mobile_layout:
        fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


def _render_item_sales_table(
    filtered_df: pd.DataFrame,
    show_usd: bool,
    current_gun_price: float,
    items_per_page: int
):
    if not filtered_df.empty:
        table_df = filtered_df.sort_values(
            by='sale_date',
            ascending=False,
            kind='stable',
        )
        current_page = get_current_page()
        pagination_result = paginate_dataframe(table_df, current_page, items_per_page)
        page_data = pagination_result['page_data']
        total_pages = pagination_result['total_pages']
        
        # Render table directly (no accordion)
        render_sales_table(page_data, show_usd, current_gun_price)
        
        # Pagination
        if total_pages > 1:
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                if current_page > 1:
                    if st.button("Previous", key="prev_page", use_container_width=True):
                        st.query_params["page"] = str(current_page - 1)
                        st.rerun()
            
            with col2:
                st.markdown(f"<div style='text-align: center; padding: 8px;'><strong>Page {current_page} of {total_pages}</strong></div>", unsafe_allow_html=True)
            
            with col3:
                if current_page < total_pages:
                    if st.button("Next", key="next_page", use_container_width=True):
                        st.query_params["page"] = str(current_page + 1)
                        st.rerun()
    else:
        st.info("No sales data for the selected date range")


def render_item_overview(
    df: pd.DataFrame,
    filtered_df: pd.DataFrame,
    current_selected_item: str,
    item_record: Dict,
    show_volume: bool,
    show_usd: bool,
    current_gun_price: float,
    show_trend_line: bool,
    item_view_mode: str = "chart",
    items_per_page: int = 50,
    highlight_wallet: Optional[str] = None
):
    """
    Ð“Ð»Ð°Ð²Ð½Ð°Ñ Ñ„ÑƒÐ½ÐºÑ†Ð¸Ñ Ñ€ÐµÐ½Ð´ÐµÑ€Ð° Item Analytics Ñ Ð½Ð¾Ð²Ð¾Ð¹ layout.
    
    Layout:
    - Ð›ÐµÐ²Ð°Ñ ÐºÐ¾Ð»Ð¾Ð½ÐºÐ° (35%): item card
    - ÐŸÑ€Ð°Ð²Ð°Ñ ÐºÐ¾Ð»Ð¾Ð½ÐºÐ° (65%): chart Ð¸Ð»Ð¸ table (based on item_view_mode from sidebar)
    
    Args:
        df: Ð˜ÑÑ…Ð¾Ð´Ð½Ñ‹Ðµ Ð´Ð°Ð½Ð½Ñ‹Ðµ item
        filtered_df: ÐžÑ‚Ñ„Ð¸Ð»ÑŒÑ‚Ñ€Ð¾Ð²Ð°Ð½Ð½Ñ‹Ðµ Ð¿Ð¾ Date Range Ð´Ð°Ð½Ð½Ñ‹Ðµ
        current_selected_item: Ð’Ñ‹Ð±Ñ€Ð°Ð½Ð½Ñ‹Ð¹ item key
        item_record: ÐœÐµÑ‚Ð°Ð´Ð°Ð½Ð½Ñ‹Ðµ item
        show_volume: ÐŸÐ¾ÐºÐ°Ð·Ñ‹Ð²Ð°Ñ‚ÑŒ Ð»Ð¸ Ð¾Ð±ÑŠÑ‘Ð¼ Ð½Ð° Ð³Ñ€Ð°Ñ„Ð¸ÐºÐµ
        show_usd: ÐŸÐ¾ÐºÐ°Ð·Ñ‹Ð²Ð°Ñ‚ÑŒ Ð»Ð¸ Ð² USD
        current_gun_price: Ð¢ÐµÐºÑƒÑ‰Ð°Ñ Ñ†ÐµÐ½Ð° GUN
        show_trend_line: ÐŸÐ¾ÐºÐ°Ð·Ñ‹Ð²Ð°Ñ‚ÑŒ Ð»Ð¸ prepared Trend Line
        item_view_mode: "chart" Ð¸Ð»Ð¸ "table" - from sidebar
        items_per_page: Rows per table page
    """
    
    # Extract item details
    item_name = df['name'].iloc[0] if 'name' in df.columns and not df.empty else current_selected_item.rsplit(' ', 1)[0]
    rarity = df['rarity'].iloc[0] if 'rarity' in df.columns and not df.empty else current_selected_item.rsplit(' ', 1)[-1]
    
    # Calculate metrics
    metrics = _build_item_card_metrics(filtered_df, df, show_usd, current_gun_price)
    
    # Load ranking metrics (optional)
    ranking_metrics = _load_item_market_ranking_metrics(item_name, rarity, period="all")
    supply_record, supply_rank = get_item_supply_with_rank(item_record.get('item_key', current_selected_item))
    trend_df = _load_item_trend_data(item_record) if show_trend_line else pd.DataFrame()

    st.markdown("""
        <style>
        .item-overview-header {
            margin-bottom: 16px;
        }

        .item-overview-header h3 {
            margin: 0 0 4px 0;
            border-bottom: 2px solid var(--otg-accent);
            padding-bottom: 6px;
            text-transform: uppercase;
            font-size: 16px;
            letter-spacing: 1px;
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
            color: var(--otg-accent);
            font-weight: 700;
        }

        .item-overview-subtitle {
            margin-top: 4px;
            margin-bottom: 0;
            color: var(--otg-text-secondary);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        @media (min-width: 769px) {
            .st-key-item_sales_table_wrapper {
                margin-top: -8px !important;
            }
        }

        </style>
        <div class="item-overview-header">
            <h3>ITEM ANALYTICS</h3>
            <div class="item-overview-subtitle">SELECTED ITEM MARKET OVERVIEW</div>
        </div>
    """, unsafe_allow_html=True)
    
    is_mobile_chart = bool(st.session_state.get('item_is_mobile_viewport', False))
    effective_item_view_mode = "chart" if is_mobile_chart else item_view_mode

    if highlight_wallet:
        st.markdown(
            '<div class="wallet-highlight-legend"><span style="color:#8B6FAE">● BUY</span> '
            '<span style="color:#6E9B78">● SELL</span> '
            '<span style="color:#85858E">● OTHER</span></div>',
            unsafe_allow_html=True,
        )

    if is_mobile_chart:
        _render_item_card(df, filtered_df, item_name, rarity, metrics, ranking_metrics, show_usd, current_gun_price, supply_record, supply_rank)
        _render_item_chart(
            filtered_df,
            show_volume,
            show_usd,
            current_gun_price,
            show_trend_line,
            trend_df,
            mobile_layout=True
            , highlight_wallet=highlight_wallet
        )
        return

    # Desktop two-column layout: 17% left, 83% right
    col_left, col_right = st.columns([0.17, 0.83])
    
    with col_left:
        _render_item_card(df, filtered_df, item_name, rarity, metrics, ranking_metrics, show_usd, current_gun_price, supply_record, supply_rank)
    
    with col_right:
        if effective_item_view_mode == "chart":
            _render_item_chart(
                filtered_df,
                show_volume,
                show_usd,
                current_gun_price,
                show_trend_line,
                trend_df,
                mobile_layout=False
                , highlight_wallet=highlight_wallet
            )
        elif effective_item_view_mode == "table":
            with st.container(key="item_sales_table_wrapper"):
                _render_item_sales_table(filtered_df, show_usd, current_gun_price, items_per_page)
