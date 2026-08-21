"""
Price History Data Access Layer.

Reads historical GUN/USD token price data from data_opensea_sales/price_history/.
Provides utilities to fetch token prices for specific dates and perform date-based lookups.

Read-only access, no modifications to source data.
"""

from pathlib import Path
from typing import Optional, Dict
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from config import get_data_dir


def _get_price_history_dir() -> Path:
    """Returns the path to the price_history directory."""
    data_dir = get_data_dir()
    return data_dir / "price_history"


def _get_gun_usd_price_history_path() -> Path:
    """Returns the path to gun_usd_price_history.csv."""
    return _get_price_history_dir() / "gun_usd_price_history.csv"


@st.cache_data(ttl=3600)
def load_gun_price_history() -> Optional[pd.DataFrame]:
    """
    Load GUN/USD historical price history from gun_usd_price_history.csv.
    
    Returns:
        DataFrame with columns: date, price_timestamp, price_usd, source, ...
        date is converted to datetime
        Returns None if file not found
    """
    price_history_path = _get_gun_usd_price_history_path()
    
    if not price_history_path.exists():
        return None
    
    try:
        df = pd.read_csv(price_history_path)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        print(f"Error loading gun price history: {e}")
        return None


def get_token_price_for_date(date: pd.Timestamp) -> Optional[float]:
    """
    Get GUN/USD token price for a specific date.
    
    Args:
        date: datetime or date to look up (will match against daily price)
    
    Returns:
        float price_usd or None if not found
    """
    df = load_gun_price_history()
    if df is None or df.empty:
        return None
    
    # Convert date to date only (ignore time)
    if isinstance(date, pd.Timestamp):
        lookup_date = date.date()
    else:
        lookup_date = date
    
    # Find matching row
    mask = df['date'].dt.date == lookup_date
    if mask.any():
        return df[mask].iloc[0]['price_usd']
    
    return None


def get_price_history_date_range() -> tuple:
    """
    Get the date range (min and max dates) from gun_usd_price_history.csv.
    
    This is used as the default date range for ITEM mode charts to provide a unified
    visual scale across all items based on available token price data.
    
    Returns:
        tuple: (start_date, end_date) as datetime.date objects
        If price history is unavailable or empty, returns (None, None)
    """
    df = load_gun_price_history()
    if df is None or df.empty:
        return (None, None)
    
    try:
        min_date = df['date'].min().date()
        max_date = df['date'].max().date()
        return (min_date, max_date)
    except Exception as e:
        print(f"Error getting price history date range: {e}")
        return (None, None)


def enrich_daily_metrics_with_token_price(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich daily_market_metrics with token price for each day.
    
    Args:
        daily_df: DataFrame from load_daily_market_metrics() with 'date' column
    
    Returns:
        DataFrame with new column 'token_price_usd' added (or NaN if not found)
    """
    if daily_df is None or daily_df.empty:
        return daily_df
    
    df = daily_df.copy()
    price_history = load_gun_price_history()
    
    if price_history is None or price_history.empty:
        df['token_price_usd'] = None
        return df
    
    # Merge on date
    # Ensure both dates are datetime for comparison
    daily_dates = pd.to_datetime(df['date']).dt.date
    price_dates = price_history['date'].dt.date
    
    # Create a mapping of date -> price
    price_map = dict(zip(price_dates, price_history['price_usd']))
    
    df['token_price_usd'] = daily_dates.map(price_map)
    return df


def enrich_monthly_metrics_with_average_token_price(monthly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich monthly_market_metrics with average token price for each month.
    
    For each month, calculates the average daily GUN/USD price across all days in that month.
    
    Args:
        monthly_df: DataFrame from load_monthly_market_metrics() with 'month_start' column
    
    Returns:
        DataFrame with new column 'token_price_usd_avg' added (or NaN if not found)
    """
    if monthly_df is None or monthly_df.empty:
        return monthly_df
    
    df = monthly_df.copy()
    price_history = load_gun_price_history()
    
    if price_history is None or price_history.empty:
        df['token_price_usd_avg'] = None
        return df
    
    # For each month_start in monthly_df, find all daily prices for that month
    # and calculate the average
    token_prices = []
    
    for _, row in df.iterrows():
        month_start = pd.to_datetime(row['month_start'])
        month_end = pd.to_datetime(row['month_end'])
        
        # Find all prices in this month range
        mask = (price_history['date'] >= month_start) & (price_history['date'] <= month_end)
        month_prices = price_history[mask]['price_usd']
        
        if len(month_prices) > 0:
            avg_price = month_prices.mean()
        else:
            avg_price = None
        
        token_prices.append(avg_price)
    
    df['token_price_usd_avg'] = token_prices
    return df
