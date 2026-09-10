"""Presentation helpers for compact GUNZscope attribution."""

import base64
from functools import lru_cache
from pathlib import Path


LOGO_PATH = Path(__file__).resolve().parents[2] / "img" / "gunz_scope" / "logo_1.png"
SUPPLY_URL = "https://gunzscope.xyz/supply/"
TOOLTIP = "Data by GUNZscope"


@lru_cache(maxsize=1)
def logo_data_uri() -> str:
    try:
        encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    except OSError:
        return ""
    return f"data:image/png;base64,{encoded}"


def inline_logo(class_name: str = "gunzscope-inline-logo") -> str:
    src = logo_data_uri()
    if not src:
        return ""
    return (
        f'<a class="gunzscope-attribution-link" href="{SUPPLY_URL}" '
        f'target="_blank" rel="noopener noreferrer" title="{TOOLTIP}" '
        f'aria-label="{TOOLTIP}"><img class="{class_name}" src="{src}" '
        'alt="GUNZscope" style="display:inline-block;width:1em;height:1em;'
        'object-fit:contain;vertical-align:-0.12em;margin-left:0;"></a>'
    )
