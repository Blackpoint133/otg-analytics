"""
Market Overview UI Page.

technical diagnostic text technical diagnostic text technical diagnostic text MARKET ANALYTICS.

technical diagnostic text:
- technical diagnostic text technical diagnostic text technical diagnostic text
- KPI metrics cards
- 4 technical diagnostic text technical diagnostic text:
  * Daily Liquidity
  * Daily Volume
  * Monthly Liquidity
  * Monthly Volume
- Date range selector
- Token split technical diagnostic text
"""

import streamlit as st
import pandas as pd
from typing import Optional
from datetime import datetime, timedelta

import market_data_access as mda
from formatters import format_number, format_metric_value, format_historical_metric_pair
from charts_market import (
    build_daily_liquidity_chart,
    build_daily_volume_chart,
    build_monthly_liquidity_chart,
    build_monthly_volume_chart,
    build_token_split_chart
)
from ui.viewport import get_viewport_info


def _is_mobile_viewport(viewport_info: Optional[dict]) -> bool:
    """Return True only when the viewport component provides a mobile width."""
    if not isinstance(viewport_info, dict):
        return False

    viewport_width = viewport_info.get("width")
    if isinstance(viewport_width, int):
        return viewport_width <= 768

    return bool(viewport_info.get("isMobile", False))


def _get_market_period_label(period: str) -> str:
    labels = {
        'all': 'ALL TIME',
        '12m': '12 MONTH',
        '6m': '6 MONTH',
        '3m': '3 MONTH',
    }
    return labels.get(period, '12 MONTH')


def _get_market_period_bounds(daily_df: pd.DataFrame, period: str):
    """Resolve Market period bounds using latest available market data date."""
    if daily_df is None or daily_df.empty or 'date' not in daily_df.columns:
        return None, None, period == 'all'

    latest_date = daily_df['date'].max().normalize()
    if period == 'all':
        return daily_df['date'].min().normalize(), latest_date, True

    month_offsets = {
        '3m': 3,
        '6m': 6,
        '12m': 12,
    }
    months = month_offsets.get(period, 12)
    start_date = latest_date - pd.DateOffset(months=months)
    return start_date, latest_date, False


def _filter_market_chart_data(
    daily_df: pd.DataFrame,
    monthly_df: Optional[pd.DataFrame],
    period: str,
    start_date: Optional[pd.Timestamp],
    end_date: Optional[pd.Timestamp],
    is_all_time: bool
):
    """Filter prepared Market chart DataFrames once for all Market charts."""
    if is_all_time or start_date is None or end_date is None:
        return daily_df, monthly_df

    filtered_daily = daily_df[
        (daily_df['date'] >= start_date) &
        (daily_df['date'] <= end_date)
    ]

    filtered_monthly = monthly_df
    if monthly_df is not None:
        filtered_monthly = monthly_df[
            (monthly_df['month_end'] >= start_date) &
            (monthly_df['month_start'] <= end_date)
        ]

    return filtered_daily, filtered_monthly


def _filter_market_sales_data(
    sales_df: Optional[pd.DataFrame],
    start_date: Optional[pd.Timestamp],
    end_date: Optional[pd.Timestamp],
    is_all_time: bool
) -> Optional[pd.DataFrame]:
    """Filter transaction-level sales with the same period bounds as Market charts."""
    if sales_df is None or sales_df.empty or 'sale_date' not in sales_df.columns:
        return sales_df
    if is_all_time or start_date is None or end_date is None:
        return sales_df

    end_exclusive = end_date + pd.Timedelta(days=1)
    return sales_df[
        (sales_df['sale_date'] >= start_date) &
        (sales_df['sale_date'] < end_exclusive)
    ]


def _build_period_market_summary(filtered_sales_df: Optional[pd.DataFrame], fallback_summary: dict) -> dict:
    """Build exact period KPI summary from transaction-level sales rows."""
    if filtered_sales_df is None:
        return fallback_summary

    required_columns = {'price_gun', 'seller', 'buyer', 'name'}
    if filtered_sales_df.empty or not required_columns.issubset(filtered_sales_df.columns):
        return {
            'totals': {
                'transactions': 0,
                'volume_gun': 0.0,
                'unique_wallets': 0,
                'items_traded': 0,
            },
            'usd_pricing': {
                'total_volume_usd': 0.0,
            }
        }

    sellers = set(filtered_sales_df['seller'].dropna().unique())
    buyers = set(filtered_sales_df['buyer'].dropna().unique())
    total_volume_usd = 0.0
    if 'price_usd_at_sale' in filtered_sales_df.columns:
        total_volume_usd = float(filtered_sales_df['price_usd_at_sale'].dropna().sum())

    return {
        'totals': {
            'transactions': int(len(filtered_sales_df)),
            'volume_gun': float(filtered_sales_df['price_gun'].sum()),
            'unique_wallets': int(len(sellers | buyers)),
            'items_traded': int(filtered_sales_df['name'].nunique()),
        },
        'usd_pricing': {
            'total_volume_usd': total_volume_usd,
        }
    }


def _resolve_market_mobile_state() -> bool:
    """Use the last valid Market viewport result so reruns do not reset mobile charts."""
    if 'market_is_mobile_viewport' not in st.session_state:
        st.session_state.market_is_mobile_viewport = False

    viewport_info = get_viewport_info(key="market_charts_viewport")
    if isinstance(viewport_info, dict):
        viewport_width = viewport_info.get("width")
        if isinstance(viewport_width, int):
            st.session_state.market_is_mobile_viewport = viewport_width <= 768
        else:
            st.session_state.market_is_mobile_viewport = bool(viewport_info.get("isMobile", False))

    return bool(st.session_state.market_is_mobile_viewport)


def render_market_overview(show_usd: bool = False, current_gun_price: float = 0.03, show_token_price: bool = False):
    """technical documentation technical documentation technical documentation Market Overview technical documentation."""
    
    # technical implementation note technical implementation note data
    status = mda.get_market_data_status()
    if status['status'] != 'OK':
        _render_no_data_state(status)
        return

    market_time_range = st.session_state.get('market_time_range', '12m')
    period_label = _get_market_period_label(market_time_range)
    
    # Header - OTG style
    st.markdown(f"""
        <style>
        .market-header {{
            margin-bottom: 16px;
        }}
        .market-header h3 {{
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
        .market-subtitle {{
            margin-top: 4px;
            margin-bottom: 0;
            color: var(--otg-text-secondary);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        /* Reduce gap before metrics */
        .market-top-section {{
            display: flex;
            flex-direction: column;
            gap: 0;
        }}
        </style>
        <div class="market-top-section">
            <div class="market-header">
                <h3>MARKET ANALYTICS</h3>
                <div class="market-subtitle">OVERALL MARKET OVERVIEW ({period_label})</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Get all data
    cache_buster = mda._get_cache_buster()
    
    daily_df = mda.load_daily_market_metrics(cache_buster=cache_buster)
    monthly_df = mda.load_monthly_market_metrics(cache_buster=cache_buster)
    summary = mda.load_market_summary(cache_buster=cache_buster)
    sales_df = mda.load_enriched_market_sales(cache_buster=cache_buster)
    
    if daily_df is None or summary is None:
        _render_no_data_state({
            'status': 'ERROR',
            'message': 'Failed to load required data'
        })
        return

    start_date, end_date, is_all_time = _get_market_period_bounds(daily_df, market_time_range)
    chart_daily_df, chart_monthly_df = _filter_market_chart_data(
        daily_df,
        monthly_df,
        market_time_range,
        start_date,
        end_date,
        is_all_time
    )
    kpi_sales_df = _filter_market_sales_data(sales_df, start_date, end_date, is_all_time)
    kpi_summary = _build_period_market_summary(kpi_sales_df, summary)
    
    # Render KPI metrics
    _render_kpi_metrics(kpi_summary, show_usd=show_usd, current_gun_price=current_gun_price)
    
    st.markdown('<div class="market-section-divider"></div>', unsafe_allow_html=True)
    
    # Render main charts - styled to match MARKET ANALYTICS header
    st.markdown("""
        <style>
        .market-trends-header h3 {
            margin: 0 0 16px 0;
            border-bottom: 2px solid var(--otg-accent);
            padding-bottom: 6px;
            text-transform: uppercase;
            font-size: 16px;
            letter-spacing: 1px;
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
            color: var(--otg-accent);
            font-weight: 700;
        }
        </style>
        <div class="market-trends-header">
            <h3>MARKET TRENDS</h3>
        </div>
    """, unsafe_allow_html=True)
    
    is_mobile_market_chart = _resolve_market_mobile_state()

    if is_mobile_market_chart:
        daily_liq_fig = build_daily_liquidity_chart(chart_daily_df, mobile_layout=True)
        if daily_liq_fig:
            st.plotly_chart(
                daily_liq_fig,
                use_container_width=True,
                config={'displayModeBar': False},
                key='daily_liquidity'
            )

        daily_vol_fig = build_daily_volume_chart(
            chart_daily_df,
            show_usd=show_usd,
            current_gun_price=current_gun_price,
            show_token_price=show_token_price,
            mobile_layout=True
        )
        if daily_vol_fig:
            st.plotly_chart(
                daily_vol_fig,
                use_container_width=True,
                config={'displayModeBar': False},
                key='daily_volume'
            )

        if chart_monthly_df is not None:
            monthly_liq_fig = build_monthly_liquidity_chart(chart_monthly_df, mobile_layout=True)
            if monthly_liq_fig:
                st.plotly_chart(
                    monthly_liq_fig,
                    use_container_width=True,
                    config={'displayModeBar': False},
                    key='monthly_liquidity'
                )

        if chart_monthly_df is not None:
            monthly_vol_fig = build_monthly_volume_chart(
                chart_monthly_df,
                show_usd=show_usd,
                current_gun_price=current_gun_price,
                show_token_price=show_token_price,
                mobile_layout=True
            )
            if monthly_vol_fig:
                st.plotly_chart(
                    monthly_vol_fig,
                    use_container_width=True,
                    config={'displayModeBar': False},
                    key='monthly_volume'
                )
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            daily_liq_fig = build_daily_liquidity_chart(chart_daily_df)
            if daily_liq_fig:
                st.plotly_chart(
                    daily_liq_fig,
                    use_container_width=True,
                    config={'displayModeBar': False},
                    key='daily_liquidity'
                )
        
        with col2:
            daily_vol_fig = build_daily_volume_chart(
                chart_daily_df,
                show_usd=show_usd,
                current_gun_price=current_gun_price,
                show_token_price=show_token_price
            )
            if daily_vol_fig:
                st.plotly_chart(
                    daily_vol_fig,
                    use_container_width=True,
                    config={'displayModeBar': False},
                    key='daily_volume'
                )
        
        col3, col4 = st.columns(2)
        
        with col3:
            if chart_monthly_df is not None:
                monthly_liq_fig = build_monthly_liquidity_chart(chart_monthly_df)
                if monthly_liq_fig:
                    st.plotly_chart(
                        monthly_liq_fig,
                        use_container_width=True,
                        config={'displayModeBar': False},
                        key='monthly_liquidity'
                    )
        
        with col4:
            if chart_monthly_df is not None:
                monthly_vol_fig = build_monthly_volume_chart(
                    chart_monthly_df,
                    show_usd=show_usd,
                    current_gun_price=current_gun_price,
                    show_token_price=show_token_price
                )
                if monthly_vol_fig:
                    st.plotly_chart(
                        monthly_vol_fig,
                        use_container_width=True,
                        config={'displayModeBar': False},
                        key='monthly_volume'
                    )
    
    st.markdown("---")
    
    # Footer with build info
    _render_market_footer(status, summary)


def _render_kpi_metrics(summary: dict, show_usd: bool = False, current_gun_price: float = 0.03):
    """technical documentation KPI metrics cards technical documentation technical documentation custom HTML grid."""
    if not summary or 'totals' not in summary:
        return
    
    totals = summary['totals']
    
    # Check if enriched USD data is available
    has_usd_pricing = 'usd_pricing' in summary
    
    # Format values
    total_transactions = f"{totals.get('transactions', 0):,}"
    
    # Use enriched historical USD pair if available
    if has_usd_pricing:
        # Format with historical GUN/USD pair (not current-price estimated)
        gun_vol = totals.get('volume_gun', 0)
        usd_vol = summary['usd_pricing'].get('total_volume_usd', 0)
        total_volume_formatted = format_historical_metric_pair(
            gun_vol,
            usd_vol,
            show_usd,
            currency='GUN',
            usd_label='USD',
            gun_label='GUN'
        )
    else:
        # Fallback: use old method with current price
        total_volume_formatted = format_metric_value(
            totals.get('volume_gun', 0),
            show_usd,
            current_gun_price,
            currency='GUN'
        )
    
    unique_wallets = f"{totals.get('unique_wallets', 0):,}"
    items_traded = f"{totals.get('items_traded', 0):,}"
    
    # Render CSS separately (no indentation issues)
    st.markdown("""
        <style>
        .market-kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            column-gap: 48px;
            row-gap: 22px;
            margin-top: 16px;
            margin-bottom: 12px;
        }

        .market-kpi {
            min-height: 64px;
        }

        .market-kpi-label {
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            color: var(--otg-text-primary);
            margin-bottom: 8px;
        }

        .market-kpi-value {
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
            font-size: 28px;
            font-weight: 700;
            color: var(--otg-text-primary);
            letter-spacing: 0.5px;
            white-space: nowrap;
        }

        .market-kpi-with-border {
            border-left: 2px solid var(--otg-accent);
            padding-left: 12px;
        }

        @media (max-width: 768px) {
            .market-kpi-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                column-gap: 12px;
                row-gap: 14px;
                margin-top: 12px;
                margin-bottom: 10px;
            }

        .market-section-divider {
            border-top: 1px solid var(--otg-border);
            margin: 8px 0 12px 0;
        }

            .market-kpi {
                min-height: 58px;
                min-width: 0;
            }

            .market-kpi-with-border {
                border-left: 2px solid var(--otg-accent);
                padding-left: 8px;
                min-width: 0;
            }

            .market-kpi-label {
                font-size: 9px;
                line-height: 1.15;
                letter-spacing: 0.4px;
                margin-bottom: 6px;
                white-space: normal;
                word-break: normal;
                overflow-wrap: normal;
            }

            .market-kpi-value {
                font-size: 20px;
                line-height: 1.1;
                letter-spacing: 0.2px;
                white-space: normal;
                word-break: normal;
                overflow-wrap: anywhere;
                min-width: 0;
            }
        }

        .tooltip {
            position: relative;
            display: inline-block;
            cursor: help;
            border-bottom: 1px dotted var(--otg-accent);
        }

        .tooltip .tooltiptext {
            visibility: hidden;
            width: 140px;
            background-color: #1a1a1a;
            color: var(--otg-text-primary);
            text-align: center;
            border-radius: 4px;
            padding: 6px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -70px;
            opacity: 0;
            transition: opacity 0.3s;
            border: 1px solid var(--otg-accent);
            font-size: 12px;
        }

        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Build KPI HTML as compact fragments without leading indentation
    kpi_parts = [
        '<div class="market-kpi-grid">',
        '<div class="market-kpi market-kpi-with-border">',
        '<div class="market-kpi-label">Total Transactions</div>',
        f'<div class="market-kpi-value">{total_transactions}</div>',
        '</div>',
        '<div class="market-kpi market-kpi-with-border">',
        '<div class="market-kpi-label">Total Volume</div>',
        f'<div class="market-kpi-value">{total_volume_formatted}</div>',
        '</div>',
        '<div class="market-kpi market-kpi-with-border">',
        '<div class="market-kpi-label">Unique Wallets</div>',
        f'<div class="market-kpi-value">{unique_wallets}</div>',
        '</div>',
        '<div class="market-kpi market-kpi-with-border">',
        '<div class="market-kpi-label">Items Traded</div>',
        f'<div class="market-kpi-value">{items_traded}</div>',
        '</div>',
        '</div>',
    ]
    kpi_html = ''.join(kpi_parts)
    st.markdown(kpi_html, unsafe_allow_html=True)


def _render_no_data_state(status: dict):
    """technical documentation state technical documentation technical documentation technical documentation."""
    st.markdown("## ⚠️ Market Data Unavailable")
    
    if status['status'] == 'MISSING':
        st.warning(
            "Market analytics data is not yet available. "
            "The backend market overview builder needs to run first. "
            "Please wait for the service to start or run the builder manually."
        )
        st.info(
            "Run: `python import_opensea_sales_market_overview.py` "
            "or check if the service `OTG_import_opensea_sales_market_overview` is running."
        )
    else:
        st.error(status.get('message', 'Unknown error loading market data'))
    
    st.markdown("---")
    st.markdown("**Status:** `{}`".format(status['status']))


def _render_market_footer(status: dict, summary: dict):
    """Footer section (metadata display removed)."""
    # Footer metadata display has been removed.
    # Data range and built timestamp are no longer shown in the UI.
    pass


