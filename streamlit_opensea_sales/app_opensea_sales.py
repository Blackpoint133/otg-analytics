"""
Off The Grid Streamlit Application.

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text. technical diagnostic text technical diagnostic text technical diagnostic text, 
technical diagnostic text UI technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.

technical diagnostic text technical diagnostic text:
================================================================================
technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text. technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text:
  ❌ items_index.json
  ❌ .import_state.json
  ❌ current_price.csv

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text update'technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text:
  ✅ background_indexer.py - technical diagnostic text/technical diagnostic text items_index.json
  ✅ import_opensea_sales.py - technical diagnostic text technical diagnostic text technical diagnostic text CSV/technical diagnostic text

technical diagnostic text technical diagnostic text technical diagnostic text:
1. technical diagnostic text technical diagnostic text: technical diagnostic text lightweight technical diagnostic text (technical diagnostic text rebuild)
2. technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text URL technical diagnostic text technical diagnostic text technical diagnostic text
3. technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
4. technical diagnostic text technical diagnostic text CSV technical diagnostic text technical diagnostic text
5. technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text

technical diagnostic text READ-ONLY:
technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text, technical diagnostic text technical diagnostic text
technical diagnostic text technical diagnostic text. technical diagnostic text data_access._assert_no_index_write_functions()
================================================================================
"""

import os
import base64
from pathlib import Path
import streamlit as st
import pandas as pd

from logging_compat import info, error, warning

# technical implementation note technical implementation note technical implementation note
from config import PAGE_TITLE, PAGE_LAYOUT, ITEMS_PER_PAGE, get_assets_dir

# technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
from loader import show_loader

# technical implementation note technical implementation note (technical implementation note technical implementation note)
# technical implementation note: technical implementation note technical implementation note technical implementation note technical implementation note, technical implementation note technical implementation note!
from data_access import (
    load_items_index,
    get_item_data_from_record,
    load_current_price
)

# technical implementation note technical implementation note
from state import initialize_selected_item, prepare_filter_state

# UI technical implementation note
from ui import (
    apply_global_styles,
    render_sidebar,
    render_market_sidebar_controls,
    render_top_items_sidebar_controls,
    render_item_header,
    render_metrics,
    render_wallet_activity,
    render_sales_table,
    render_sales_table_collapsible,
    get_current_page,
    paginate_dataframe,
    render_sidebar_footer,
    render_sidebar_logo,
    mode_switch
)
from ui.market_overview import render_market_overview
from ui.top_items_overview import render_top_items_overview
from ui.item_overview import render_item_overview
from site_analytics import record_current_session_once
from visitor_identity import get_browser_identity
from visitor_dashboard import render_visitor_dashboard


def _get_page_icon_base64() -> str:
    """technical documentation technical documentation technical documentation technical documentation technical documentation base64 technical documentation page_icon."""
    try:
        icon_path = Path(__file__).resolve().parents[1] / "img" / "logo.png"
        with open(icon_path, 'rb') as f:
            icon_data = base64.b64encode(f.read()).decode()
        return f"data:image/png;base64,{icon_data}"
    except Exception:
        return "▲"  # Fallback technical diagnostic text technical diagnostic text


def main():
    """technical documentation technical documentation technical documentation technical documentation technical documentation technical documentation technical documentation."""
    # technical implementation note technical implementation note technical implementation note technical implementation note (technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note)
    page_icon = _get_page_icon_base64()
    st.set_page_config(page_title=PAGE_TITLE, page_icon=page_icon, layout=PAGE_LAYOUT)
    
    # technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
    show_loader()

    # technical implementation note technical implementation note technical implementation note
    apply_global_styles()
    

    info("Application started (lazy-load architecture)")

    # technical implementation note technical implementation note technical implementation note
    st.sidebar.markdown("<div style='flex: 1'></div>", unsafe_allow_html=True)

    # technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
    render_sidebar_logo()

    requested_mode = st.query_params.get("mode", "item")
    if isinstance(requested_mode, list):
        requested_mode = requested_mode[0] if requested_mode else "item"
    if requested_mode == "internal_analytics":
        render_visitor_dashboard()
        return
    
    # ════════════════════════════════════════════════════════════════
    # technical implementation note technical implementation note: ITEM vs MARKET vs TOP ITEMS ANALYTICS
    # ════════════════════════════════════════════════════════════════
    current_mode = mode_switch.render_mode_switch()
    browser_identity = get_browser_identity()
    record_current_session_once(
        mode=current_mode,
        item_key=st.query_params.get("item"),
        browser_identity=browser_identity,
    )
    
    # Load current gun price early for all modes
    current_gun_price = load_current_price()
    
    # MARKET ANALYTICS MODE
    if current_mode == 'market':
        # Render market-specific sidebar controls
        market_controls = render_market_sidebar_controls()
        
        # Pass controls to market overview
        with st.container(key="market_main_content"):
            render_market_overview(
                show_usd=market_controls['show_usd'],
                current_gun_price=current_gun_price,
                show_token_price=market_controls['show_token_price']
            )
        render_sidebar_footer()
        return
    
    # TOP ITEMS ANALYTICS MODE
    if current_mode == 'top_items':
        # Render top items-specific sidebar controls
        top_items_controls = render_top_items_sidebar_controls()
        
        # Pass controls to top items overview
        with st.container(key="top_items_main_content"):
            render_top_items_overview(
                show_usd=top_items_controls['show_usd'],
                current_gun_price=current_gun_price,
                ranking_mode=top_items_controls['ranking_mode'],
                period=top_items_controls['period'],
                top_items_view=top_items_controls['top_items_view']
            )
        render_sidebar_footer()
        return
    
    # ════════════════════════════════════════════════════════════════
    # ITEM ANALYTICS MODE (technical implementation note technical implementation note, technical implementation note technical implementation note technical implementation note)
    # ════════════════════════════════════════════════════════════════

    # ════════════════════════════════════════════════════════════════
    # technical implementation note 1: technical implementation note LIGHTWEIGHT technical implementation note (technical implementation note technical implementation note technical implementation note CSV)
    # ════════════════════════════════════════════════════════════════
    items_index, diagnostics = load_items_index()
    
    info(f"technical diagnostic text technical diagnostic text technical diagnostic text {len(items_index)} technical diagnostic text, technical diagnostic text technical diagnostic text GUN: {current_gun_price}")
    
    # If no items loaded, show error and exit
    if not items_index or not diagnostics.success:
        error(f"Index loading error: {diagnostics.error_message or 'Index is empty'}")
        st.error(
            f"❌ Index loading error: {diagnostics.error_message or 'Index is empty'}\n\n"
            f"Make sure the file 'data_opensea_sales/items_index.json' exists "
            f"or that CSV files are present in 'data_opensea_sales/sales/' directory."
        )
        return
    
    # ════════════════════════════════════════════════════════════════
    # technical implementation note 2: technical implementation note technical implementation note technical implementation note
    # ════════════════════════════════════════════════════════════════
    initialize_selected_item(items_index)
    info("technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text URL technical diagnostic text technical diagnostic text technical diagnostic text")
    
    # ════════════════════════════════════════════════════════════════
    # technical implementation note 3: technical implementation note technical implementation note technical implementation note (technical implementation note technical implementation note, technical implementation note technical implementation note CSV)
    # ════════════════════════════════════════════════════════════════
    sidebar_options = render_sidebar(items_index, browser_identity=browser_identity)
    if sidebar_options is None:
        return
    
    # Validate and prepare filter state
    try:
        filter_state = prepare_filter_state(sidebar_options)
    except ValueError as e:
        error(f"Filter validation error: {str(e)}")
        st.error(f"❌ Filter validation error: {str(e)}")
        return
    
    # technical implementation note technical implementation note technical implementation note
    current_selected_item = filter_state['selected_item']
    item_record = filter_state['item_record']
    show_volume = filter_state['show_volume']
    show_usd = filter_state['show_usd']
    show_trend_line = filter_state.get('show_trend_line', True)
    item_view_mode = filter_state.get('item_view_mode', 'chart')
    highlight_wallet = filter_state.get('highlight_wallet')
    
    # ════════════════════════════════════════════════════════════════
    # technical implementation note 4: technical implementation note technical implementation note CSV technical implementation note technical implementation note (lazy!)
    # ════════════════════════════════════════════════════════════════
    info(f"[LAZY] Loading data for '{current_selected_item}'...")
    df = get_item_data_from_record(item_record)
    info(f"[LAZY] Loaded {len(df)} records for '{current_selected_item}'")
    
    if df.empty:
        error(f"Failed to load data for '{current_selected_item}'. File: {item_record.get('file_path')}")
        st.error(
            f"❌ Failed to load data for '{current_selected_item}'.\n\n"
            f"File: {item_record.get('file_path')}"
        )
        return
    
    # technical implementation note technical implementation note
    df['sale_date'] = pd.to_datetime(df['sale_date'])
    
    filtered_df = df.copy()
    filtered_df['formatted_date'] = filtered_df['sale_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    info(f"Using full item sales history: {len(filtered_df)} records")
    
    if filtered_df.empty:
        warning("technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text")
    
    # ════════════════════════════════════════════════════════════════
    # technical implementation note 5: technical implementation note technical implementation note (technical implementation note technical implementation note technical implementation note technical implementation note)
    # ════════════════════════════════════════════════════════════════
    
    # technical implementation note Item Analytics technical implementation note technical implementation note technical implementation note
    render_item_overview(
        df=df,
        filtered_df=filtered_df,
        current_selected_item=current_selected_item,
        item_record=item_record,
        show_volume=show_volume,
        show_usd=show_usd,
        current_gun_price=current_gun_price,
        show_trend_line=show_trend_line,
        item_view_mode=item_view_mode,
        highlight_wallet=highlight_wallet,
        items_per_page=ITEMS_PER_PAGE
    )

    # ════════════════════════════════════════════════════════════════
    # technical implementation note technical implementation note technical implementation note
    # ════════════════════════════════════════════════════════════════
    render_sidebar_footer()


if __name__ == "__main__":
    main()
