"""Viewport detection helper for item-only responsive chart layout."""

from pathlib import Path
from typing import Any, Dict, Optional

import streamlit.components.v1 as components


_COMPONENT_DIR = Path(__file__).parent / "viewport_component"
_viewport_component = components.declare_component(
    "otg_viewport",
    path=str(_COMPONENT_DIR),
)


def get_viewport_info(key: str = "otg_viewport") -> Optional[Dict[str, Any]]:
    """Return browser viewport information, or None until the component responds."""
    value = _viewport_component(default=None, key=key)
    if not isinstance(value, dict):
        return None

    width = value.get("width")
    is_mobile = value.get("isMobile")
    if not isinstance(width, (int, float)) or isinstance(width, bool):
        return None
    if not isinstance(is_mobile, bool):
        is_mobile = width <= 768

    return {
        "width": int(width),
        "isMobile": is_mobile,
    }
