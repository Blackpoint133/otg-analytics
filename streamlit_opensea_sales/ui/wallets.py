"""
technical diagnostic text technical diagnostic text (technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text).

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
"""

import streamlit as st
import pandas as pd

from formatters import shorten_address, format_opensea_link


def render_wallet_activity(combined_df: pd.DataFrame):
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text (technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text).
    
    Args:
        combined_df: technical diagnostic text DataFrame technical diagnostic text technical diagnostic text technical diagnostic text
    """
    with st.expander("Wallet Activity Details"):
        wallet_col1, wallet_col2 = st.columns(2)
        
        with wallet_col1:
            st.subheader("Top Sellers")
            top_sellers = (combined_df['seller']
                         .value_counts()
                         .head(5)
                         .reset_index())
            top_sellers.columns = ['Address', 'Sales']
            
            sellers_html = '<table class="sales-table"><tbody>'
            for _, row in top_sellers.iterrows():
                sellers_html += '<tr>'
                sellers_html += (f'<td class="link-cell"><a href="{format_opensea_link(row["Address"])}" '
                               f'target="_blank">{shorten_address(row["Address"])}</a></td>')
                sellers_html += f'<td>{row["Sales"]} sales</td>'
                sellers_html += '</tr>'
            sellers_html += '</tbody></table>'
            st.markdown(sellers_html, unsafe_allow_html=True)
        
        with wallet_col2:
            st.subheader("Top Buyers")
            top_buyers = (combined_df['buyer']
                        .value_counts()
                        .head(5)
                        .reset_index())
            top_buyers.columns = ['Address', 'Purchases']
            
            buyers_html = '<table class="sales-table"><tbody>'
            for _, row in top_buyers.iterrows():
                buyers_html += '<tr>'
                buyers_html += (f'<td class="link-cell"><a href="{format_opensea_link(row["Address"])}" target="_blank">'
                              f'{shorten_address(row["Address"])}</a></td>')
                buyers_html += f'<td>{row["Purchases"]} purchases</td>'
                buyers_html += '</tr>'
            buyers_html += '</tbody></table>'
            st.markdown(buyers_html, unsafe_allow_html=True)
