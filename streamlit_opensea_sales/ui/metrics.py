"""
technical diagnostic text technical diagnostic text (technical diagnostic text technical diagnostic text, technical diagnostic text technical diagnostic text technical diagnostic text.technical diagnostic text.).

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text USD technical diagnostic text.
"""

import streamlit as st
import pandas as pd
import numpy as np

from formatters import format_metric_value, format_historical_metric_pair


def render_metrics(combined_df: pd.DataFrame, show_usd: bool, current_gun_price: float):
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text USD.
    
    technical diagnostic text technical diagnostic text technical diagnostic text USD technical diagnostic text (price_usd_at_sale), technical diagnostic text technical diagnostic text.
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text GUN technical diagnostic text technical diagnostic text.
    
    Args:
        combined_df: technical diagnostic text DataFrame
        show_usd: technical diagnostic text technical diagnostic text technical diagnostic text USD
        current_gun_price: technical diagnostic text technical diagnostic text GUN technical diagnostic text USD
    """
    # technical implementation note technical implementation note technical implementation note USD technical implementation note
    has_historical_usd = 'price_usd_at_sale' in combined_df.columns
    
    # technical implementation note technical implementation note
    avg_price_gun = combined_df['price_gun'].mean()
    total_volume_gun = combined_df['price_gun'].sum()
    min_price_gun = combined_df['price_gun'].min()
    max_price_gun = combined_df['price_gun'].max()
    
    if has_historical_usd:
        # technical implementation note technical implementation note USD (technical implementation note NaN)
        price_usd_values = combined_df['price_usd_at_sale'].dropna()
        if len(price_usd_values) > 0:
            avg_price_usd = price_usd_values.mean()
            total_volume_usd = combined_df['price_usd_at_sale'].sum()
            min_price_usd = price_usd_values.min()
            max_price_usd = price_usd_values.max()
        else:
            # Fallback technical implementation note technical implementation note technical implementation note NaN
            avg_price_usd = avg_price_gun * current_gun_price
            total_volume_usd = total_volume_gun * current_gun_price
            min_price_usd = min_price_gun * current_gun_price
            max_price_usd = max_price_gun * current_gun_price
            has_historical_usd = False
    else:
        # technical implementation note technical implementation note technical implementation note technical implementation note
        avg_price_usd = avg_price_gun * current_gun_price
        total_volume_usd = total_volume_gun * current_gun_price
        min_price_usd = min_price_gun * current_gun_price
        max_price_usd = max_price_gun * current_gun_price
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Average Price
        if has_historical_usd:
            avg_formatted = format_historical_metric_pair(
                avg_price_gun, avg_price_usd, show_usd, currency='GUN',
                usd_label='USD', gun_label='GUN'
            )
        else:
            avg_formatted = format_metric_value(avg_price_gun, show_usd, current_gun_price, currency='GUN')
        
        st.markdown(f"<div class='metric-container'><div class='metric-label'>Average Price</div>{avg_formatted}</div>", unsafe_allow_html=True)
        
        # Total Volume
        if has_historical_usd:
            vol_formatted = format_historical_metric_pair(
                total_volume_gun, total_volume_usd, show_usd, currency='GUN',
                usd_label='USD', gun_label='GUN'
            )
        else:
            vol_formatted = format_metric_value(total_volume_gun, show_usd, current_gun_price, currency='GUN')
        
        st.markdown(f"<div class='metric-container'><div class='metric-label'>Total Volume</div>{vol_formatted}</div>", unsafe_allow_html=True)
    
    with col2:
        # Minimum Price
        if has_historical_usd:
            min_formatted = format_historical_metric_pair(
                min_price_gun, min_price_usd, show_usd, currency='GUN',
                usd_label='USD', gun_label='GUN'
            )
        else:
            min_formatted = format_metric_value(min_price_gun, show_usd, current_gun_price, currency='GUN')
        
        st.markdown(f"<div class='metric-container'><div class='metric-label'>Minimum Price</div>{min_formatted}</div>", unsafe_allow_html=True)
        
        # Maximum Price
        if has_historical_usd:
            max_formatted = format_historical_metric_pair(
                max_price_gun, max_price_usd, show_usd, currency='GUN',
                usd_label='USD', gun_label='GUN'
            )
        else:
            max_formatted = format_metric_value(max_price_gun, show_usd, current_gun_price, currency='GUN')
        
        st.markdown(f"<div class='metric-container'><div class='metric-label'>Maximum Price</div>{max_formatted}</div>", unsafe_allow_html=True)
    
    with col3:
        unique_sellers = combined_df['seller'].nunique()
        unique_buyers = combined_df['buyer'].nunique()
        st.markdown(f"<div class='metric-container'><div class='metric-label'>Unique Sellers</div>{unique_sellers}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-container'><div class='metric-label'>Unique Buyers</div>{unique_buyers}</div>", unsafe_allow_html=True)
    
    with col4:
        total_transactions = len(combined_df)
        unique_wallets = len(set(combined_df['seller'].unique()) | set(combined_df['buyer'].unique()))
        st.markdown(f"<div class='metric-container'><div class='metric-label'>Total Transactions</div>{total_transactions}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-container'><div class='metric-label'>Total Unique Wallets</div>{unique_wallets}</div>", unsafe_allow_html=True)
