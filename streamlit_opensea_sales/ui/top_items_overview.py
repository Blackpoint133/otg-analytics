"""
Top Items Analytics UI Page.

technical diagnostic text technical diagnostic text technical diagnostic text TOP ITEMS ANALYTICS.

technical diagnostic text:
- technical diagnostic text "TOP ITEMS ANALYTICS"
- Top Items cards grid technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
- technical diagnostic text card technical diagnostic text:
  * technical diagnostic text technical diagnostic text
  * technical diagnostic text
  * technical diagnostic text technical diagnostic text technical diagnostic text
  * technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
  * technical diagnostic text technical diagnostic text technical diagnostic text ITEM ANALYTICS technical diagnostic text technical diagnostic text technical diagnostic text
"""

import streamlit as st
import pandas as pd
from typing import Optional
from html import escape
from urllib.parse import quote_plus
import textwrap

import market_data_access as mda
from data_access import load_items_index
from formatters import format_number, format_metric_value, format_historical_metric_pair, get_rarity_style
from gunzscope_supply import dense_supply_ranks, read_current_snapshot, valid_supply


# Image URL normalization
IMAGE_CDN_BASE = "https://cdne-g01-livepc-wu-itemsthumbnails.azureedge.net"

_MARKET_METRIC_COLUMNS = (
    'market_strength_score', 'liquidity_score', 'volume_gun', 'volume_usd',
    'weighted_volume_gun', 'period_events', 'active_trading_days',
    'avg_price_gun', 'avg_price_usd', 'transactions',
)


def _normalize_top_item_image_url(image_url):
    """
    Normalize image URLs for Top Items rendering.
    
    Handles both absolute URLs and relative paths starting with /ExportedAssets/.
    
    Args:
        image_url: Raw image URL from CSV
        
    Returns:
        Normalized URL or empty string if None/NaN/blank
    """
    if image_url is None or pd.isna(image_url):
        return ""
    value = str(image_url).strip()
    if not value:
        return ""
    if value.startswith("/ExportedAssets/"):
        return IMAGE_CDN_BASE + value
    return value


def _build_item_mode_url(item_name: str, rarity: str) -> str:
    """Build the same ITEM Analytics URL used by Top Items cards."""
    item_query = f"{str(item_name).strip()} {str(rarity).strip()}"
    item_encoded = quote_plus(item_query)
    return f"?mode=item&item={item_encoded}&page=1"


def _format_rank(value) -> str:
    """Format prepared integer rank values for Top Items UI."""
    if value is None or pd.isna(value):
        return "-"
    try:
        rank = int(float(value))
    except (TypeError, ValueError, OverflowError):
        return "-"
    if rank <= 0:
        return "-"
    return f"#{rank}"


def _load_global_total_supply_candidates() -> Optional[pd.DataFrame]:
    """Load the complete tracked OTG catalog for global Supply ranking."""
    items_index, diagnostics = load_items_index()
    if not diagnostics.success or not items_index:
        return None

    rows = []
    for item_key, record in items_index.items():
        if not isinstance(record, dict):
            continue
        rows.append({
            'item_key': item_key,
            'item_name': record.get('display_name', ''),
            'rarity': record.get('rarity', ''),
            'image_url': record.get('image_url', ''),
        })
    return pd.DataFrame(rows)


def _load_all_time_market_metrics() -> Optional[pd.DataFrame]:
    """Load the complete all-time market metrics table used for enrichment."""
    path = mda.get_market_overview_dir() / "top_items_by_liquidity.csv"
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except (OSError, ValueError, pd.errors.ParserError):
        return None


def _catalog_identity_map(catalog: pd.DataFrame) -> dict:
    """Build an exact, collision-checked (name, rarity) -> catalog key map."""
    required = {'item_key', 'item_name', 'rarity'}
    if not required.issubset(catalog.columns):
        raise ValueError("catalog identity columns are missing")
    work = catalog[['item_key', 'item_name', 'rarity']].copy()
    work['_identity'] = list(zip(work['item_name'], work['rarity']))
    if work['_identity'].duplicated().any():
        raise ValueError("duplicate catalog (item_name, rarity) identity")
    return dict(zip(work['_identity'], work['item_key']))


def _enrich_with_all_time_market_metrics(catalog_rows: pd.DataFrame, market_rows: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Join all-time market metrics by exact name+rarity, never raw item_key."""
    result = catalog_rows.copy()
    if market_rows is None:
        for column in _MARKET_METRIC_COLUMNS:
            if column not in result.columns:
                result[column] = pd.NA
        return result
    required = {'item_name', 'rarity'}
    if not required.issubset(market_rows.columns):
        raise ValueError("market identity columns are missing")
    market = market_rows.copy()
    market['_identity'] = list(zip(market['item_name'], market['rarity']))
    if market['_identity'].duplicated().any():
        raise ValueError("duplicate market (item_name, rarity) identity")
    catalog = result.copy()
    catalog['_identity'] = list(zip(catalog['item_name'], catalog['rarity']))
    if catalog['_identity'].duplicated().any():
        raise ValueError("duplicate catalog (item_name, rarity) identity")
    available = [column for column in _MARKET_METRIC_COLUMNS if column in market.columns]
    joined = catalog.merge(
        market[['_identity', *available]], on='_identity', how='left',
        validate='one_to_one', suffixes=('', '_market'),
    )
    for column in _MARKET_METRIC_COLUMNS:
        market_column = f'{column}_market'
        if market_column in joined.columns:
            joined[column] = joined[market_column]
            joined = joined.drop(columns=[market_column])
        elif column not in joined.columns:
            joined[column] = pd.NA
    return joined.drop(columns=['_identity'])


def _attach_canonical_item_keys(top_items: pd.DataFrame) -> pd.DataFrame:
    """Attach canonical catalog keys to period market rows for Supply lookup."""
    catalog_data, diagnostics = load_items_index()
    if not diagnostics.success or not catalog_data:
        result = top_items.copy()
        result['_canonical_item_key'] = pd.NA
        return result
    catalog_rows = pd.DataFrame([
        {'item_key': key, 'item_name': record.get('display_name', ''), 'rarity': record.get('rarity', '')}
        for key, record in catalog_data.items() if isinstance(record, dict)
    ])
    identity_map = _catalog_identity_map(catalog_rows)
    result = top_items.copy()
    result['_canonical_item_key'] = [
        identity_map.get((name, rarity), pd.NA)
        for name, rarity in zip(result['item_name'], result['rarity'])
    ]
    return result


def _attach_supply_metadata(top_items: pd.DataFrame, snapshot=None) -> pd.DataFrame:
    """Attach local Supply and global dense rank without changing row order."""
    result = top_items.copy()
    data = snapshot if snapshot is not None else read_current_snapshot()
    ranks = dense_supply_ranks(data)
    records = data.get('items', {}) if isinstance(data, dict) else {}
    keys = result.get('_canonical_item_key', result.get('item_key', pd.Series(pd.NA, index=result.index)))

    def supply_for(key):
        record = records.get(key) if isinstance(records, dict) and pd.notna(key) else None
        value = record.get('supply') if isinstance(record, dict) else None
        return value if record and record.get('status') in {'ok', 'stale'} and valid_supply(value) else pd.NA

    result['_supply'] = [supply_for(key) for key in keys]
    result['_supply_rank'] = [ranks.get(key, pd.NA) if pd.notna(key) else pd.NA for key in keys]
    return result


def _prepare_total_supply_data(top_items: pd.DataFrame, snapshot=None, limit: Optional[int] = None) -> pd.DataFrame:
    """Attach local Supply values and apply deterministic scarcity ordering."""
    display_data = _attach_supply_metadata(top_items, snapshot)
    display_data['_supply_missing'] = display_data['_supply'].isna()
    display_data = display_data.sort_values(
        ['_supply_missing', '_supply', 'item_key'],
        ascending=[True, True, True],
        kind='stable',
        na_position='last',
    ).reset_index(drop=True)
    display_data['display_rank'] = display_data['_supply_rank']
    if limit is not None:
        display_data = display_data.head(limit).reset_index(drop=True)
    return display_data


def render_top_items_overview(show_usd: bool = False, current_gun_price: float = 0.03, ranking_mode: str = 'volume', period: str = 'all', top_items_view: str = 'cards'):
    """
    technical diagnostic text technical diagnostic text technical diagnostic text Top Items Analytics technical diagnostic text.
    
    Args:
        show_usd: technical diagnostic text technical diagnostic text USD technical diagnostic text
        current_gun_price: technical diagnostic text technical diagnostic text GUN technical diagnostic text technical diagnostic text
        ranking_mode: technical diagnostic text technical diagnostic text ('volume', 'liquidity', 'market_strength')
        period: technical diagnostic text technical diagnostic text ('all', '30d', '7d', '1d')
        top_items_view: technical diagnostic text technical diagnostic text ('cards' technical diagnostic text 'chart')
    """
    
    # technical implementation note technical implementation note data
    status = mda.get_market_data_status()
    if status['status'] != 'OK':
        _render_no_data_state(status)
        return
    
    # Get all data
    cache_buster = mda._get_cache_buster()
    
    # Render top items section with current ranking mode and period
    _render_top_items_section(cache_buster=cache_buster, show_usd=show_usd, current_gun_price=current_gun_price, ranking_mode=ranking_mode, period=period, top_items_view=top_items_view)
    
    st.markdown("---")
    
    # Footer
    _render_top_items_footer()


def _render_no_data_state(status: dict):
    """technical documentation state technical documentation technical documentation technical documentation."""
    st.markdown("## ⚠️ Top Items Data Unavailable")
    
    if status['status'] == 'MISSING':
        st.warning(
            "Top items analytics data is not yet available. "
            "The backend market overview builder needs to run first. "
            "Please wait for the service to start or run the builder manually."
        )
        st.info(
            "Run: `python import_opensea_sales_market_overview.py` "
            "or check if the service `OTG_import_opensea_sales_market_overview` is running."
        )
    else:
        st.error(status.get('message', 'Unknown error loading top items data'))
    
    st.markdown("---")
    st.markdown("**Status:** `{}`".format(status['status']))


def _render_top_items_footer():
    """Footer section for Top Items page."""
    # Footer can be customized later if needed
    pass


def _render_top_items_section(cache_buster: str, show_usd: bool = False, current_gun_price: float = 0.03, ranking_mode: str = 'volume', period: str = 'all', top_items_view: str = 'cards'):
    """
    technical diagnostic text Top Items section technical diagnostic text technical diagnostic text content renderer.
    
    Args:
        cache_buster: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
        show_usd: technical diagnostic text technical diagnostic text USD technical diagnostic text
        current_gun_price: technical diagnostic text technical diagnostic text GUN
        ranking_mode: technical diagnostic text technical diagnostic text ('volume', 'liquidity', 'market_strength')
        period: technical diagnostic text technical diagnostic text ('all', '30d', '7d', '1d')
        top_items_view: technical diagnostic text technical diagnostic text ('cards', 'chart', 'table')
    """
    
    # Determine title and subtitle based on ranking mode
    ranking_title = "TOP 20 ITEMS"
    if ranking_mode == 'volume':
        ranking_subtitle = "Sorted by total trading volume"
    elif ranking_mode == 'liquidity':
        ranking_subtitle = "Sorted by Total Trading Liquidity"
    elif ranking_mode == 'market_strength':
        ranking_subtitle = "Sorted by Market Strength Score"
    elif ranking_mode == 'total_supply':
        ranking_subtitle = "Sorted by Lowest Current Supply"
    else:
        # Fallback
        ranking_mode = 'volume'
        ranking_subtitle = "Sorted by total trading volume"
    
    # Determine period label
    period_labels = {
        'all': 'ALL-TIME RANKING',
        '30d': 'ROLLING 30-DAY RANKING',
        '7d': 'ROLLING 7-DAY RANKING',
        '1d': 'ROLLING 24-HOUR RANKING'
    }
    period_label = 'GLOBAL CURRENT SUPPLY' if ranking_mode == 'total_supply' else period_labels.get(period, 'ALL-TIME RANKING')
    
    # Section heading with title and subtitle
    st.markdown(f"""
        <style>
        .top-items-ranking-header {{
            margin-bottom: 16px;
        }}
        .top-items-ranking-header h3 {{
            margin: 0 0 4px 0;
            border-bottom: 2px solid var(--otg-accent);
            padding-bottom: 6px;
            text-transform: uppercase;
            font-size: 16px;
            letter-spacing: 1px;
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
            color: var(--otg-accent);
            font-weight: 700;
        }}
        .top-items-ranking-subtitle {{
            font-size: 13px;
            color: var(--otg-text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 4px;
            margin-bottom: 4px;
        }}
        .top-items-ranking-period {{
            font-size: 11px;
            color: var(--otg-text-tertiary);
            text-transform: uppercase;
            letter-spacing: 0.4px;
            margin-top: 4px;
            margin-bottom: 12px;
        }}
        </style>
        <div class="top-items-ranking-header">
            <h3>{ranking_title}</h3>
            <div class="top-items-ranking-subtitle">{ranking_subtitle}</div>
            <div class="top-items-ranking-period">{period_label}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Market modes use their existing period-specific prepared rankings. Supply
    # mode is global and must not use a period-specific Volume candidate list.
    if ranking_mode == 'total_supply':
        top_items = _load_global_total_supply_candidates()
        if top_items is not None:
            top_items = _enrich_with_all_time_market_metrics(top_items, _load_all_time_market_metrics())
    else:
        top_items = mda.load_top_items_ranking(
            ranking_mode=ranking_mode,
            period=period,
            cache_buster=cache_buster,
            limit=20
        )
    
    # Handle missing or empty period data
    if top_items is None:
        st.warning("TOP ITEMS DATA UNAVAILABLE FOR SELECTED PERIOD")
        return
    
    if len(top_items) == 0:
        st.info("NO SALES IN SELECTED PERIOD")
        return
    
    # For Volume mode with USD toggle enabled, re-rank by volume_usd for display
    if ranking_mode == 'total_supply':
        display_data = _prepare_total_supply_data(top_items, limit=20)
    else:
        display_data = _attach_supply_metadata(_attach_canonical_item_keys(top_items))
    if ranking_mode == 'total_supply':
        # Global Supply rows intentionally have no market rank column.
        display_data['display_rank'] = display_data['_supply_rank']
    elif ranking_mode == 'volume' and show_usd and 'volume_usd' in display_data.columns:
        # Create a copy and sort by volume_usd descending, then re-assign display ranks
        display_data = display_data.sort_values('volume_usd', ascending=False).reset_index(drop=True)
        # Create a new rank column for display (1-20)
        display_data['display_rank'] = range(1, len(display_data) + 1)
    else:
        # For other modes or when USD is off, use original ranking
        display_data['display_rank'] = display_data['rank']
    
    # Render appropriate view (cards, chart, or table)
    if top_items_view == 'chart':
        _render_top_items_chart_view(display_data, ranking_mode=ranking_mode, show_usd=show_usd, current_gun_price=current_gun_price)
    elif top_items_view == 'table':
        _render_top_items_table_view(display_data, ranking_mode=ranking_mode, show_usd=show_usd, current_gun_price=current_gun_price)
    else:
        # Default to cards view
        _render_top_items_card_view(display_data, show_usd=show_usd, current_gun_price=current_gun_price, ranking_mode=ranking_mode)


def _render_top_items_card_view(top_items: pd.DataFrame, show_usd: bool = False, current_gun_price: float = 0.03, ranking_mode: str = 'volume'):
    """Render Top 20 Items as one compact HTML grid with clickable cards."""
    
    # CSS for card grid
    st.markdown("""
        <style>
        .top-items-card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            margin-top: 16px;
            margin-bottom: 16px;
        }
        
        .top-items-card-link {
            text-decoration: none !important;
            color: inherit !important;
        }
        
        .top-items-card-link:hover {
            text-decoration: none !important;
        }
        
        .top-items-card {
            background-color: #000000;
            border: 1px solid #1a1a1a;
            border-top: 2px solid var(--otg-accent);
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            transition: all 0.1s linear;
            cursor: pointer;
        }
        
        .top-items-card:hover {
            border-color: var(--otg-accent);
            box-shadow: 0 0 12px rgba(255, 0, 58, 0.2);
        }
        
        .top-items-card-rank {
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--otg-accent);
            margin-bottom: 4px;
        }
        
        .top-items-card-image-container {
            width: 100%;
            height: 160px;
            background-color: #0a0a0a;
            border: 1px solid #1a1a1a;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            margin-bottom: 4px;
        }
        
        .top-items-card-image {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }
        
        .top-items-card-placeholder {
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
        
        .top-items-card-name {
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
            font-size: 13px;
            font-weight: 700;
            color: var(--otg-text-primary);
            line-height: 1.3;
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .top-items-card-rarity {
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            color: var(--otg-accent);
            margin-bottom: 6px;
        }
        
        .top-items-card-metrics {
            display: flex;
            flex-direction: column;
            gap: 4px;
            font-size: 11px;
        }
        
        .top-items-card-metric-row {
            display: flex;
            justify-content: space-between;
            font-family: 'Space Mono', monospace;
        }
        
        .top-items-card-metric-label {
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            color: var(--otg-text-secondary);
            font-size: 10px;
        }
        
        .top-items-card-metric-value {
            font-weight: 700;
            color: var(--otg-text-primary);
            text-align: right;
        }
        
        .top-items-card-volume {
            padding-top: 6px;
            border-top: 1px solid #1a1a1a;
            margin-top: 6px;
        }
        
        .top-items-card-volume-label {
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            color: var(--otg-text-secondary);
            margin-bottom: 2px;
        }
        
        .top-items-card-volume-value {
            font-size: 16px;
            font-weight: 700;
            color: var(--otg-accent);
            font-family: 'Space Mono', monospace;
        }
        </style>
    """, unsafe_allow_html=True)
    
    cards_html_parts = ['<div class="top-items-card-grid">']
    
    # Check if enriched USD data is available
    has_usd_data = 'volume_usd' in top_items.columns and 'avg_price_usd' in top_items.columns
    
    for idx, row in top_items.iterrows():
        display_rank = _format_rank(row.get('display_rank')) if ranking_mode == 'total_supply' else f"#{row.get('display_rank', row['rank'])}"
        item_name = str(row['item_name']).strip()
        rarity = str(row['rarity']).strip()
        
        image_url = row.get('image_url', '')
        
        item_url = _build_item_mode_url(item_name, rarity)
        
        # Escape HTML attributes
        item_name_safe = escape(item_name, quote=True)
        rarity_safe = escape(rarity, quote=True)
        
        # Get rarity color
        rarity_color, _ = get_rarity_style(rarity)
        
        # Normalize image URL
        normalized_image_url = _normalize_top_item_image_url(image_url)
        
        if normalized_image_url:
            safe_image_url = escape(normalized_image_url, quote=True)
            image_html = f'<img src="{safe_image_url}" class="top-items-card-image" alt="{item_name_safe}">'
        else:
            image_html = '<div class="top-items-card-placeholder">NO IMAGE</div>'
        
        # Build metrics based on ranking mode
        metrics_html = '<div class="top-items-card-metrics">'
        volume_section_html = ''
        
        if ranking_mode == 'volume':
            # Volume mode: main metric is Volume (GUN or USD based on toggle)
            transactions = int(row['transactions'])
            volume_gun = row['volume_gun']
            avg_price_gun = row['avg_price_gun']
            volume_usd = row.get('volume_usd', 0) if has_usd_data else 0
            avg_price_usd = row.get('avg_price_usd', 0) if has_usd_data else 0
            
            metrics_html += (
                '<div class="top-items-card-metric-row">'
                '<span class="top-items-card-metric-label">Transactions</span>'
                f'<span class="top-items-card-metric-value">{transactions:,}</span>'
                '</div>'
            )
            
            # Only show Avg Price if it has valid data
            if has_usd_data and pd.notna(avg_price_usd) and avg_price_usd > 0:
                avg_price_formatted = format_historical_metric_pair(
                    avg_price_gun, avg_price_usd, show_usd, currency='GUN',
                    usd_label='USD', gun_label='GUN'
                )
                metrics_html += (
                    '<div class="top-items-card-metric-row">'
                    '<span class="top-items-card-metric-label">Avg Price</span>'
                    f'<span class="top-items-card-metric-value">{avg_price_formatted}</span>'
                    '</div>'
                )
            elif pd.notna(avg_price_gun) and avg_price_gun > 0:
                avg_price_formatted = format_metric_value(avg_price_gun, show_usd, current_gun_price, currency='GUN')
                metrics_html += (
                    '<div class="top-items-card-metric-row">'
                    '<span class="top-items-card-metric-label">Avg Price</span>'
                    f'<span class="top-items-card-metric-value">{avg_price_formatted}</span>'
                    '</div>'
                )
            
            # Build volume section - show based on toggle
            if has_usd_data and pd.notna(volume_usd) and volume_usd > 0:
                volume_formatted = format_historical_metric_pair(
                    volume_gun, volume_usd, show_usd, currency='GUN',
                    usd_label='USD', gun_label='GUN'
                )
                volume_label = 'Volume (GUN/USD)'
            else:
                volume_formatted = format_metric_value(volume_gun, show_usd, current_gun_price, currency='GUN')
                volume_label = 'Volume (USD)' if show_usd else 'Volume (GUN)'
            
            volume_section_html = (
                '<div class="top-items-card-volume">'
                f'<div class="top-items-card-volume-label">{volume_label}</div>'
                f'<div class="top-items-card-volume-value">{volume_formatted}</div>'
                '</div>'
            )
        
        elif ranking_mode == 'liquidity':
            # Liquidity mode: main metric is Liquidity Score
            liquidity_score = row.get('liquidity_score', 0)
            period_events = int(row.get('period_events', 0))
            active_days = int(row.get('active_trading_days', 0))
            weighted_volume_gun = row.get('weighted_volume_gun', 0)
            
            metrics_html += (
                '<div class="top-items-card-metric-row">'
                '<span class="top-items-card-metric-label">Period Events</span>'
                f'<span class="top-items-card-metric-value">{period_events:,}</span>'
                '</div>'
            )
            metrics_html += (
                '<div class="top-items-card-metric-row">'
                '<span class="top-items-card-metric-label">Active Days</span>'
                f'<span class="top-items-card-metric-value">{active_days}</span>'
                '</div>'
            )
            
            volume_section_html = (
                '<div class="top-items-card-volume">'
                '<div class="top-items-card-volume-label">Liquidity Score</div>'
                f'<div class="top-items-card-volume-value">{liquidity_score:.2f}</div>'
                '</div>'
            )
        
        elif ranking_mode == 'market_strength':
            # Market Strength mode: main metric is Market Strength Score
            market_strength_score = row.get('market_strength_score', 0)
            rank_volume = _format_rank(row.get('rank_volume'))
            rank_liquidity = _format_rank(row.get('rank_liquidity'))
            
            metrics_html += (
                '<div class="top-items-card-metric-row">'
                '<span class="top-items-card-metric-label">Volume Rank</span>'
                f'<span class="top-items-card-metric-value">{rank_volume}</span>'
                '</div>'
            )
            metrics_html += (
                '<div class="top-items-card-metric-row">'
                '<span class="top-items-card-metric-label">Liquidity Rank</span>'
                f'<span class="top-items-card-metric-value">{rank_liquidity}</span>'
                '</div>'
            )
            
            volume_section_html = (
                '<div class="top-items-card-volume">'
                '<div class="top-items-card-volume-label">Market Strength</div>'
                f'<div class="top-items-card-volume-value">{market_strength_score:.3f}</div>'
                '</div>'
            )

        elif ranking_mode == 'total_supply':
            # Supply metadata is rendered below for every ranking mode.
            pass

        supply_value = row.get('_supply')
        supply_text = f"{int(supply_value):,}" if pd.notna(supply_value) and valid_supply(supply_value) else 'N/A'
        metrics_html += (
            '<div class="top-items-card-metric-row">'
            '<span class="top-items-card-metric-label">TOTAL SUPPLY</span>'
            f'<span class="top-items-card-metric-value">{supply_text}</span>'
            '</div>'
            '<div class="top-items-card-metric-row">'
            '<span class="top-items-card-metric-label">SUPPLY RANK</span>'
            f'<span class="top-items-card-metric-value">{_format_rank(row.get("_supply_rank"))}</span>'
            '</div>'
        )
        
        metrics_html += '</div>'
        
        # Build card HTML wrapped in anchor link
        card_html = (
            f'<a href="{item_url}" class="top-items-card-link">'
            '<div class="top-items-card">'
            f'<div class="top-items-card-rank">{display_rank}</div>'
            f'<div class="top-items-card-image-container">{image_html}</div>'
            f'<div class="top-items-card-name">{item_name_safe}</div>'
            f'<div class="top-items-card-rarity" style="color: {rarity_color};">{rarity_safe}</div>'
            f'{metrics_html}'
            f'{volume_section_html}'
            '</div>'
            '</a>'
        )
        
        cards_html_parts.append(card_html)
    
    cards_html_parts.append('</div>')
    st.markdown(''.join(cards_html_parts), unsafe_allow_html=True)


def _render_top_items_chart_view(top_items: pd.DataFrame, ranking_mode: str = 'volume', show_usd: bool = False, current_gun_price: float = 0.03):
    """
    Render Top 20 Items as a custom HTML/CSS leaderboard with thumbnails.
    
    Layout per row:
    [48x48 thumbnail] [rank + item name + rarity] [horizontal bar] [value]
    
    Args:
        top_items: DataFrame with top items data
        ranking_mode: 'volume', 'liquidity', or 'market_strength'
        show_usd: whether to use USD for volume mode
        current_gun_price: current GUN price for conversion
    """
    
    # Determine metric column and label based on ranking mode
    if ranking_mode == 'volume':
        if show_usd and 'volume_usd' in top_items.columns:
            metric_col = 'volume_usd'
            metric_label = 'Volume (USD)'
        else:
            metric_col = 'volume_gun'
            metric_label = 'Volume (GUN)'
        metric_format = ',.0f'
    elif ranking_mode == 'liquidity':
        metric_col = 'liquidity_score'
        metric_label = 'Liquidity Score'
        metric_format = '.2f'
    elif ranking_mode == 'market_strength':
        metric_col = 'market_strength_score'
        metric_label = 'Market Strength'
        metric_format = '.3f'
    elif ranking_mode == 'total_supply':
        metric_col = '_supply'
        metric_label = 'Total Supply'
        metric_format = ',.0f'
    else:
        metric_col = 'volume_gun'
        metric_label = 'Volume (GUN)'
        metric_format = ',.0f'
    
    # Get metric values and normalize for bar width
    metric_values = pd.to_numeric(top_items[metric_col], errors='coerce').fillna(0).values
    max_value = metric_values.max() if len(metric_values) > 0 else 1
    
    # Normalize to percentage (0-100) for bar width
    bar_widths = [(v / max_value) * 100 if max_value > 0 else 0 for v in metric_values]
    
    # Format values for display
    if metric_format == ',.0f':
        formatted_values = ["N/A" if pd.isna(row.get(metric_col)) else f"{v:,.0f}" for v, (_, row) in zip(metric_values, top_items.iterrows())]
    else:
        formatted_values = [f"{v:{metric_format}}" for v in metric_values]
    
    # Build rows HTML
    rows_html = []
    for idx, (_, row) in enumerate(top_items.iterrows()):
        display_rank = _format_rank(row.get('display_rank')) if ranking_mode == 'total_supply' else f"#{row.get('display_rank', row['rank'])}"
        item_name = str(row['item_name']).strip()
        rarity = str(row['rarity']).strip()
        image_url = row.get('image_url', '')
        bar_width = bar_widths[idx]
        value_str = formatted_values[idx]
        item_url = _build_item_mode_url(item_name, rarity)
        item_name_safe = escape(item_name, quote=True)
        rarity_safe = escape(rarity, quote=True)
        item_url_safe = escape(item_url, quote=True)
        
        # Get rarity color
        rarity_color, _ = get_rarity_style(rarity)
        
        # Normalize and build thumbnail
        normalized_image_url = _normalize_top_item_image_url(image_url)
        if normalized_image_url:
            safe_image_url = escape(normalized_image_url, quote=True)
            thumbnail_html = f'<a href="{item_url_safe}" class="leaderboard-image-link"><img src="{safe_image_url}" alt="{item_name_safe}"></a>'
        else:
            thumbnail_html = f'<a href="{item_url_safe}" class="leaderboard-image-link">-</a>'
        
        # Build row
        row_html = f'<div class="leaderboard-row"><div class="leaderboard-thumbnail">{thumbnail_html}</div><div class="leaderboard-info"><div class="leaderboard-rank">{display_rank}</div><a href="{item_url_safe}" class="leaderboard-item-link"><div class="leaderboard-item-name">{item_name_safe}</div></a><div class="leaderboard-rarity" style="color: {rarity_color};">{rarity_safe}</div></div><div class="leaderboard-bar-container"><div class="leaderboard-bar"><div class="leaderboard-bar-fill" style="width: {bar_width:.1f}%;"></div></div><div class="leaderboard-value">{value_str}</div></div></div>'
        rows_html.append(row_html)
    
    # Build complete HTML with CSS
    leaderboard_html = textwrap.dedent("""
<style>
.top-items-leaderboard {
    margin-top: 16px;
    margin-bottom: 16px;
    border: 1px solid #1a1a1a;
    background-color: #000000;
}
.leaderboard-row {
    display: flex;
    align-items: center;
    padding: 12px;
    border-bottom: 1px solid #1a1a1a;
    gap: 12px;
    transition: all 0.1s linear;
}
.leaderboard-row:hover {
    background-color: #0a0a0a;
}
.leaderboard-row:last-child {
    border-bottom: none;
}
.leaderboard-thumbnail {
    flex-shrink: 0;
    width: 48px;
    height: 48px;
    background-color: #0a0a0a;
    border: 1px solid #1a1a1a;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    border-radius: 1px;
}
.leaderboard-thumbnail img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}
.leaderboard-image-link,
.leaderboard-item-link {
    color: inherit !important;
    text-decoration: none !important;
}
.leaderboard-image-link {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
}
.leaderboard-info {
    flex: 0 0 auto;
    min-width: 180px;
    display: flex;
    flex-direction: column;
    gap: 2px;
}
.leaderboard-rank {
    font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: #FF003A;
}
.leaderboard-item-name {
    font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
    font-size: 12px;
    font-weight: 700;
    color: #FFFFFF;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    line-height: 1.2;
}
.leaderboard-rarity {
    font-family: 'Space Mono', monospace;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    color: #666;
}
.leaderboard-bar-container {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 100px;
}
.leaderboard-bar {
    flex: 1;
    height: 20px;
    background-color: #0a0a0a;
    border: 1px solid #1a1a1a;
    position: relative;
    overflow: hidden;
    border-radius: 1px;
}
.leaderboard-bar-fill {
    height: 100%;
    background-color: #FF003A;
    transition: width 0.3s ease;
}
.leaderboard-value {
    flex-shrink: 0;
    min-width: 70px;
    text-align: right;
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    color: #FFFFFF;
    letter-spacing: 0.3px;
}
@media (max-width: 768px) {
    .leaderboard-row {
        display: grid;
        grid-template-columns: 48px minmax(0, 1fr);
        align-items: center;
        gap: 8px 10px;
        padding: 10px;
    }
    .leaderboard-thumbnail {
        grid-column: 1;
        grid-row: 1;
    }
    .leaderboard-info {
        grid-column: 2;
        grid-row: 1;
        min-width: 0;
        width: 100%;
    }
    .leaderboard-item-name {
        overflow-wrap: anywhere;
    }
    .leaderboard-bar-container {
        grid-column: 1 / -1;
        grid-row: 2;
        min-width: 0;
        width: 100%;
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: center;
    }
    .leaderboard-value {
        min-width: max-content;
        white-space: nowrap;
    }
}
</style>
<div class="top-items-leaderboard">
""").strip() + '\n' + ''.join(rows_html) + '\n</div>'
    
    st.markdown(leaderboard_html, unsafe_allow_html=True)


def _render_top_items_table_view(top_items: pd.DataFrame, ranking_mode: str = 'volume', show_usd: bool = False, current_gun_price: float = 0.03):
    """
    Render Top 20 Items as a 13-column comprehensive HTML/CSS table.
    
    Shows all 20 rows with all available metrics (not mode-specific).
    Allows user to sort by one metric while comparing all others.
    
    All 13 columns:
    1. Rank
    2. Image
    3. Item
    4. Rarity
    5. Market Strength
    6. Liquidity Score
    7. Volume (GUN)
    8. Volume (USD)
    9. Weighted Volume (GUN)
    10. Events
    11. Active Days
    12. Avg Price (GUN)
    13. Avg Price (USD)
    
    Args:
        top_items: DataFrame with top items data
        ranking_mode: current ranking mode (not used for column selection, all shown)
        show_usd: whether to show USD values when available
        current_gun_price: current GUN price for conversion
    """
    
    # Build table rows HTML
    table_rows = []
    
    for idx, (_, row) in enumerate(top_items.iterrows()):
        display_rank = _format_rank(row.get('display_rank')) if ranking_mode == 'total_supply' else f"#{row.get('display_rank', row['rank'])}"
        item_name = str(row['item_name']).strip()
        rarity = str(row['rarity']).strip()
        item_url = _build_item_mode_url(item_name, rarity)
        item_url_safe = escape(item_url, quote=True)
        item_name_safe = escape(item_name, quote=True)
        
        # Normalize image URL
        raw_image_url = row.get('image_url', '')
        normalized_image_url = _normalize_top_item_image_url(raw_image_url)
        
        # Get rarity color
        rarity_color, _ = get_rarity_style(rarity)
        
        # Build image cell
        if normalized_image_url:
            safe_image_url = escape(normalized_image_url, quote=True)
            image_cell = f'<a href="{item_url_safe}" class="top-items-table-link"><img src="{safe_image_url}" alt="{item_name_safe}" style="max-width: 48px; max-height: 48px; object-fit: contain;"></a>'
        else:
            image_cell = ''
        
        # Extract all metric values
        market_strength_score = row.get('market_strength_score', 0)
        liquidity_score = row.get('liquidity_score', 0)
        volume_gun = row.get('volume_gun', 0)
        volume_usd = row.get('volume_usd', 0)
        weighted_volume_gun = row.get('weighted_volume_gun', 0)
        period_events = row.get('period_events', 0)
        active_days = row.get('active_trading_days', 0)
        avg_price_gun = row.get('avg_price_gun', 0)
        avg_price_usd = row.get('avg_price_usd', 0)
        total_supply = row.get('_supply')
        supply_rank = _format_rank(row.get('_supply_rank'))
        
        # Format missing metrics explicitly; valid zeroes remain visible.
        def optional_number(value, spec):
            return "N/A" if pd.isna(value) else format(value, spec)

        market_strength_str = optional_number(market_strength_score, '.3f')
        liquidity_str = optional_number(liquidity_score, '.2f')
        volume_gun_str = optional_number(volume_gun, ',.0f')
        volume_usd_str = optional_number(volume_usd, ',.0f')
        weighted_vol_str = optional_number(weighted_volume_gun, ',.0f')
        period_events_str = optional_number(period_events, ',.0f')
        active_days_str = optional_number(active_days, '.0f')
        avg_price_gun_str = optional_number(avg_price_gun, ',.2f')
        avg_price_usd_str = optional_number(avg_price_usd, ',.2f')
        
        # Build row with all 13 columns, all left-aligned (no inline text-align)
        supply_text = f"{int(total_supply):,}" if pd.notna(total_supply) and valid_supply(total_supply) else "N/A"
        supply_cells = f'<td>{supply_text}</td><td>{supply_rank}</td>'

        row_html = f'''<tr>
<td>{display_rank}</td>
<td style="text-align: center; padding: 4px;">{image_cell}</td>
<td style="text-transform: uppercase; letter-spacing: 0.3px; font-weight: 700; max-width: 140px; word-break: break-word;"><a href="{item_url_safe}" class="top-items-table-link">{item_name_safe}</a></td>
<td style="text-transform: uppercase; letter-spacing: 0.3px; font-size: 10px; font-weight: 700; color: {rarity_color};">{escape(rarity, quote=True)}</td>
<td>{market_strength_str}</td>
<td>{liquidity_str}</td>
<td>{volume_gun_str}</td>
<td>{volume_usd_str}</td>
<td>{weighted_vol_str}</td>
<td>{period_events_str}</td>
<td>{active_days_str}</td>
<td>{avg_price_gun_str}</td>
<td>{avg_price_usd_str}</td>
{supply_cells}
</tr>'''
        table_rows.append(row_html)
    
    # Build complete table HTML with the standard columns plus Supply columns in Supply mode
    table_html = textwrap.dedent(f"""
<style>
.top-items-table {{
    width: 100%;
    border-collapse: collapse;
    background-color: #000000;
    border: 1px solid #FF003A;
    font-family: 'Space Mono', monospace;
    font-size: 12px;
    margin-top: 16px;
    margin-bottom: 16px;
}}
.top-items-table thead {{
    background-color: #0a0a0a;
    border-bottom: 2px solid #FF003A;
}}
.top-items-table th {{
    color: #FF003A;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 10px 8px;
    text-align: left !important;
    font-size: 11px;
}}
.top-items-table tbody tr {{
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}}
.top-items-table tbody tr:hover {{
    background-color: #0a0a0a;
}}
.top-items-table td {{
    color: #FFFFFF;
    padding: 8px;
    text-align: left !important;
    font-size: 11px;
}}
.top-items-table-link {{
    color: inherit !important;
    text-decoration: none !important;
}}
.top-items-table-link:hover {{
    color: #FF003A !important;
}}
</style>
<table class="top-items-table">
<thead><tr>
<th>Rank</th>
<th>Image</th>
<th>Item</th>
<th>Rarity</th>
<th>Market Strength</th>
<th>Liquidity Score</th>
<th>Volume (GUN)</th>
<th>Volume (USD)</th>
<th>Weighted Vol (GUN)</th>
<th>Events</th>
<th>Active Days</th>
<th>Avg Price (GUN)</th>
<th>Avg Price (USD)</th>
<th>Total Supply</th>
<th>Supply Rank</th>
</tr></thead>
<tbody>
{''.join(table_rows)}
</tbody>
</table>
""").strip()
    
    st.markdown(table_html, unsafe_allow_html=True)
