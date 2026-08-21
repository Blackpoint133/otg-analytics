"""
technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
"""

from typing import Dict
import streamlit as st
import pandas as pd

from config import ITEMS_PER_PAGE
from formatters import format_number, shorten_address, format_opensea_link, format_gunzscan_link


def get_current_page() -> int:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text URL technical diagnostic text.
    
    Returns:
        int: technical diagnostic text technical diagnostic text technical diagnostic text (technical diagnostic text technical diagnostic text 1)
    """
    page_param = st.query_params.get("page")
    if isinstance(page_param, list):
        page_str = page_param[0] if page_param else "1"
    else:
        page_str = page_param if page_param else "1"
    
    try:
        return int(page_str)
    except ValueError:
        return 1


def paginate_dataframe(
    df: pd.DataFrame,
    page: int,
    items_per_page: int = ITEMS_PER_PAGE
) -> Dict:
    """
    technical diagnostic text dataframe technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Args:
        df: DataFrame technical diagnostic text technical diagnostic text
        page: technical diagnostic text technical diagnostic text technical diagnostic text
        items_per_page: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    
    Returns:
        dict: technical diagnostic text technical diagnostic text page_data, page, total_pages
    """
    total_pages = len(df) // items_per_page + (1 if len(df) % items_per_page > 0 else 0)
    if total_pages == 0:
        total_pages = 1
    
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_data = df.iloc[start_idx:end_idx]
    
    return {
        'page_data': page_data,
        'page': page,
        'total_pages': total_pages
    }


def render_sales_table(
    page_data: pd.DataFrame,
    show_usd: bool,
    current_gun_price: float
):
    """
    technical diagnostic text HTML technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text USD technical diagnostic text.
    
    technical diagnostic text technical diagnostic text price_usd_at_sale technical diagnostic text gun_usd_price_at_sale, technical diagnostic text
    technical diagnostic text USD technical diagnostic text technical diagnostic text tooltip. technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    technical diagnostic text technical diagnostic text GUN technical diagnostic text technical diagnostic text.
    
    Args:
        page_data: DataFrame technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
        show_usd: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text USD
        current_gun_price: technical diagnostic text technical diagnostic text GUN
    """
    # technical implementation note technical implementation note technical implementation note USD technical implementation note
    has_historical_usd = 'price_usd_at_sale' in page_data.columns and 'gun_usd_price_at_sale' in page_data.columns
    
    # technical implementation note HTML technical implementation note
    table_html = '<table class="sales-table"><thead><tr>'
    columns = ['Date', 'Price', 'Seller', 'Buyer', 'Tx Hash', 'View']
    for col in columns:
        table_html += f'<th>{col}</th>'
    table_html += '</tr></thead><tbody>'

    for _, row in page_data.iterrows():
        table_html += '<tr>'
        table_html += f'<td>{row["formatted_date"]}</td>'
        
        # technical implementation note technical implementation note tooltip technical implementation note technical implementation note USD
        if show_usd:
            # USD technical implementation note
            if has_historical_usd and pd.notna(row.get('price_usd_at_sale')):
                # technical implementation note technical implementation note USD
                price_usd_at_sale = row['price_usd_at_sale']
                gun_usd_at_sale = row.get('gun_usd_price_at_sale', 0)
                main_value = format_number(price_usd_at_sale, True, 1.0, currency='USD')
                gun_value = format_number(row['price_gun'], False, 1.0, currency='GUN')
                tooltip_text = f"GUN/USD at sale: ${gun_usd_at_sale:.8f}<br>Price GUN: {gun_value}"
                table_html += f'<td><div class="tooltip">{main_value}<span class="tooltiptext">{tooltip_text}</span></div></td>'
            else:
                # Fallback technical implementation note technical implementation note technical implementation note
                table_html += '<td>N/A</td>'
        else:
            # GUN technical implementation note
            currency = 'WGUN' if row['type'] == 'WGUN' else 'GUN'
            gun_value = format_number(row["price_gun"], False, current_gun_price, currency=currency)
            
            if has_historical_usd and pd.notna(row.get('price_usd_at_sale')):
                # technical implementation note technical implementation note USD technical implementation note tooltip
                price_usd_at_sale = row['price_usd_at_sale']
                gun_usd_at_sale = row.get('gun_usd_price_at_sale', 0)
                tooltip_text = f"USD at sale: ${price_usd_at_sale:.2f}<br>GUN/USD: ${gun_usd_at_sale:.8f}"
                table_html += f'<td><div class="tooltip">{gun_value}<span class="tooltiptext">{tooltip_text}</span></div></td>'
            else:
                # Fallback technical implementation note technical implementation note technical implementation note
                usd_value = format_number(row["price_gun"], True, current_gun_price, currency='GUN')
                table_html += f'<td><div class="tooltip">{gun_value}<span class="tooltiptext">CURRENT ESTIMATE: {usd_value}</span></div></td>'
        
        table_html += (f'<td class="link-cell"><a href="{format_opensea_link(row["seller"])}" target="_blank">'
                    f'{shorten_address(row["seller"])}</a></td>')
        table_html += (f'<td class="link-cell"><a href="{format_opensea_link(row["buyer"])}" target="_blank">'
                    f'{shorten_address(row["buyer"])}</a></td>')
        table_html += (f'<td class="link-cell"><a href="{format_gunzscan_link(row["transaction_hash"])}" target="_blank">'
                    f'{shorten_address(row["transaction_hash"])}</a></td>')
        table_html += (f'<td class="link-cell"><a href="{row["item_url"]}" target="_blank">OpenSea</a></td>')
        table_html += '</tr>'

    table_html += '</tbody></table>'
    st.markdown(table_html, unsafe_allow_html=True)


def render_sales_table_collapsible(
    filtered_df: pd.DataFrame,
    show_usd: bool,
    current_gun_price: float,
    items_per_page: int = ITEMS_PER_PAGE
):
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text. technical diagnostic text
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text, technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Args:
        filtered_df: DataFrame technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
        show_usd: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text USD
        current_gun_price: technical diagnostic text technical diagnostic text GUN
        items_per_page: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    """
    if filtered_df.empty:
        return
    
    # technical implementation note technical implementation note technical implementation note technical implementation note (technical implementation note technical implementation note technical implementation note)
    filtered_df_sorted = filtered_df.sort_values(
        by='sale_date',
        ascending=False,
        kind='stable',
    )
    
    # technical implementation note technical implementation note technical implementation note
    page = get_current_page()
    pagination = paginate_dataframe(filtered_df_sorted, page, items_per_page)
    
    # technical implementation note, technical implementation note technical implementation note technical implementation note technical implementation note
    if page < 1 or page > pagination['total_pages']:
        page = 1
        pagination = paginate_dataframe(filtered_df_sorted, page, items_per_page)
    
    # technical implementation note expander technical implementation note technical implementation note technical implementation note (technical implementation note technical implementation note technical implementation note)
    with st.expander("Sales History Details", expanded=False):
        # technical implementation note technical implementation note
        render_sales_table(pagination['page_data'], show_usd, current_gun_price)
        
        # technical implementation note technical implementation note - technical implementation note technical implementation note
        current_page = pagination['page']
        total_pages = pagination['total_pages']
        total_records = len(filtered_df_sorted)
        
        # technical implementation note technical implementation note technical implementation note
        prev_disabled = current_page <= 1
        next_disabled = current_page >= total_pages
        
        # technical implementation note technical implementation note technical implementation note technical implementation note - technical implementation note technical implementation note technical implementation note technical implementation note
        # technical implementation note [5, 1, 1, 1, 5] technical implementation note technical implementation note technical implementation note
        pag_col1, pag_col2, pag_col3, pag_col4, pag_col5 = st.columns([4, 2, 1, 2, 4])
        
        with pag_col2:
            # Previous page button.
            if st.button(
                "Previous",
                key="sales_prev_page",
                disabled=prev_disabled,
                use_container_width=True
            ):
                if current_page > 1:
                    new_page = current_page - 1
                    st.query_params['page'] = str(new_page)
                    st.rerun()
        
        with pag_col3:
            # technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
            st.markdown(
                f'<div class="otg-pagination-number">{current_page}</div>',
                unsafe_allow_html=True
            )
        
        with pag_col4:
            # Next page button.
            if st.button(
                "Next",
                key="sales_next_page",
                disabled=next_disabled,
                use_container_width=True
            ):
                if current_page < total_pages:
                    new_page = current_page + 1
                    st.query_params['page'] = str(new_page)
                    st.rerun()
        
        # technical implementation note technical implementation note technical implementation note/technical implementation note - technical implementation note technical implementation note, technical implementation note technical implementation note
        st.markdown(f"""
            <div class="otg-pagination-info">
                Page {current_page} of {total_pages} | {total_records} total records
            </div>
        """, unsafe_allow_html=True)
