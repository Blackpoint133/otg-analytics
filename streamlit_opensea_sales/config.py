"""
technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text, technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
"""

from pathlib import Path
import base64

# ════════════════════════════════════════════════════════════════════════════════
# technical implementation note technical implementation note
# ════════════════════════════════════════════════════════════════════════════════
ITEMS_PER_PAGE = 10
FONT_FAMILY = "'PP Supply Sans', 'Space Mono', monospace, sans-serif"

# ════════════════════════════════════════════════════════════════════════════════
# MARKET OVERVIEW CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════════
# Phase 3B: Switch to enriched market overview with historical USD pricing
# When True: Uses market_overview_enriched/ with pre-calculated historical USD values
# When False: Uses market_overview/ (original data without USD enrichment)
USE_ENRICHED_MARKET_OVERVIEW = True

# ════════════════════════════════════════════════════════════════════════════════
# technical implementation note technical implementation note
# ════════════════════════════════════════════════════════════════════════════════
PAGE_TITLE = "Off The Grid"
PAGE_LAYOUT = "wide"

# ════════════════════════════════════════════════════════════════════════════════
# technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
# ════════════════════════════════════════════════════════════════════════════════
def get_app_root_dir() -> Path:
    """technical documentation technical documentation technical documentation technical documentation."""
    return Path(__file__).parent


def get_assets_dir() -> Path:
    """technical documentation technical documentation technical documentation technical documentation technical documentation technical documentation."""
    return get_app_root_dir() / "assets"


def get_data_dir() -> Path:
    """technical documentation technical documentation technical documentation technical documentation technical documentation technical documentation."""
    return get_app_root_dir() / "data_opensea_sales"


def get_assets_loading_image() -> Path:
    """technical documentation technical documentation technical documentation technical documentation technical documentation."""
    return get_app_root_dir().parent / "img" / "logo.png"


def get_assets_logo_image() -> Path:
    """technical documentation technical documentation technical documentation technical documentation technical documentation."""
    return get_app_root_dir().parent / "img" / "logo.png"


def get_icon_image() -> Path:
    """technical documentation technical documentation technical documentation technical documentation technical documentation."""
    return get_assets_dir() / "icon.png"


def get_page_icon() -> str:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text base64 technical diagnostic text st.set_page_config().
    
    Returns:
        str: Base64 technical diagnostic text technical diagnostic text technical diagnostic text emoji fallback
    """
    try:
        icon_path = get_icon_image()
        if icon_path.exists():
            with open(icon_path, 'rb') as f:
                icon_data = base64.b64encode(f.read()).decode()
            # Streamlit technical implementation note technical implementation note data URLs technical implementation note technical implementation note page_icon
            # technical implementation note emoji technical implementation note fallback
            return "🔱"
        return "🔱"
    except Exception:
        return "🔱"


# ════════════════════════════════════════════════════════════════════════════════
# technical implementation note technical implementation note
# ════════════════════════════════════════════════════════════════════════════════
OPENSEA_COLLECTION_URL = "https://opensea.io/collection/off-the-grid"
EPIC_GAMES_URL = "https://store.epicgames.com/en-US/p/off-the-grid-7e3cc5"
TWITTER_URL = "https://x.com/blackpoint_team"
OPENSEA_ICON_URL = "https://static.seadn.io/logos/Logomark-White.svg"
BLACKPOINT_LOGO_URL = "https://i.postimg.cc/L5wFLwgw/NEW-LOGO.png"
