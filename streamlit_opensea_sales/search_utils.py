"""
technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
"""

from typing import Dict, Optional, Any
from urllib.parse import unquote_plus

from logging_compat import info


def normalize_string(s: str) -> str:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Args:
        s: technical diagnostic text technical diagnostic text
    
    Returns:
        str: technical diagnostic text technical diagnostic text
    """
    return ' '.join(s.split()).lower()


def normalize_quotes(s: str) -> str:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Args:
        s: technical diagnostic text technical diagnostic text
    
    Returns:
        str: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    """
    s = s.replace('"', '"').replace('"', '"').replace('"', '"')
    s = s.replace('"""', '"').replace('""', '"')
    return normalize_string(s)


def find_item_in_meta(search_term: Optional[str], items_index: Dict[str, Any]) -> Optional[str]:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text items_index technical diagnostic text technical diagnostic text:
    1. technical diagnostic text technical diagnostic text item_key
    2. technical diagnostic text technical diagnostic text (lowercase, trim spaces)
    3. technical diagnostic text technical diagnostic text technical diagnostic text display_name
    4. technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    
    Args:
        search_term: technical diagnostic text technical diagnostic text
        items_index: technical diagnostic text item_key -> item_record
    
    Returns:
        Optional[str]: item_key technical diagnostic text technical diagnostic text technical diagnostic text None
    """
    if not search_term:
        return None
    
    search_term = unquote_plus(search_term).strip()
    info(f"[SEARCH] technical diagnostic text: '{search_term}'")
    
    # technical implementation note 1: technical implementation note technical implementation note item_key
    if search_term in items_index:
        info(f"[SEARCH] technical diagnostic text technical diagnostic text technical diagnostic text: '{search_term}'")
        return search_term
    
    search_normalized = normalize_string(search_term)
    search_normalized_quotes = normalize_quotes(search_term)
    
    info(f"[SEARCH] technical diagnostic text technical diagnostic text: '{search_normalized}'")
    
    # technical implementation note 2: technical implementation note technical implementation note item_key
    for item_key in items_index.keys():
        key_normalized = normalize_string(item_key)
        key_normalized_quotes = normalize_quotes(item_key)
        
        if (key_normalized == search_normalized or 
            key_normalized_quotes == search_normalized_quotes):
            info(f"[SEARCH] technical diagnostic text technical diagnostic text technical diagnostic text: '{search_term}' -> '{item_key}'")
            return item_key
    
    # technical implementation note 3: technical implementation note technical implementation note display_name
    search_name = search_term.rsplit(' ', 1)[0] if ' ' in search_term else search_term
    search_name_normalized = normalize_string(search_name)
    search_name_normalized_quotes = normalize_quotes(search_name)
    
    info(f"[SEARCH] technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text: '{search_name_normalized}'")
    
    for item_key, item_record in items_index.items():
        display_name = item_record.get('display_name', item_key)
        display_name_normalized = normalize_string(display_name)
        display_name_normalized_quotes = normalize_quotes(display_name)
        
        if (display_name_normalized == search_name_normalized or 
            display_name_normalized_quotes == search_name_normalized_quotes):
            info(f"[SEARCH] technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text: '{search_term}' -> '{item_key}'")
            return item_key
    
    info(f"[SEARCH] technical diagnostic text technical diagnostic text technical diagnostic text: '{search_term}'")
    if items_index:
        info(f"[SEARCH] technical diagnostic text technical diagnostic text (technical diagnostic text 5): {list(items_index.keys())[:5]}")
    
    return None
