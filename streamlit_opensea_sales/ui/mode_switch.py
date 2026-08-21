"""
Mode Switch UI Component.

technical diagnostic text technical diagnostic text technical diagnostic text:
- ITEM ANALYTICS (technical diagnostic text technical diagnostic text)
- MARKET ANALYTICS (technical diagnostic text technical diagnostic text)

technical diagnostic text query parameter `mode` technical diagnostic text persisting technical diagnostic text.

technical diagnostic text: technical diagnostic text HTML anchor links technical diagnostic text OTG cyberpunk technical diagnostic text
- technical diagnostic text: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
- technical diagnostic text: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
- technical diagnostic text: technical diagnostic text technical diagnostic text, technical diagnostic text technical diagnostic text
"""

import streamlit as st
from typing import Literal


def render_mode_switch() -> Literal['item', 'market', 'top_items']:
    """
    technical diagnostic text mode switcher technical diagnostic text sidebar technical diagnostic text technical diagnostic text HTML anchor links.
    
    technical diagnostic text query param `mode` technical diagnostic text technical diagnostic text technical diagnostic text.
    Default: 'item'
    
    technical diagnostic text technical diagnostic text technical diagnostic text: ?mode=item, ?mode=market, ?mode=top_items
    Streamlit technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text URL.
    
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text OTG cyberpunk technical diagnostic text:
    - technical diagnostic text technical diagnostic text: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    - technical diagnostic text technical diagnostic text: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    - technical diagnostic text emoji, technical diagnostic text "MODE" label
    
    Returns:
        'item', 'market' technical diagnostic text 'top_items' technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    """
    # Get current mode from query params
    current_mode = st.query_params.get('mode', 'item')
    if isinstance(current_mode, list):
        current_mode = current_mode[0]
    
    # Ensure valid mode (whitelist: item, market, top_items)
    if current_mode not in ['item', 'market', 'top_items']:
        current_mode = 'item'
    
    # Determine active classes
    item_class = "active" if current_mode == "item" else ""
    market_class = "active" if current_mode == "market" else ""
    top_items_class = "active" if current_mode == "top_items" else ""
    
    # Render mode switch using styled HTML anchor links with custom CSS
    st.sidebar.markdown(f"""
        <style>
        .otg-mode-switch {{
            margin: 18px 0 22px 0;
        }}

        .otg-mode-link {{
            display: block;
            width: 100%;
            box-sizing: border-box;
            min-height: 58px;
            padding: 18px 16px;
            margin-bottom: 10px;
            border: 2px solid var(--otg-accent);
            background: var(--otg-bg-secondary);
            color: var(--otg-text-primary) !important;
            text-decoration: none !important;
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            text-align: center;
            border-radius: 0;
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        .otg-mode-link:hover {{
            background: rgba(255, 0, 58, 0.08);
            color: var(--otg-accent) !important;
            text-decoration: none !important;
        }}

        .otg-mode-link.active {{
            color: var(--otg-accent) !important;
            box-shadow: inset 5px 0 0 var(--otg-accent);
            background: var(--otg-bg-secondary);
        }}

        .otg-mode-link.active:hover {{
            background: rgba(255, 0, 58, 0.06);
            color: var(--otg-accent) !important;
            text-decoration: none !important;
        }}

        .otg-mode-roadmap-disabled {{
            appearance: none;
            -webkit-appearance: none;
            border: 2px solid rgba(200, 200, 205, 0.45);
            background: var(--otg-bg-secondary);
            color: var(--otg-text-secondary) !important;
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 1px;
            line-height: normal;
            text-transform: uppercase;
            cursor: default;
            transition: none;
            text-align: center;
        }}

        .otg-mode-link.otg-mode-roadmap-disabled:hover,
        .otg-mode-link.otg-mode-roadmap-disabled:focus,
        .otg-mode-link.otg-mode-roadmap-disabled:focus-visible {{
            border-color: rgba(200, 200, 205, 0.45);
            background: var(--otg-bg-secondary);
            color: var(--otg-text-secondary) !important;
            box-shadow: none;
            outline: none;
            text-decoration: none !important;
        }}

        </style>

        <div class="otg-mode-switch">
            <a class="otg-mode-link {item_class}" href="?mode=item" target="_self">ITEM ANALYTICS</a>
            <a class="otg-mode-link {market_class}" href="?mode=market" target="_self">MARKET ANALYTICS</a>
            <a class="otg-mode-link {top_items_class}" href="?mode=top_items" target="_self">TOP ITEMS ANALYTICS</a>
            <button type="button" class="otg-mode-link otg-mode-roadmap-disabled" disabled aria-disabled="true" tabindex="-1">ROADMAP</button>
        </div>
    """, unsafe_allow_html=True)
    
    return current_mode
