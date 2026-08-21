"""
technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
"""

import streamlit as st
import pandas as pd

from formatters import get_rarity_style


def render_item_header(df: pd.DataFrame, current_selected_item: str):
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Args:
        df: DataFrame technical diagnostic text technical diagnostic text technical diagnostic text (technical diagnostic text technical diagnostic text technical diagnostic text, technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text)
        current_selected_item: technical diagnostic text technical diagnostic text technical diagnostic text
    """
    if 'rarity' in df.columns and len(df) > 0:
        rarity = df['rarity'].iloc[0]
    else:
        # technical implementation note technical implementation note technical implementation note technical implementation note df, technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
        rarity = current_selected_item.split()[-1] if current_selected_item else 'Common'
    
    color, rarity_class = get_rarity_style(rarity)
    # technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
    item_name = current_selected_item.rsplit(' ', 1)[0]
    st.markdown(f"""
        <div class="rarity-container">
            <h3 style="margin: 0;">{item_name}</h3>
            <span class="rarity-dot" style="background-color: {color};"></span>
            <span class="rarity-text rarity-{rarity_class}">{rarity}</span>
        </div>
    """, unsafe_allow_html=True)
