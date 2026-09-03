"""
Market Analytics Charts.

Plotly graphtechnical diagnostic text technical diagnostic text Market Overview technical diagnostic text.
- Daily Liquidity (line chart)
- Daily Volume (line chart)
- Monthly Liquidity (bar chart)
- Monthly Volume (bar chart)

technical diagnostic text: OTG technical diagnostic text/technical diagnostic text technical diagnostic text, technical diagnostic text technical diagnostic text, readable Plotly hover.
"""

import plotly.graph_objects as go
import pandas as pd
from typing import Optional
from formatters import format_number
from price_history_access import enrich_daily_metrics_with_token_price, enrich_monthly_metrics_with_average_token_price

# OTG Color scheme
COLOR_BACKGROUND = '#000000'  # Pure black
COLOR_TEXT = '#e0e0e0'
COLOR_ACCENT_RED = '#FF003A'  # OTG brand red
COLOR_GRID = '#1a1a1a'
COLOR_LINE = '#FF003A'  # OTG brand red for line charts
COLOR_MARKER = '#CC0030'  # Darker red for markers/dots


def build_daily_liquidity_chart(daily_df: pd.DataFrame, mobile_layout: bool = False, unique_wallets_df: Optional[pd.DataFrame] = None, show_unique_wallets: bool = False) -> Optional[go.Figure]:
    """
    technical diagnostic text Daily Liquidity line chart.
    
    Liquidity = number of completed item-sale events
    Shows: transactions_count per day
    
    Args:
        daily_df: DataFrame technical diagnostic text load_daily_market_metrics()
    
    Returns:
        Plotly Figure technical diagnostic text None technical diagnostic text technical diagnostic text
    """
    if daily_df is None or len(daily_df) == 0:
        return None
    
    try:
        df = daily_df.copy()
        df['liquidity'] = pd.to_numeric(
            df['transactions_count'],
            errors='coerce',
        ).fillna(0)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['liquidity'],
            mode='lines+markers',
            name='Daily Liquidity',
            line=dict(color=COLOR_LINE, width=2),
            marker=dict(size=4, color=COLOR_MARKER),
            hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Liquidity: %{y:,.0f} transactions<extra></extra>',
            fill='tozeroy',
            fillcolor='rgba(255, 0, 58, 0.15)'
        ))

        if show_unique_wallets and unique_wallets_df is not None and not unique_wallets_df.empty:
            wallet_df = unique_wallets_df.copy()
            fig.add_trace(go.Scatter(
                x=wallet_df['date'], y=pd.to_numeric(wallet_df['unique_wallets'], errors='coerce'),
                mode='lines+markers', name='Unique Wallets', yaxis='y2',
                line=dict(color='#FFD400', width=2.5), marker=dict(size=4, color='#FFD400'),
                hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Unique Wallets: %{y:,.0f}<extra></extra>',
            ))
        
        xaxis_config = dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=COLOR_GRID,
            tickfont=dict(color='#FFFFFF'),
            showline=False,
        )
        if show_unique_wallets and unique_wallets_df is not None and not unique_wallets_df.empty:
            date_values = pd.to_datetime(df['date'], errors='coerce').dropna()
            if len(date_values) > 1:
                xaxis_config['range'] = [date_values.min(), date_values.max()]
        yaxis_config = dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=COLOR_GRID,
            tickfont=dict(color='#FFFFFF'),
            showline=False,
            zeroline=False,
        )
        yaxis2_config = None
        if show_unique_wallets and unique_wallets_df is not None and not unique_wallets_df.empty:
            yaxis2_config = dict(overlaying='y', side='right', showgrid=False, showline=False, ticks='',
                                 tickfont=dict(color='#FFD400', size=10), zeroline=False,
                                 showticklabels=not mobile_layout)
        if mobile_layout:
            xaxis_config['domain'] = [0.0, 1.0]
            yaxis_config.update(
                title=dict(text=''),
                showticklabels=False,
                ticks='',
                showline=False,
                automargin=False
            )

        fig.update_layout(
            title=dict(text='Daily Market Liquidity', font=dict(color='#FFFFFF')),
            xaxis_title=None,
            yaxis_title=None,
            hovermode='x unified',
            template='plotly_dark',
            plot_bgcolor=COLOR_BACKGROUND,
            paper_bgcolor=COLOR_BACKGROUND,
            font=dict(color=COLOR_TEXT, family='monospace'),
            xaxis=xaxis_config,
            yaxis=yaxis_config,
            margin=dict(l=4, r=4, t=36, b=40) if mobile_layout else dict(l=50, r=50, t=80, b=50),
            height=280 if mobile_layout else 400,
            showlegend=False,
            yaxis2=yaxis2_config
        )
        fig.update_xaxes(title=None, showline=False)
        fig.update_yaxes(title=None, showline=False)
        
        return fig
    except Exception as e:
        print(f"Error building daily liquidity chart: {e}")
        return None


def build_daily_volume_chart(daily_df: pd.DataFrame, show_usd: bool = False, current_gun_price: float = 0.03, show_token_price: bool = False, mobile_layout: bool = False) -> Optional[go.Figure]:
    """
    technical diagnostic text Daily Volume line chart.
    
    Volume = total GUN traded per day (or USD equivalent if show_usd=True)
    Shows: volume_gun per day, or volume_usd if enriched data available
    
    Args:
        daily_df: DataFrame technical diagnostic text load_daily_market_metrics()
        show_usd: If True, display volume in USD; if False, display in GUN
        current_gun_price: Price of GUN in USD (used only if volume_usd not available)
    
    Returns:
        Plotly Figure technical diagnostic text None technical diagnostic text technical diagnostic text
    """
    if daily_df is None or len(daily_df) == 0:
        return None
    
    try:
        df = daily_df.copy()
        
        # Enrich with token prices for tooltip
        df = enrich_daily_metrics_with_token_price(df)
        
        # Check if enriched USD data is available
        has_usd_data = 'volume_usd' in df.columns
        
        # Calculate Y values and secondary values for hover
        if show_usd:
            # Use enriched historical USD if available, otherwise calculate from current price
            if has_usd_data:
                y_values = df['volume_usd']
                secondary_values_for_hover = df['volume_gun']
                use_historical_usd = True
            else:
                y_values = df['volume_gun'] * current_gun_price
                secondary_values_for_hover = df['volume_gun']
                use_historical_usd = False
            
            y_axis_title = 'Volume (USD)' if has_usd_data else 'Volume (USD)'
            chart_title = 'Daily Market Volume'
            main_currency = 'USD'
            secondary_currency = 'GUN'
        else:
            y_values = df['volume_gun']
            if has_usd_data:
                secondary_values_for_hover = df['volume_usd']
                use_historical_usd = True
            else:
                secondary_values_for_hover = df['volume_gun'] * current_gun_price
                use_historical_usd = False
            
            y_axis_title = 'Volume (GUN)'
            chart_title = 'Daily Market Volume'
            main_currency = 'GUN'
            secondary_currency = 'USD'
        
        # Create formatted values for hover display using actual y_values and secondary_values
        main_values = [format_number(v, show_usd, 1.0 if (show_usd and use_historical_usd) else current_gun_price, currency='GUN' if main_currency == 'GUN' else 'USD') 
                      for v in y_values]
        secondary_values = [format_number(v, not show_usd, 1.0 if (not show_usd and use_historical_usd) else current_gun_price, currency='GUN' if secondary_currency == 'GUN' else 'USD')
                           for v in secondary_values_for_hover]
        
        # Format token prices for hover
        token_prices = []
        for token_price in df['token_price_usd']:
            if pd.isna(token_price):
                token_prices.append('unavailable')
            else:
                token_prices.append(f'${token_price:.6f}')
        
        fig = go.Figure()
        
        # Create hover template showing both currencies and token price (skip token price if overlay is shown)
        if show_token_price:
            hover_template = '<b>%{x|%Y-%m-%d}</b><br>' + \
                            f'{main_currency}: %{{customdata[0]}}<br>' + \
                            f'{secondary_currency}: %{{customdata[1]}}<extra></extra>'
        else:
            hover_template = '<b>%{x|%Y-%m-%d}</b><br>' + \
                            f'{main_currency}: %{{customdata[0]}}<br>' + \
                            f'{secondary_currency}: %{{customdata[1]}}<br>' + \
                            f'GUN/USD: %{{customdata[2]}}<extra></extra>'
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=y_values,
            mode='lines+markers',
            name=f'Daily Volume ({main_currency})',
            line=dict(color=COLOR_LINE, width=2),
            marker=dict(size=4, color=COLOR_MARKER),
            customdata=list(zip(main_values, secondary_values, token_prices)),
            hovertemplate=hover_template,
            fill='tozeroy',
            fillcolor='rgba(255, 0, 58, 0.15)'
        ))
        
        # Add token price overlay if enabled
        yaxis2_config = None
        if show_token_price:
            # Prepare token price data for overlay (skip NaN to show gaps)
            token_price_plot = df.copy()
            
            # Create hover template for token price trace
            token_hover = '<b>%{x|%Y-%m-%d}</b><br>GUN/USD: %{y:.6f}<extra></extra>'
            
            fig.add_trace(go.Scatter(
                x=token_price_plot['date'],
                y=token_price_plot['token_price_usd'],
                mode='lines',
                name='GUN/USD',
                line=dict(color='#AFFF01', width=2.5),
                hovertemplate=token_hover,
                yaxis='y2'
            ))
            
            # Configure secondary Y-axis for token price
            if mobile_layout:
                yaxis2_config = dict(
                    overlaying='y',
                    side='right',
                    showgrid=False,
                    showticklabels=False,
                    ticks='',
                    zeroline=False,
                    showline=False,
                    automargin=False
                )
            else:
                yaxis2_config = dict(
                    overlaying='y',
                    side='right',
                    showgrid=False,
                    ticks='',
                    tickfont=dict(color='#AFFF01', size=10),
                    zeroline=False,
                    showline=False
                )

        xaxis_config = dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=COLOR_GRID,
            tickfont=dict(color='#FFFFFF'),
            showline=False,
        )
        yaxis_config = dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=COLOR_GRID,
            tickfont=dict(color='#FFFFFF'),
            showline=False,
            zeroline=False,
        )
        if mobile_layout:
            xaxis_config['domain'] = [0.0, 1.0]
            yaxis_config.update(
                title=dict(text=''),
                showticklabels=False,
                ticks='',
                showline=False,
                automargin=False
            )
        
        fig.update_layout(
            title=dict(text=chart_title, font=dict(color='#FFFFFF')),
            xaxis_title=None,
            yaxis_title=None,
            hovermode='x unified',
            template='plotly_dark',
            plot_bgcolor=COLOR_BACKGROUND,
            paper_bgcolor=COLOR_BACKGROUND,
            font=dict(color=COLOR_TEXT, family='monospace'),
            xaxis=xaxis_config,
            yaxis=yaxis_config,
            yaxis2=yaxis2_config,
            margin=dict(l=4, r=4, t=36, b=40) if mobile_layout else dict(l=50, r=70 if show_token_price else 50, t=90, b=50),
            height=280 if mobile_layout else 400,
            showlegend=False if mobile_layout else show_token_price,
            legend=dict(
                orientation="h",
                x=0,
                xanchor="left",
                y=1.02,
                yanchor="bottom",
                font=dict(family='monospace', size=10, color='white')
            )
        )
        fig.update_xaxes(title=None, showline=False)
        fig.update_yaxes(title=None)
        fig.layout.yaxis.showline = False
        
        return fig
    except Exception as e:
        print(f"Error building daily volume chart: {e}")
        return None


def build_monthly_liquidity_chart(monthly_df: pd.DataFrame, mobile_layout: bool = False, unique_wallets_df: Optional[pd.DataFrame] = None, show_unique_wallets: bool = False) -> Optional[go.Figure]:
    """
    technical diagnostic text Monthly Liquidity bar chart.
    
    Liquidity = number of completed item-sale events
    Shows: transactions_count per month
    
    Args:
        monthly_df: DataFrame technical diagnostic text load_monthly_market_metrics()
    
    Returns:
        Plotly Figure technical diagnostic text None technical diagnostic text technical diagnostic text
    """
    if monthly_df is None or len(monthly_df) == 0:
        return None
    
    try:
        df = monthly_df.copy()
        df['liquidity'] = pd.to_numeric(
            df['transactions_count'],
            errors='coerce',
        ).fillna(0)
        df['month_label'] = df['month']
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df['month_label'],
            y=df['liquidity'],
            name='Monthly Liquidity',
            marker=dict(color=COLOR_LINE),
            hovertemplate='<b>%{x}</b><br>Liquidity: %{y:,.0f} transactions<extra></extra>',
            offsetgroup='liquidity',
            yaxis='y',
        ))

        if show_unique_wallets and unique_wallets_df is not None and not unique_wallets_df.empty:
            wallet_df = unique_wallets_df.copy()
            fig.add_trace(go.Bar(
                x=wallet_df['month'], y=pd.to_numeric(wallet_df['unique_wallets'], errors='coerce'),
                name='Unique Wallets', yaxis='y2',
                marker=dict(color='#FFD400', line=dict(color='#8A7300', width=1.2)),
                hovertemplate='<b>%{x}</b><br>Unique Wallets: %{y:,.0f}<extra></extra>',
                offsetgroup='unique_wallets',
            ))
        
        xaxis_config = dict(
            showgrid=False,
            tickfont=dict(color='#FFFFFF'),
            showline=False,
        )
        yaxis_config = dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=COLOR_GRID,
            tickfont=dict(color='#FFFFFF'),
            showline=False,
            zeroline=False,
        )
        yaxis2_config = None
        if show_unique_wallets and unique_wallets_df is not None and not unique_wallets_df.empty:
            yaxis2_config = dict(overlaying='y', side='right', showgrid=False, showline=False, ticks='',
                                 tickfont=dict(color='#FFD400', size=10), zeroline=False,
                                 showticklabels=not mobile_layout)
        if mobile_layout:
            xaxis_config['domain'] = [0.0, 1.0]
            yaxis_config.update(
                title=dict(text=''),
                showticklabels=False,
                ticks='',
                showline=False,
                automargin=False
            )

        fig.update_layout(
            title=dict(text='Monthly Market Liquidity', font=dict(color='#FFFFFF')),
            xaxis_title=None,
            yaxis_title=None,
            hovermode='x unified',
            template='plotly_dark',
            plot_bgcolor=COLOR_BACKGROUND,
            paper_bgcolor=COLOR_BACKGROUND,
            font=dict(color=COLOR_TEXT, family='monospace'),
            xaxis=xaxis_config,
            yaxis=yaxis_config,
            barmode='group' if show_unique_wallets and unique_wallets_df is not None and not unique_wallets_df.empty else 'overlay',
            bargap=0.25,
            bargroupgap=0.05,
            margin=dict(l=4, r=4, t=36, b=40) if mobile_layout else dict(l=50, r=70 if show_unique_wallets and unique_wallets_df is not None and not unique_wallets_df.empty else 50, t=80, b=50),
            height=240 if mobile_layout else 400,
            showlegend=False,
            yaxis2=yaxis2_config
        )
        fig.update_xaxes(title=None, showline=False)
        fig.update_yaxes(title=None, showline=False)
        
        return fig
    except Exception as e:
        print(f"Error building monthly liquidity chart: {e}")
        return None


def build_monthly_volume_chart(monthly_df: pd.DataFrame, show_usd: bool = False, current_gun_price: float = 0.03, show_token_price: bool = False, mobile_layout: bool = False) -> Optional[go.Figure]:
    """
    technical diagnostic text Monthly Volume bar chart.
    
    Volume = total GUN traded per month (or USD equivalent if show_usd=True)
    Shows: volume_gun per month, or volume_usd if enriched data available
    
    Args:
        monthly_df: DataFrame technical diagnostic text load_monthly_market_metrics()
        show_usd: If True, display volume in USD; if False, display in GUN
        current_gun_price: Price of GUN in USD (used only if volume_usd not available)
    
    Returns:
        Plotly Figure technical diagnostic text None technical diagnostic text technical diagnostic text
    """
    if monthly_df is None or len(monthly_df) == 0:
        return None
    
    try:
        df = monthly_df.copy()
        df['month_label'] = df['month']
        
        # Enrich with token prices for tooltip
        df = enrich_monthly_metrics_with_average_token_price(df)
        
        # Check if enriched USD data is available
        has_usd_data = 'volume_usd' in df.columns
        
        # Calculate Y values and secondary values for hover
        if show_usd:
            # Use enriched historical USD if available, otherwise calculate from current price
            if has_usd_data:
                y_values = df['volume_usd']
                secondary_values_for_hover = df['volume_gun']
                use_historical_usd = True
            else:
                y_values = df['volume_gun'] * current_gun_price
                secondary_values_for_hover = df['volume_gun']
                use_historical_usd = False
            
            y_axis_title = 'Volume (USD)' if has_usd_data else 'Volume (USD)'
            chart_title = 'Monthly Market Volume'
            main_currency = 'USD'
            secondary_currency = 'GUN'
        else:
            y_values = df['volume_gun']
            if has_usd_data:
                secondary_values_for_hover = df['volume_usd']
                use_historical_usd = True
            else:
                secondary_values_for_hover = df['volume_gun'] * current_gun_price
                use_historical_usd = False
            
            y_axis_title = 'Volume (GUN)'
            chart_title = 'Monthly Market Volume'
            main_currency = 'GUN'
            secondary_currency = 'USD'
        
        # Create formatted values for hover display using actual y_values and secondary_values
        main_values = [format_number(v, show_usd, 1.0 if (show_usd and use_historical_usd) else current_gun_price, currency='GUN' if main_currency == 'GUN' else 'USD')
                      for v in y_values]
        secondary_values = [format_number(v, not show_usd, 1.0 if (not show_usd and use_historical_usd) else current_gun_price, currency='GUN' if secondary_currency == 'GUN' else 'USD')
                           for v in secondary_values_for_hover]
        
        # Format token prices for hover
        token_prices = []
        for token_price in df['token_price_usd_avg']:
            if pd.isna(token_price):
                token_prices.append('unavailable')
            else:
                token_prices.append(f'${token_price:.6f}')
        
        fig = go.Figure()
        
        # Create hover template showing both currencies and token price (skip token price if overlay is shown)
        if show_token_price:
            hover_template = '<b>%{x}</b><br>' + \
                            f'{main_currency}: %{{customdata[0]}}<br>' + \
                            f'{secondary_currency}: %{{customdata[1]}}<extra></extra>'
        else:
            hover_template = '<b>%{x}</b><br>' + \
                            f'{main_currency}: %{{customdata[0]}}<br>' + \
                            f'{secondary_currency}: %{{customdata[1]}}<br>' + \
                            f'GUN/USD (avg): %{{customdata[2]}}<extra></extra>'
        
        fig.add_trace(go.Bar(
            x=df['month_label'],
            y=y_values,
            name=f'Monthly Volume ({main_currency})',
            marker=dict(color=COLOR_LINE),
            customdata=list(zip(main_values, secondary_values, token_prices)),
            hovertemplate=hover_template,
            offsetgroup='volume',
            yaxis='y'
        ))
        
        # Add token price overlay if enabled
        yaxis2_config = None
        if show_token_price:
            # Prepare token price data for overlay (skip NaN to show gaps)
            token_price_plot = df.copy()
            
            # Create hover template for token price trace
            token_hover = '<b>%{x}</b><br>GUN/USD (avg): %{y:.6f}<extra></extra>'
            
            fig.add_trace(go.Bar(
                x=token_price_plot['month_label'],
                y=token_price_plot['token_price_usd_avg'],
                name='GUN/USD Avg',
                marker=dict(color='#AFFF01', line=dict(color='#2d5016', width=1.5)),
                hovertemplate=token_hover,
                offsetgroup='token_price',
                yaxis='y2'
            ))
            
            # Configure secondary Y-axis for token price
            if mobile_layout:
                yaxis2_config = dict(
                    overlaying='y',
                    side='right',
                    showgrid=False,
                    showticklabels=False,
                    ticks='',
                    zeroline=False,
                    showline=False,
                    automargin=False
                )
            else:
                yaxis2_config = dict(
                    overlaying='y',
                    side='right',
                    showgrid=False,
                    ticks='',
                    tickfont=dict(color='#AFFF01', size=10),
                    zeroline=False,
                    showline=False
                )

        xaxis_config = dict(
            showgrid=False,
            tickfont=dict(color='#FFFFFF'),
            showline=False,
        )
        yaxis_config = dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=COLOR_GRID,
            tickfont=dict(color='#FFFFFF'),
            showline=False,
            zeroline=False,
        )
        if mobile_layout:
            xaxis_config['domain'] = [0.0, 1.0]
            yaxis_config.update(
                title=dict(text=''),
                showticklabels=False,
                ticks='',
                showline=False,
                automargin=False
            )
        
        fig.update_layout(
            title=dict(text=chart_title, font=dict(color='#FFFFFF')),
            xaxis_title=None,
            yaxis_title=None,
            hovermode='x unified',
            template='plotly_dark',
            plot_bgcolor=COLOR_BACKGROUND,
            paper_bgcolor=COLOR_BACKGROUND,
            font=dict(color=COLOR_TEXT, family='monospace'),
            barmode='group' if show_token_price else 'overlay',
            bargap=0.25,
            bargroupgap=0.05,
            xaxis=xaxis_config,
            yaxis=yaxis_config,
            yaxis2=yaxis2_config,
            margin=dict(l=4, r=4, t=36, b=40) if mobile_layout else dict(l=50, r=70 if show_token_price else 50, t=90, b=50),
            height=260 if mobile_layout else 400,
            showlegend=False if mobile_layout else show_token_price,
            legend=dict(
                orientation="h",
                x=0,
                xanchor="left",
                y=1.02,
                yanchor="bottom",
                font=dict(family='monospace', size=10, color='white')
            )
        )
        fig.update_xaxes(title=None, showline=False)
        fig.update_yaxes(title=None)
        fig.layout.yaxis.showline = False
        
        return fig
    except Exception as e:
        print(f"Error building monthly volume chart: {e}")
        return None


def build_token_split_chart(token_split: dict) -> Optional[go.Figure]:
    """
    technical diagnostic text Token Split pie chart (GUN vs WGUN).
    
    Args:
        token_split: dict technical diagnostic text get_market_token_split()
    
    Returns:
        Plotly Figure technical diagnostic text None technical diagnostic text technical diagnostic text
    """
    if token_split is None or len(token_split) == 0:
        return None
    
    try:
        labels = []
        values = []
        
        for token, data in token_split.items():
            labels.append(token)
            values.append(data.get('percent_of_volume', 0))
        
        fig = go.Figure()
        
        fig.add_trace(go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=[COLOR_LINE, '#FF6B77']),
            hovertemplate='<b>%{label}</b><br>%{value:.1f}%<extra></extra>',
        ))
        
        fig.update_layout(
            title='Token Split (by Volume)',
            template='plotly_dark',
            plot_bgcolor=COLOR_BACKGROUND,
            paper_bgcolor=COLOR_BACKGROUND,
            font=dict(color=COLOR_TEXT, family='monospace'),
            margin=dict(l=50, r=50, t=80, b=50),
            height=350,
            showlegend=False
        )
        
        return fig
    except Exception as e:
        print(f"Error building token split chart: {e}")
        return None
