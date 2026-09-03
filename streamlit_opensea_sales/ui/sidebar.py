"""
technical diagnostic text technical diagnostic text technical diagnostic text.

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
"""

from pathlib import Path
from typing import Dict, Optional, Any
from collections import Counter
import pandas as pd
import streamlit as st

from logging_compat import get_module_logger, info

from ui.viewport import get_viewport_info
from site_item_events import record_explicit_item_selection, record_initial_item_context
from site_item_events import EVENT_INITIALIZED_KEY, LAST_ITEM_KEY, SEQUENCE_KEY
from data_access import load_item_data


SIDEBAR_LOG_PATH = Path(__file__).resolve().parents[2] / "logs" / "site_analytics.log"
SIDEBAR_LOGGER = get_module_logger("sidebar", log_file=SIDEBAR_LOG_PATH, module_tag="sidebar")


def _log_item_ui(marker: str, **fields: Any) -> None:
    """Emit redacted item-widget diagnostics without affecting the public UI."""
    try:
        payload = " ".join(f"{key}={value}" for key, value in fields.items())
        SIDEBAR_LOGGER.info(f"{marker}{(' ' + payload) if payload else ''}")
    except Exception:
        pass


def _safe_event_sequence() -> int:
    value = st.session_state.get(SEQUENCE_KEY, 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _on_item_selection_changed(browser_identity: Optional[Dict[str, Any]]) -> None:
    selected_item = st.session_state.get("selected_item")
    selected_present = selected_item is not None
    identity_present = isinstance(browser_identity, dict) and browser_identity.get("status") == "ok"
    _log_item_ui(
        "ITEM_UI_CALLBACK_ENTER",
        selected_present=selected_present,
        browser_identity_present=identity_present,
    )
    last_item = st.session_state.get(LAST_ITEM_KEY)
    _log_item_ui(
        "ITEM_UI_CALLBACK_STATE",
        selected_present=selected_present,
        same_as_last=selected_present and last_item is not None and selected_item == last_item,
        sequence=_safe_event_sequence(),
    )
    _log_item_ui("ITEM_UI_EVENT_CALL", browser_identity_present=identity_present)
    result = record_explicit_item_selection(selected_item, browser_identity)
    _log_item_ui("ITEM_UI_EVENT_RESULT", success=bool(result))


def _is_mobile_viewport(viewport_info: Optional[Dict]) -> bool:
    """Return True only when the viewport component provides a mobile width."""
    if not isinstance(viewport_info, dict):
        return False

    viewport_width = viewport_info.get("width")
    if isinstance(viewport_width, int):
        return viewport_width <= 768

    return bool(viewport_info.get("isMobile", False))


def _wallet_options_for_item(item_record: Optional[Dict]) -> list:
    """Return full wallet values ordered by participation, without address folding."""
    if not isinstance(item_record, dict) or not item_record.get('file_path'):
        return []
    try:
        path = Path(item_record['file_path'])
        if not path.exists():
            return []
        df = load_item_data(str(path), path.stat().st_mtime)
    except Exception:
        return []
    counts = Counter()
    for _, row in df.iterrows():
        wallets = set()
        for field in ('buyer', 'seller'):
            value = row.get(field)
            if pd.isna(value):
                continue
            value = str(value).strip()
            if value:
                wallets.add(value)
        for wallet in wallets:
            counts[wallet] += 1
    return sorted(counts, key=lambda wallet: (-counts[wallet], wallet))


def _short_wallet_label(wallet: str) -> str:
    value = str(wallet)
    return value if len(value) <= 12 else f"{value[:6]}…{value[-4:]}"


SHARED_DISPLAY_OPTIONS_CSS = """
    <style>
    .otg-sidebar-label {
        font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        color: var(--otg-text-secondary);
        display: block;
        margin: 0 0 10px 0;
        padding: 0;
        height: auto;
        min-height: 0;
        overflow: visible;
        line-height: 1.1;
    }

    .otg-sidebar-section-gap {
        height: 14px;
        min-height: 14px;
        margin: 0;
        padding: 0;
        display: block;
    }
    </style>
"""


def render_sidebar(items_index: Dict[str, Any], browser_identity: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    technical diagnostic text technical diagnostic text Streamlit technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text CSS.
    
    Args:
        items_index: technical diagnostic text item_key -> item_record technical diagnostic text technical diagnostic text
    
    Returns:
        dict: technical diagnostic text technical diagnostic text selected_item, show_volume, show_usd, show_trend_line
        technical diagnostic text None technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    """
    _log_item_ui(
        "ITEM_UI_RENDER",
        selected_present=st.session_state.get("selected_item") is not None,
        event_initialized=st.session_state.get(EVENT_INITIALIZED_KEY) is True,
        event_sequence=_safe_event_sequence(),
    )

    def format_option(item_key: str) -> str:
        """technical documentation technical documentation technical documentation technical documentation technical documentation technical documentation."""
        if item_key in items_index:
            item_record = items_index[item_key]
            rarity = item_record.get('rarity', 'Common')
            display_name = item_record.get('display_name', item_key)
            dots = {
                'Common': '⚪',
                'Uncommon': '🟢',
                'Rare': '🔵',
                'Epic': '🟣',
                'Legendary': '🟡'
            }
            return f"{dots.get(rarity, '⚪')} {display_name}"
        return f"⚪ {item_key}"
    
    st.sidebar.header("Display Options")

    item_sidebar_css = SHARED_DISPLAY_OPTIONS_CSS + """
        <style>
        .st-key-item_view_buttons {
            padding: 0;
        }

        .st-key-item_view_buttons button {
            width: 100% !important;
            min-height: 28px !important;
            height: 28px !important;
            padding: 4px 10px !important;
            margin-bottom: 3px !important;
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif !important;
            font-size: 10px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            border-radius: 1px !important;
            cursor: pointer !important;
            transition: all 0.12s linear !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        
        .st-key-item_view_buttons button[data-testid="stBaseButton-secondary"] {
            background-color: #0a0a0a !important;
            border: 1px solid #333 !important;
            color: #666 !important;
        }
        
        .st-key-item_view_buttons button[data-testid="stBaseButton-secondary"]:hover {
            background-color: #0f0f0f !important;
            border-color: #444 !important;
            color: #888 !important;
        }
        
        .st-key-item_view_buttons button[data-testid="stBaseButton-primary"] {
            background-color: #FF003A !important;
            border: 1px solid #FF003A !important;
            color: #FFFFFF !important;
            font-weight: 800 !important;
        }
        
        .st-key-item_view_buttons button[data-testid="stBaseButton-primary"]:hover {
            background-color: #E60033 !important;
            border-color: #FF003A !important;
            color: #FFFFFF !important;
        }
        </style>
    """
    st.sidebar.html(item_sidebar_css)

    viewport_info = get_viewport_info(key="item_chart_viewport")
    is_mobile_viewport = _is_mobile_viewport(viewport_info)
    st.session_state['item_is_mobile_viewport'] = is_mobile_viewport
    
    # Selectbox with key automatically syncs with st.session_state
    st.sidebar.markdown('<div class="otg-sidebar-label">SELECT ITEM</div>', unsafe_allow_html=True)
    _log_item_ui(
        "ITEM_UI_SELECTBOX_READY",
        callback_registered=True,
        selected_present=st.session_state.get("selected_item") is not None,
    )
    st.sidebar.selectbox(
        "Select Item",
        options=sorted(items_index.keys()),
        format_func=format_option,
        key="selected_item",
        on_change=_on_item_selection_changed,
        args=(browser_identity,),
        label_visibility="collapsed"
    )
    _log_item_ui(
        "ITEM_UI_POST_WIDGET",
        selected_present=st.session_state.get("selected_item") is not None,
    )

    record_initial_item_context(
        st.session_state.selected_item,
        st.session_state.get("item_initial_event_type", "initial_default"),
        browser_identity,
    )
    
    # technical implementation note technical implementation note technical implementation note technical implementation note session_state
    current_selected_item = st.session_state.selected_item
    info(f"[SELECT] technical diagnostic text technical diagnostic text technical diagnostic text: '{current_selected_item}'")
    
    # technical implementation note URL technical implementation note technical implementation note technical implementation note technical implementation note
    _log_item_ui("ITEM_UI_QUERY_SYNC", selected_present=current_selected_item is not None)
    st.query_params['item'] = current_selected_item
    
    # technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
    item_record = items_index.get(current_selected_item)
    if not item_record:
        st.error(f"Item '{current_selected_item}' not found in index.")
        return None

    wallet_options = _wallet_options_for_item(item_record)
    wallet_key = f"item_highlight_wallet_{abs(hash(current_selected_item))}"
    current_wallet = st.session_state.get(wallet_key, "ALL WALLETS")
    if current_wallet != "ALL WALLETS" and current_wallet not in wallet_options:
        current_wallet = "ALL WALLETS"
        st.session_state[wallet_key] = current_wallet
    st.sidebar.markdown('<div class="otg-sidebar-label">HIGHLIGHT WALLET</div>', unsafe_allow_html=True)
    highlight_wallet = st.sidebar.selectbox(
        "Highlight Wallet",
        options=["ALL WALLETS", *wallet_options],
        format_func=lambda value: value if value == "ALL WALLETS" else _short_wallet_label(value),
        key=wallet_key,
        label_visibility="collapsed",
    )
    
    show_volume = False
    if 'item_show_usd' not in st.session_state:
        st.session_state.item_show_usd = True
    if 'item_show_trend_line' not in st.session_state:
        st.session_state.item_show_trend_line = False

    st.sidebar.markdown('<div class="otg-sidebar-section-gap"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="otg-sidebar-label">VALUE DISPLAY</div>', unsafe_allow_html=True)
    show_usd = st.sidebar.checkbox('USD Price', key='item_show_usd')
    show_trend_line = st.sidebar.checkbox('Trend Line', key='item_show_trend_line')
    
    # Initialize session state for item_view_mode if not present
    if 'item_view_mode' not in st.session_state:
        st.session_state.item_view_mode = 'chart'
    
    current_item_view = st.session_state.item_view_mode

    if not is_mobile_viewport:
        st.sidebar.markdown('<div class="otg-sidebar-section-gap"></div>', unsafe_allow_html=True)
        st.sidebar.markdown('<div class="otg-sidebar-label">VIEW</div>', unsafe_allow_html=True)

        # Wrap only the View buttons for scoped styling.
        with st.sidebar.container(key="item_view_buttons"):
            
            # View buttons using native type parameter
            if st.button(
                "CHART",
                key="item_view_chart",
                use_container_width=True,
                type="primary" if current_item_view == 'chart' else "secondary"
            ):
                st.session_state.item_view_mode = 'chart'
                st.rerun()
            
            if st.button(
                "TABLE",
                key="item_view_table",
                use_container_width=True,
                type="primary" if current_item_view == 'table' else "secondary"
            ):
                st.session_state.item_view_mode = 'table'
                st.rerun()
    
    return {
        'selected_item': current_selected_item,
        'item_record': item_record,
        'show_volume': show_volume,
        'show_usd': show_usd,
        'show_trend_line': show_trend_line,
        'item_view_mode': current_item_view,
        'is_mobile_viewport': is_mobile_viewport
        , 'highlight_wallet': None if highlight_wallet == "ALL WALLETS" else highlight_wallet
    }


def render_market_sidebar_controls() -> Dict[str, Any]:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text MARKET ANALYTICS.
    
    technical diagnostic text technical diagnostic text Streamlit technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text CSS.
    
    Returns:
        dict: technical diagnostic text technical diagnostic text show_usd, show_token_price
    """
    st.sidebar.header("Display Options")
    
    if 'market_show_usd' not in st.session_state:
        st.session_state.market_show_usd = True

    # Display options
    st.sidebar.html(SHARED_DISPLAY_OPTIONS_CSS)
    st.sidebar.markdown(
        '<div class="otg-sidebar-label">VALUE DISPLAY</div>',
        unsafe_allow_html=True,
    )
    show_usd = st.sidebar.checkbox(
        'USD Price',
        key='market_show_usd'
    )
    show_token_price = st.sidebar.checkbox(
        'Token Price',
        value=False,
        key='market_show_token_price'
    )

    if 'market_time_range' not in st.session_state:
        st.session_state.market_time_range = '12m'

    current_period = st.session_state.market_time_range

    st.sidebar.markdown(
        '<div class="otg-sidebar-section-gap"></div>',
        unsafe_allow_html=True,
    )

    st.sidebar.html("""
        <style>
        .st-key-market_time_range_controls {
            padding: 0;
        }

        .st-key-market_time_range_controls button {
            width: 100% !important;
            min-height: 28px !important;
            height: 28px !important;
            padding: 4px 10px !important;
            margin-bottom: 3px !important;
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif !important;
            font-size: 10px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            border-radius: 1px !important;
            cursor: pointer !important;
            transition: all 0.12s linear !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        .st-key-market_time_range_controls button[data-testid="stBaseButton-secondary"] {
            background-color: #0a0a0a !important;
            border: 1px solid #333 !important;
            color: #666 !important;
        }

        .st-key-market_time_range_controls button[data-testid="stBaseButton-secondary"]:hover {
            background-color: #0f0f0f !important;
            border-color: #444 !important;
            color: #888 !important;
        }

        .st-key-market_time_range_controls button[data-testid="stBaseButton-primary"] {
            background-color: #FF003A !important;
            border: 1px solid #FF003A !important;
            color: #FFFFFF !important;
            font-weight: 800 !important;
        }

        .st-key-market_time_range_controls button[data-testid="stBaseButton-primary"]:hover {
            background-color: #E60033 !important;
            border-color: #FF003A !important;
            color: #FFFFFF !important;
        }
        </style>
    """)

    with st.sidebar.container(key="market_time_range_controls"):
        st.markdown('<div class="otg-sidebar-label">PERIOD</div>', unsafe_allow_html=True)

        if st.button(
            "ALL",
            key="market_time_range_all",
            use_container_width=True,
            type="primary" if current_period == 'all' else "secondary"
        ):
            st.session_state.market_time_range = 'all'
            st.rerun()

        if st.button(
            "12 MONTH",
            key="market_time_range_12m",
            use_container_width=True,
            type="primary" if current_period == '12m' else "secondary"
        ):
            st.session_state.market_time_range = '12m'
            st.rerun()

        if st.button(
            "6 MONTH",
            key="market_time_range_6m",
            use_container_width=True,
            type="primary" if current_period == '6m' else "secondary"
        ):
            st.session_state.market_time_range = '6m'
            st.rerun()

        if st.button(
            "3 MONTH",
            key="market_time_range_3m",
            use_container_width=True,
            type="primary" if current_period == '3m' else "secondary"
        ):
            st.session_state.market_time_range = '3m'
            st.rerun()
    
    info(f"Market sidebar: show_usd={show_usd}, show_token_price={show_token_price}, time_range={current_period}")
    
    return {
        'show_usd': show_usd,
        'show_token_price': show_token_price
    }


def render_top_items_sidebar_controls() -> Dict[str, Any]:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text TOP ITEMS ANALYTICS.
    
    technical diagnostic text technical diagnostic text Streamlit technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text CSS.
    
    Returns:
        dict: technical diagnostic text technical diagnostic text show_usd, ranking_mode, period
    """
    # Initialize session state for ranking mode if not present
    if 'top_items_ranking_mode' not in st.session_state:
        st.session_state.top_items_ranking_mode = 'market_strength'

    # Initialize session state for top_items_period if not present
    if 'top_items_period' not in st.session_state:
        st.session_state.top_items_period = 'all'

    # Initialize session state for top_items_view if not present
    if 'top_items_view' not in st.session_state:
        st.session_state.top_items_view = 'cards'

    # Resolve Top Items viewport before visible controls so the component slot
    # does not interrupt the VALUE DISPLAY -> SORT BY rhythm.
    if 'top_items_is_mobile_viewport' not in st.session_state:
        st.session_state.top_items_is_mobile_viewport = False
    if 'top_items_viewport_resolved' not in st.session_state:
        st.session_state.top_items_viewport_resolved = False

    with st.sidebar:
        viewport_info = get_viewport_info(key='top_items_viewport')
    if isinstance(viewport_info, dict):
        viewport_width = int(viewport_info.get('width', 0) or 0)
        st.session_state.top_items_is_mobile_viewport = viewport_width <= 768
        st.session_state.top_items_viewport_resolved = True

    viewport_resolved = bool(st.session_state.top_items_viewport_resolved)
    is_mobile = bool(st.session_state.top_items_is_mobile_viewport)

    if viewport_resolved and not is_mobile and st.session_state.top_items_view == 'chart':
        st.session_state.top_items_view = 'cards'
    if viewport_resolved and is_mobile and st.session_state.top_items_view == 'table':
        st.session_state.top_items_view = 'cards'

    current_mode = st.session_state.top_items_ranking_mode
    current_period = st.session_state.top_items_period
    current_view = st.session_state.top_items_view if viewport_resolved else 'cards'

    # Apply stable CSS scope targeting container before visible controls.
    st.sidebar.html("""
        <style>
        /* OTG Top Items Controls Container Scope */
        .st-key-top_items_filter_controls {
            padding: 0;
        }
        
        /* All buttons in container */
        .st-key-top_items_filter_controls button {
            width: 100% !important;
            min-height: 28px !important;
            height: 28px !important;
            padding: 4px 10px !important;
            margin-bottom: 3px !important;
            font-family: 'PP Supply Sans', 'Space Mono', monospace, sans-serif !important;
            font-size: 10px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            border-radius: 1px !important;
            cursor: pointer !important;
            transition: all 0.12s linear !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        
        /* Secondary buttons (inactive) */
        .st-key-top_items_filter_controls button[data-testid="stBaseButton-secondary"] {
            background-color: #0a0a0a !important;
            border: 1px solid #333 !important;
            color: #666 !important;
        }
        
        .st-key-top_items_filter_controls button[data-testid="stBaseButton-secondary"]:hover {
            background-color: #0f0f0f !important;
            border-color: #444 !important;
            color: #888 !important;
        }
        
        /* Primary buttons (active) */
        .st-key-top_items_filter_controls button[data-testid="stBaseButton-primary"] {
            background-color: #FF003A !important;
            border: 1px solid #FF003A !important;
            color: #FFFFFF !important;
            font-weight: 800 !important;
        }

        .st-key-top_items_filter_controls button:disabled {
            opacity: 0.42 !important;
            cursor: not-allowed !important;
        }
        
        .st-key-top_items_filter_controls button[data-testid="stBaseButton-primary"]:hover {
            background-color: #E60033 !important;
            border-color: #FF003A !important;
            color: #FFFFFF !important;
        }
        </style>
    """)

    st.sidebar.header("Display Options")
    st.sidebar.html(SHARED_DISPLAY_OPTIONS_CSS)
    st.sidebar.markdown(
        '<div class="otg-sidebar-label">VALUE DISPLAY</div>',
        unsafe_allow_html=True,
    )
    
    # Display options
    show_usd = st.sidebar.checkbox(
        'USD Price',
        value=True,
        key='top_items_show_usd'
    )
    
    st.sidebar.markdown(
        '<div class="otg-sidebar-section-gap"></div>',
        unsafe_allow_html=True,
    )
    
    # Wrap Top Items controls in stable container
    with st.sidebar.container(key="top_items_filter_controls"):
        # Render Sort By label
        st.markdown('<div class="otg-sidebar-label">SORT BY</div>', unsafe_allow_html=True)
        
        # Sort By buttons using native type parameter
        if st.button(
            "MARKET STRENGTH",
            key="top_items_rank_strength",
            use_container_width=True,
            type="primary" if current_mode == 'market_strength' else "secondary"
        ):
            st.session_state.top_items_ranking_mode = 'market_strength'
            st.rerun()
        
        if st.button(
            "VOLUME",
            key="top_items_rank_volume",
            use_container_width=True,
            type="primary" if current_mode == 'volume' else "secondary"
        ):
            st.session_state.top_items_ranking_mode = 'volume'
            st.rerun()
        
        if st.button(
            "LIQUIDITY",
            key="top_items_rank_liquidity",
            use_container_width=True,
            type="primary" if current_mode == 'liquidity' else "secondary"
        ):
            st.session_state.top_items_ranking_mode = 'liquidity'
            st.rerun()

        if st.button(
            "TOTAL SUPPLY",
            key="top_items_rank_total_supply",
            use_container_width=True,
            type="primary" if current_mode == 'total_supply' else "secondary"
        ):
            st.session_state.top_items_ranking_mode = 'total_supply'
            st.rerun()
        
        st.markdown(
            '<div class="otg-sidebar-section-gap"></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="otg-sidebar-label">PERIOD</div>', unsafe_allow_html=True)
        
        # Period buttons using native type parameter
        if st.button(
            "ALL",
            key="top_items_period_all",
            use_container_width=True,
            type="secondary" if current_mode == 'total_supply' else ("primary" if current_period == 'all' else "secondary"),
            disabled=current_mode == 'total_supply'
        ):
            st.session_state.top_items_period = 'all'
            st.rerun()
        
        if st.button(
            "30 DAY",
            key="top_items_period_30d",
            use_container_width=True,
            type="secondary" if current_mode == 'total_supply' else ("primary" if current_period == '30d' else "secondary"),
            disabled=current_mode == 'total_supply'
        ):
            st.session_state.top_items_period = '30d'
            st.rerun()
        
        if st.button(
            "7 DAY",
            key="top_items_period_7d",
            use_container_width=True,
            type="secondary" if current_mode == 'total_supply' else ("primary" if current_period == '7d' else "secondary"),
            disabled=current_mode == 'total_supply'
        ):
            st.session_state.top_items_period = '7d'
            st.rerun()
        
        if st.button(
            "1 DAY",
            key="top_items_period_1d",
            use_container_width=True,
            type="secondary" if current_mode == 'total_supply' else ("primary" if current_period == '1d' else "secondary"),
            disabled=current_mode == 'total_supply'
        ):
            st.session_state.top_items_period = '1d'
            st.rerun()
        
        st.markdown(
            '<div class="otg-sidebar-section-gap"></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="otg-sidebar-label">VIEW</div>', unsafe_allow_html=True)
        
        # View buttons using native type parameter
        if st.button(
            "CARDS",
            key="top_items_view_cards",
            use_container_width=True,
            type="primary" if current_view == 'cards' else "secondary"
        ):
            st.session_state.top_items_view = 'cards'
            st.rerun()
        
        if viewport_resolved and is_mobile:
            if st.button(
                "LEADERBOARD",
                key="top_items_view_chart",
                use_container_width=True,
                type="primary" if current_view == 'chart' else "secondary"
            ):
                st.session_state.top_items_view = 'chart'
                st.rerun()

        if viewport_resolved and not is_mobile:
            if st.button(
                "TABLE",
                key="top_items_view_table",
                use_container_width=True,
                type="primary" if current_view == 'table' else "secondary"
            ):
                st.session_state.top_items_view = 'table'
                st.rerun()
    
    info(f"Top Items sidebar: show_usd={show_usd}, ranking_mode={current_mode}, period={current_period}, view={current_view}")
    
    return {
        'show_usd': show_usd,
        'ranking_mode': current_mode,
        'period': current_period,
        'top_items_view': current_view
    }
