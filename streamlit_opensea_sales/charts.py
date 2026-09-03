"""
technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.

technical diagnostic text Plotly technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
"""

from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go

from config import FONT_FAMILY
from theme import OTG_THEME
from formatters import format_number

BUY_COLOR = '#A477C7'
SELL_COLOR = '#67C77A'
OTHER_GUN_COLOR = '#6B6B73'
OTHER_WGUN_COLOR = '#85858E'
SELF_TRADE_COLOR = '#7E7487'
BUY_OUTLINE_COLOR = '#5D397A'
SELL_OUTLINE_COLOR = '#356B44'
OTHER_GUN_OUTLINE_COLOR = '#3F3F46'
OTHER_WGUN_OUTLINE_COLOR = '#55555D'
SELF_TRADE_OUTLINE_COLOR = '#453D59'


def classify_wallet_role(row: pd.Series, highlight_wallet: str = None) -> str:
    if not highlight_wallet:
        return 'OTHER'
    buyer = '' if pd.isna(row.get('buyer')) else str(row.get('buyer')).strip()
    seller = '' if pd.isna(row.get('seller')) else str(row.get('seller')).strip()
    if buyer == highlight_wallet and seller == highlight_wallet:
        return 'SELF_TRADE'
    if buyer == highlight_wallet:
        return 'BUY'
    if seller == highlight_wallet:
        return 'SELL'
    return 'OTHER'


def wallet_point_colors(df: pd.DataFrame, token_type: str, highlight_wallet: str = None) -> list:
    if not highlight_wallet:
        return OTG_THEME.accent if token_type == 'GUN' else '#FFD700'
    other = OTHER_GUN_COLOR if token_type == 'GUN' else OTHER_WGUN_COLOR
    return [
        {'BUY': BUY_COLOR, 'SELL': SELL_COLOR, 'SELF_TRADE': SELF_TRADE_COLOR}.get(
            classify_wallet_role(row, highlight_wallet), other
        ) for _, row in df.iterrows()
    ]


def wallet_point_outline_colors(df: pd.DataFrame, token_type: str, highlight_wallet: str = None) -> list:
    if not highlight_wallet:
        return '#8B0000' if token_type == 'GUN' else '#B8860B'
    other = OTHER_GUN_OUTLINE_COLOR if token_type == 'GUN' else OTHER_WGUN_OUTLINE_COLOR
    return [
        {'BUY': BUY_OUTLINE_COLOR, 'SELL': SELL_OUTLINE_COLOR,
         'SELF_TRADE': SELF_TRADE_OUTLINE_COLOR}.get(
            classify_wallet_role(row, highlight_wallet), other
        ) for _, row in df.iterrows()
    ]


def build_sales_chart(
    filtered_df: pd.DataFrame,
    show_volume: bool,
    show_usd: bool,
    current_gun_price: float,
    show_trend_line: bool = False,
    trend_df: pd.DataFrame = None,
    mobile_layout: bool = False,
    compact_vertical_margins: bool = False
    , highlight_wallet: str = None
) -> go.Figure:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    technical diagnostic text technical diagnostic text technical diagnostic text: GUN (technical diagnostic text) technical diagnostic text WGUN (technical diagnostic text) technical diagnostic text technical diagnostic text
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    technical diagnostic text technical diagnostic text USD technical diagnostic text:
    - technical diagnostic text technical diagnostic text price_usd_at_sale technical diagnostic text gun_usd_price_at_sale, technical diagnostic text
    - technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text current_gun_price technical diagnostic text technical diagnostic text
    
    Args:
        filtered_df: technical diagnostic text technical diagnostic text technical diagnostic text
        show_volume: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
        show_usd: technical diagnostic text technical diagnostic text technical diagnostic text USD
        current_gun_price: technical diagnostic text technical diagnostic text GUN technical diagnostic text USD
        show_trend_line: technical diagnostic text technical diagnostic text technical diagnostic text Trend Line
        trend_df: technical diagnostic text backend linear regression endpoints technical diagnostic text item_trends/<item>.csv
    
    Returns:
        go.Figure: Plotly Figure technical diagnostic text technical diagnostic text technical diagnostic text
    """
    # technical implementation note technical implementation note technical implementation note technical implementation note
    sales_df = filtered_df[filtered_df['type'] == 'GUN']
    offers_df = filtered_df[filtered_df['type'] == 'WGUN']
    combined_df = filtered_df.copy()
    
    fig = go.Figure()

    # technical implementation note technical implementation note technical implementation note USD technical implementation note
    has_historical_usd_columns = (
        'price_usd_at_sale' in filtered_df.columns
        and 'gun_usd_price_at_sale' in filtered_df.columns
    )
    has_historical_usd = (
        has_historical_usd_columns
        and pd.to_numeric(filtered_df['price_usd_at_sale'], errors='coerce').notna().any()
        and pd.to_numeric(filtered_df['gun_usd_price_at_sale'], errors='coerce').notna().any()
    )
    historical_usd_unavailable = show_usd and not has_historical_usd
    primary_currency_title = "USD AT SALE" if show_usd else "GUN"

    def format_gun_amount(value):
        numeric = pd.to_numeric(pd.Series([value]), errors='coerce').iloc[0]
        if pd.isna(numeric):
            return "unavailable"
        if abs(numeric) >= 1000000:
            return f"{numeric / 1000000:.1f}M"
        if abs(numeric) >= 1000:
            return f"{numeric / 1000:.1f}K"
        if float(numeric).is_integer():
            return f"{numeric:,.0f}"
        return f"{numeric:,.2f}".rstrip('0').rstrip('.')

    def format_usd_amount(value):
        numeric = pd.to_numeric(pd.Series([value]), errors='coerce').iloc[0]
        if pd.isna(numeric):
            return "unavailable"
        if abs(numeric) >= 1000000:
            return f"${numeric / 1000000:.1f}M"
        if abs(numeric) >= 1000:
            return f"${numeric / 1000:.1f}K"
        return f"${numeric:,.2f}"

    def format_rate(value):
        numeric = pd.to_numeric(pd.Series([value]), errors='coerce').iloc[0]
        if pd.isna(numeric):
            return "unavailable"
        return f"${numeric:.8f}"

    # technical implementation note technical implementation note technical implementation note customdata technical implementation note technical implementation note technical implementation note USD
    def build_hover_customdata(df, use_historical_usd):
        """technical documentation customdata technical documentation hover technical documentation technical documentation technical documentation USD."""
        customdata_list = []
        for _, row in df.iterrows():
            date_str = row.get('formatted_date', '')
            price_gun = row.get('price_gun', 0)
            
            # technical implementation note hover text
            hover_lines = [
                f"Date: {date_str}",
                f"Price: {price_gun:.2f} {row.get('type', 'GUN')}",
            ]
            
            if use_historical_usd:
                if pd.notna(row.get('price_usd_at_sale')):
                    gun_usd = row.get('gun_usd_price_at_sale', 0)
                    price_usd = row.get('price_usd_at_sale', 0)
                    hover_lines.append(f"GUN/USD at sale: ${gun_usd:.8f}")
                    hover_lines.append(f"USD at sale: ${price_usd:.2f}")
                else:
                    hover_lines.append("USD: unavailable")
            else:
                # technical implementation note technical implementation note technical implementation note
                calc_usd = price_gun * current_gun_price
                hover_lines.append(f"USD (current estimate): ${calc_usd:.2f}")
            
            customdata_list.append("<br>".join(hover_lines))
        
        return customdata_list

    # technical implementation note technical implementation note technical implementation note Y-technical implementation note
    def build_currency_hover_customdata(df, show_usd_mode, use_historical_usd):
        customdata_list = []
        for _, row in df.iterrows():
            date_str = row.get('formatted_date', '')
            price_gun = row.get('price_gun', 0)
            token_type = row.get('type', 'GUN')
            role = classify_wallet_role(row, highlight_wallet)

            if show_usd_mode:
                if use_historical_usd and pd.notna(row.get('price_usd_at_sale')):
                    hover_lines = [
                        f"USD at sale: {format_usd_amount(row.get('price_usd_at_sale'))}",
                        f"Date: {date_str}",
                        f"Token type: {token_type}",
                        f"GUN paid: {format_gun_amount(price_gun)}",
                        f"GUN/USD at sale: {format_rate(row.get('gun_usd_price_at_sale'))}",
                    ]
                else:
                    hover_lines = [
                        "USD at sale: unavailable",
                        f"Date: {date_str}",
                        f"Token type: {token_type}",
                        f"GUN paid: {format_gun_amount(price_gun)}",
                    ]
            else:
                hover_lines = [
                    f"GUN paid: {format_gun_amount(price_gun)}",
                    f"Date: {date_str}",
                    f"Token type: {token_type}",
                ]
                if use_historical_usd and pd.notna(row.get('price_usd_at_sale')):
                    hover_lines.append(f"USD at sale: {format_usd_amount(row.get('price_usd_at_sale'))}")
                    hover_lines.append(f"GUN/USD at sale: {format_rate(row.get('gun_usd_price_at_sale'))}")
                else:
                    price_gun_numeric = pd.to_numeric(pd.Series([price_gun]), errors='coerce').iloc[0]
                    calc_usd = price_gun_numeric * current_gun_price if pd.notna(price_gun_numeric) else None
                    hover_lines.append(f"USD (current estimate): {format_usd_amount(calc_usd)}")

            if highlight_wallet and role != 'OTHER':
                hover_lines.append(f"ROLE: {role.replace('_', '-')}")

            customdata_list.append("<br>".join(hover_lines))

        return customdata_list

    def get_y_values(df, show_usd_mode, use_historical):
        """technical documentation Y-technical documentation technical documentation technical documentation technical documentation technical documentation technical documentation."""
        if not show_usd_mode:
            return df['price_gun'].values
        
        if use_historical and 'price_usd_at_sale' in df.columns:
            # technical implementation note technical implementation note USD technical implementation note technical implementation note, fallback to calculated
            return pd.to_numeric(df['price_usd_at_sale'], errors='coerce').values
        else:
            # technical implementation note technical implementation note technical implementation note technical implementation note
            return pd.Series(dtype=float).values

    # Customdata technical implementation note GUN technical implementation note
    customdata_sales = build_currency_hover_customdata(sales_df, show_usd, has_historical_usd)
    customdata_offers = build_currency_hover_customdata(offers_df, show_usd, has_historical_usd)

    # Y-technical implementation note
    y_sales = get_y_values(sales_df, show_usd, has_historical_usd)
    y_offers = get_y_values(offers_df, show_usd, has_historical_usd)

    # Hover template technical implementation note (customdata technical implementation note technical implementation note technical implementation note technical implementation note)
    hover_template_sales = "%{customdata}<extra></extra>"
    hover_template_offers = "%{customdata}<extra></extra>"

    # technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note (GUN)
    if not sales_df.empty and not historical_usd_unavailable:
        fig.add_trace(go.Scatter(
            x=sales_df['sale_date'],
            y=y_sales,
            mode='markers',
            name='GUN',
            marker=dict(size=12, color=wallet_point_colors(sales_df, 'GUN', highlight_wallet), opacity=0.9, line=dict(color=wallet_point_outline_colors(sales_df, 'GUN', highlight_wallet), width=1.5)),
            hovertemplate=hover_template_sales,
            customdata=customdata_sales,
            hoverlabel=dict(bgcolor='#080808', bordercolor='#5A5A62', font=dict(color='#FFFFFF')),
            showlegend=False
        ))

    # technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note (WGUN)
    if not offers_df.empty and not historical_usd_unavailable:
        fig.add_trace(go.Scatter(
            x=offers_df['sale_date'],
            y=y_offers,
            mode='markers',
            name='WGUN',
            marker=dict(size=12, color=wallet_point_colors(offers_df, 'WGUN', highlight_wallet), opacity=0.85, line=dict(color=wallet_point_outline_colors(offers_df, 'WGUN', highlight_wallet), width=1.5)),
            hovertemplate=hover_template_offers,
            customdata=customdata_offers,
            hoverlabel=dict(bgcolor='#080808', bordercolor='#5A5A62', font=dict(color='#FFFFFF')),
            showlegend=False
        ))

    # technical implementation note technical implementation note backend Trend Line
    if show_trend_line and trend_df is not None and not trend_df.empty:
        start_value_col = 'trend_start_price_usd' if show_usd else 'trend_start_price_gun'
        end_value_col = 'trend_end_price_usd' if show_usd else 'trend_end_price_gun'
        required_trend_cols = {'start_date', 'end_date', start_value_col, end_value_col}
        if required_trend_cols.issubset(trend_df.columns):
            trend_row = trend_df.iloc[0]
            trend_dates = pd.to_datetime(
                [trend_row.get('start_date'), trend_row.get('end_date')],
                errors='coerce'
            )
            trend_values = pd.to_numeric(
                pd.Series([trend_row.get(start_value_col), trend_row.get(end_value_col)]),
                errors='coerce'
            )

            if trend_dates.notna().all() and trend_values.notna().all():
                trend_plot_df = pd.DataFrame({
                    'trend_date': trend_dates,
                    'trend_value': trend_values,
                }).sort_values('trend_date')
            else:
                trend_plot_df = pd.DataFrame()
        else:
            trend_plot_df = pd.DataFrame()

    else:
        trend_plot_df = pd.DataFrame()

    if not trend_plot_df.empty:
        if show_usd:
            trend_hover_values = [f"USD trend: ${value:,.2f}" for value in trend_plot_df['trend_value']]
        else:
            trend_hover_values = [f"GUN trend: {format_number(value, False, 1.0, currency='GUN')}" for value in trend_plot_df['trend_value']]

        fig.add_trace(go.Scatter(
            x=trend_plot_df['trend_date'],
            y=trend_plot_df['trend_value'],
            mode='lines',
            name='Trend Line',
            line=dict(color='#AFFF01', width=2.5, dash='solid'),
            hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Trend<br>%{customdata}<extra></extra>',
            customdata=trend_hover_values,
            showlegend=False
        ))

    # technical implementation note technical implementation note technical implementation note
    show_volume_bars = show_volume and not historical_usd_unavailable
    if show_volume_bars:
        daily_volumes = combined_df.groupby(combined_df['sale_date'].dt.date).agg({
            'price_gun': ['sum', 'count']
        }).reset_index()
        daily_volumes.columns = ['date', 'volume_gun', 'count']
        
        # technical implementation note technical implementation note USD technical implementation note technical implementation note
        if has_historical_usd and 'price_usd_at_sale' in combined_df.columns:
            daily_usd = combined_df.groupby(combined_df['sale_date'].dt.date)['price_usd_at_sale'].sum().reset_index()
            daily_usd.columns = ['date', 'volume_usd']
            daily_volumes = daily_volumes.merge(daily_usd, on='date', how='left')
            daily_volumes['volume_usd'] = daily_volumes['volume_usd']
        else:
            daily_volumes['volume_usd'] = pd.NA
        
        volume_dates = [datetime.combine(date, datetime.min.time()) + timedelta(hours=12) for date in daily_volumes['date']]
        
        volume_hover_template = "<br>".join([
            "Date: %{x}",
            "Volume: %{customdata[1]}",
            "Secondary: %{customdata[2]}",
            "Transactions: %{customdata[0]}",
            "<extra></extra>"
        ])

        if show_usd:
            # USD mode: technical implementation note technical implementation note USD, technical implementation note GUN
            y_values = daily_volumes['volume_usd']
            volume_formatted = [format_number(vol, True, 1.0, currency='USD') for vol in daily_volumes['volume_usd']]
            secondary_formatted = [format_number(vol, False, 1.0, currency='GUN') for vol in daily_volumes['volume_gun']]
        else:
            # GUN mode: technical implementation note technical implementation note GUN, technical implementation note USD
            y_values = daily_volumes['volume_gun']
            volume_formatted = [format_number(vol, False, 1.0, currency='GUN') for vol in daily_volumes['volume_gun']]
            secondary_formatted = [format_number(vol, True, 1.0, currency='USD') for vol in daily_volumes['volume_usd']]
        
        fig.add_trace(go.Bar(
            x=volume_dates,
            y=y_values,
            name='Volume',
            marker_color='rgba(139,0,0,0.4)',
            yaxis='y2',
            hovertemplate=volume_hover_template,
            customdata=list(zip(daily_volumes['count'], volume_formatted, secondary_formatted))
        ))

    # technical implementation note technical implementation note
    primary_y_tick_size = 9 if mobile_layout else 12
    xaxis_title_size = 10 if mobile_layout else 14
    xaxis_tick_size = 9 if mobile_layout else 12
    chart_height = 240 if mobile_layout else 690
    chart_margin = (
        dict(l=4, r=4, t=12, b=40)
        if mobile_layout
        else dict(
            l=70,
            r=100 if show_volume else 5,
            t=18 if compact_vertical_margins else 50,
            b=42 if compact_vertical_margins else 70
        )
    )
    
    xaxis_config = dict(
        title=dict(
            text=None,
            font=dict(family=FONT_FAMILY, size=xaxis_title_size)
        ),
        showgrid=True,
        gridcolor="rgba(255,0,58,0.2)",
        gridwidth=1,
        linecolor=OTG_THEME.border,
        linewidth=2,
        tickfont=dict(family=FONT_FAMILY, size=xaxis_tick_size, color="#FFFFFF"),
        zeroline=False,
        showline=True
    )
    
    if mobile_layout:
        xaxis_config["domain"] = [0.0, 1.0]
    
    yaxis_config = dict(
        title=dict(
            text=None,
            font=dict(family=FONT_FAMILY, size=12)
        ),
        showgrid=True,
        gridcolor="rgba(255,0,58,0.2)",
        gridwidth=1,
        linecolor=OTG_THEME.border,
        linewidth=2,
        tickfont=dict(family=FONT_FAMILY, size=primary_y_tick_size, color="#FFFFFF"),
        tickprefix="$" if show_usd else None,
        tickformat="~s",
        zeroline=False,
        showline=False
    )

    if mobile_layout:
        yaxis_config.update(
            title=dict(
                text="",
                font=dict(family=FONT_FAMILY, size=14)
            ),
            automargin=False,
            showline=False,
            showticklabels=False,
            ticks=""
        )

    annotations = []
    if mobile_layout:
        annotations.append(dict(
            text=f"PRICE - {primary_currency_title}",
            xref="paper",
            yref="paper",
            x=0,
            y=1.08,
            xanchor="left",
            yanchor="bottom",
            showarrow=False,
            font=dict(family=FONT_FAMILY, size=10, color=OTG_THEME.text_secondary),
        ))
    if historical_usd_unavailable:
        annotations.append(dict(
            text="HISTORICAL USD DATA UNAVAILABLE",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            xanchor="center",
            yanchor="middle",
            showarrow=False,
            font=dict(family=FONT_FAMILY, size=12 if mobile_layout else 14, color=OTG_THEME.text_secondary),
        ))
    
    # Build yaxis2 config for volume
    yaxis2_config = dict()
    
    if show_volume_bars:
        yaxis2_config = dict(
            title=dict(
                text="Volume",
                font=dict(family=FONT_FAMILY, size=14)
            ),
            overlaying="y",
            side="right",
            showgrid=True,
            gridcolor="rgba(255,0,58,0.12)",
            gridwidth=1,
            linecolor=OTG_THEME.border,
            linewidth=2,
            tickfont=dict(family=FONT_FAMILY, size=12),
            zeroline=False,
            showline=True
        )
    
    fig.update_layout(
        hovermode='closest',
        height=chart_height,
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family=FONT_FAMILY, size=13),
        legend=dict(
            bgcolor="rgba(255,255,255,0)",
            bordercolor=OTG_THEME.border,
            borderwidth=2,
            font=dict(family=FONT_FAMILY, size=12),
            x=1.05,
            y=0.99,
            xanchor='left',
            yanchor='top'
        ),
        xaxis=xaxis_config,
        yaxis=yaxis_config,
        yaxis2=yaxis2_config,
        annotations=annotations,
        margin=chart_margin
    )

    return fig
