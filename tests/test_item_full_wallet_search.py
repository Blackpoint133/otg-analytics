from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
APP = ROOT / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

from ui.sidebar import _match_existing_wallet


WALLET = "0x6891cf9d5a270331075bee95abcdef1234561d8c"


def test_match_existing_wallet_is_exact_case_insensitive_and_canonical():
    options = [WALLET]
    assert _match_existing_wallet(WALLET, options) == WALLET
    assert _match_existing_wallet(WALLET.upper(), options) == WALLET
    assert _match_existing_wallet(f"  {WALLET}  ", options) == WALLET


def test_match_existing_wallet_rejects_unknown_prefix_all_and_none():
    options = [WALLET]
    assert _match_existing_wallet("0x0000000000000000000000000000000000000000", options) is None
    assert _match_existing_wallet("0x6891", options) is None
    assert _match_existing_wallet("ALL WALLETS", options) is None
    assert _match_existing_wallet(None, options) is None


def test_item_wallet_selector_accepts_full_values_but_keeps_compact_labels():
    source = (APP / "ui" / "sidebar.py").read_text(encoding="utf-8")
    item_wallet = source.split('key="item_wallet_filter"', 1)[1].split('highlight_wallet =', 1)[0]
    assert 'render_trader_search' in item_wallet
    assert 'key="item_wallet_search"' in item_wallet
    assert '_match_existing_wallet' in source

    assert 'render_item_search' in source


def test_item_select_filters_keeps_one_shared_spacer_and_trader_selector_is_unchanged():
    source = (APP / "ui" / "sidebar.py").read_text(encoding="utf-8")
    selectbox = source.index('key="item_select_item"')
    filters = source.index('<div class="otg-sidebar-label">FILTERS</div>', selectbox)
    assert source[selectbox:filters].count("otg-sidebar-section-gap") == 1
    assert 'key="trader_search"' in source
