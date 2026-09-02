"""
technical diagnostic text technical diagnostic text technical diagnostic text.

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
"""

from typing import Dict, Optional, Any
import streamlit as st

from logging_compat import info

from search_utils import find_item_in_meta


def initialize_selected_item(items_index: Dict[str, Any]):
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text URL technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    technical diagnostic text st.session_state.selected_item.
    
    Args:
        items_index: technical diagnostic text item_key -> item_record technical diagnostic text technical diagnostic text
    """
    if 'selected_item' not in st.session_state:
        # technical implementation note technical implementation note URL technical implementation note
        item_raw = st.query_params.get('item')
        if item_raw:
            if isinstance(item_raw, list):
                potential_item = item_raw[0]
            else:
                potential_item = item_raw
            selected_item = find_item_in_meta(potential_item, items_index)
            info(f"[INIT] technical diagnostic text technical diagnostic text URL: '{potential_item}' → '{selected_item}'")
        else:
            selected_item = None
            info(f"[INIT] technical diagnostic text item technical diagnostic text technical diagnostic text technical diagnostic text URL")
        
        # technical implementation note technical implementation note URL technical implementation note technical implementation note, technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
        if not selected_item and items_index:
            selected_item = sorted(items_index.keys())[0]
            info(f"[INIT AUTO SELECT] technical diagnostic text technical diagnostic text technical diagnostic text: '{selected_item}'")
        
        st.session_state.selected_item = selected_item
        st.session_state.item_initial_event_type = (
            "initial_explicit" if selected_item and item_raw and selected_item == potential_item else "initial_default"
        )


def prepare_filter_state(filter_dict: Optional[Dict]) -> Dict:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Args:
        filter_dict: technical diagnostic text technical diagnostic text technical diagnostic text (selected_item, item_record, show_volume, show_usd)
    
    Returns:
        dict: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
        
    Raises:
        ValueError: technical diagnostic text required technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    """
    if not filter_dict:
        raise ValueError("technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text None")
    
    required_keys = {'selected_item', 'item_record', 'show_volume', 'show_usd'}
    missing_keys = required_keys - set(filter_dict.keys())
    
    if missing_keys:
        raise ValueError(f"technical diagnostic text technical diagnostic text technical diagnostic text: {missing_keys}")
    
    # technical implementation note technical implementation note
    if not isinstance(filter_dict['show_volume'], bool):
        filter_dict['show_volume'] = bool(filter_dict['show_volume'])
    if not isinstance(filter_dict['show_usd'], bool):
        filter_dict['show_usd'] = bool(filter_dict['show_usd'])
    if 'show_trend_line' in filter_dict and not isinstance(filter_dict['show_trend_line'], bool):
        filter_dict['show_trend_line'] = bool(filter_dict['show_trend_line'])
    
    return filter_dict
