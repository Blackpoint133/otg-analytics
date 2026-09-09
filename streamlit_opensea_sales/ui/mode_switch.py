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


def render_mode_switch() -> Literal['item', 'market', 'top_items', 'trader']:
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
    raw_mode = st.query_params.get('mode', 'item')
    if isinstance(raw_mode, list):
        raw_mode = raw_mode[0]
    current_mode = 'trader' if raw_mode in ('trader', 'top_traders') else raw_mode
    
    # Ensure valid mode (whitelist)
    if current_mode not in ['item', 'market', 'top_items', 'trader']:
        current_mode = 'item'
    
    # Determine active classes
    item_class = "active" if current_mode == "item" else ""
    market_class = "active" if current_mode == "market" else ""
    top_items_class = "active" if current_mode == "top_items" else ""
    trader_class = "active" if current_mode == "trader" else ""
    
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

        .otg-mode-roadmap {{
            border-color: #FF9D2E;
            color: #FF9D2E !important;
            animation: otg-roadmap-pulse 2.8s ease-in-out infinite;
        }}

        .otg-mode-link.otg-mode-roadmap:hover,
        .otg-mode-link.otg-mode-roadmap.active {{
            border-color: #FF9D2E;
            background: #FF9D2E;
            color: #000 !important;
            box-shadow: 0 0 14px rgba(255, 157, 46, 0.45);
        }}

        @keyframes otg-roadmap-pulse {{
            0%, 100% {{ box-shadow: 0 0 0 rgba(255, 157, 46, 0); }}
            50% {{ box-shadow: 0 0 12px rgba(255, 157, 46, 0.38); }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            .otg-mode-link.otg-mode-roadmap {{ animation: none; }}
        }}

        </style>

        <div class="otg-mode-switch">
            <a class="otg-mode-link {item_class}" href="?mode=item" target="_self">ITEM</a>
            <a class="otg-mode-link {market_class}" href="?mode=market" target="_self">MARKET</a>
            <a class="otg-mode-link {top_items_class}" href="?mode=top_items" target="_self">TOP ITEMS</a>
            <a class="otg-mode-link {trader_class}" href="?mode=top_traders" target="_self">TOP TRADERS</a>
            <a class="otg-mode-link otg-mode-roadmap" href="/?mode=roadmap" target="_self">ROADMAP</a>
        </div>
    """, unsafe_allow_html=True)
    
    return current_mode
