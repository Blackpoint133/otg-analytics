"""
technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text Off The Grid.
"""

import base64
import streamlit as st

from config import (
    get_assets_logo_image,
    EPIC_GAMES_URL,
)


def render_sidebar_logo():
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text, technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    technical diagnostic text technical diagnostic text.
    """
    logo_path = get_assets_logo_image()
    try:
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        st.sidebar.markdown(f"""
            <div class="otg-logo">
                <a href="{EPIC_GAMES_URL}" target="_blank">
                    <img src="data:image/png;base64,{logo_base64}" alt="Off The Grid">
                </a>
            </div>
        """, unsafe_allow_html=True)
    except Exception:
        # Fallback technical implementation note technical implementation note technical implementation note
        st.sidebar.markdown(f"""
            <div class="otg-logo">
                <a href="{EPIC_GAMES_URL}" target="_blank">
                    <span aria-label="Off The Grid"></span>
                </a>
            </div>
        """, unsafe_allow_html=True)
