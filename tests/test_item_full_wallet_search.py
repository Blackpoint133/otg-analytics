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
    assert 'render_item_wallet_search' in item_wallet
    assert 'key="item_wallet_search"' in item_wallet
    assert '_match_existing_wallet' in source

    assert 'render_item_search' in source


def test_item_select_filters_keeps_one_shared_spacer_and_trader_selector_is_unchanged():
    source = (APP / "ui" / "sidebar.py").read_text(encoding="utf-8")
    selectbox = source.index('key="item_select_item"')
    filters = source.index('<div class="otg-sidebar-label">FILTERS</div>', selectbox)
    assert source[selectbox:filters].count("otg-sidebar-section-gap") == 1
    assert 'key="trader_search"' in source

def test_item_component_has_selected_marker_and_dimensions():
    source = (APP / "ui" / "item_search_component" / "index.html").read_text()
    assert "selected-diamond" in source and "width:8px;height:8px" in source
    assert "selectedMode=" in source and "rarity_color" in source

def test_item_component_hides_marker_outside_selected_mode():
    source = (APP / "ui" / "item_search_component" / "index.html").read_text()
    assert ".selected .selected-diamond{display:block}" in source
    assert ".selected-diamond{display:none" in source

def test_item_component_has_one_shared_sorted_match_helper():
    source = (APP / "ui" / "item_search_component" / "index.html").read_text()
    assert source.count("function matches(") == 1
    assert "localeCompare" in source and "slice(0,10)" in source
    assert "matches(browsing?'':q.value)" in source

def test_item_keyboard_uses_shared_matches():
    source = (APP / "ui" / "item_search_component" / "index.html").read_text()
    assert "ArrowDown" in source and "ArrowUp" in source and "Enter" in source and "Escape" in source
    assert "m=matches(browsing?'':q.value)" in source

def test_item_component_uses_safe_text_and_json_protocol():
    source = (APP / "ui" / "item_search_component" / "index.html").read_text()
    assert "textContent" in source and "dataType:'json'" in source

def test_item_component_selected_render_restores_marker():
    source = (APP / "ui" / "item_search_component" / "index.html").read_text()
    assert "a.selected_item" in source and "records.find(function(r){return r.item_key===a.selected_item}" in source

def test_item_component_result_marker_uses_record_color():
    source = (APP / "ui" / "item_search_component" / "index.html").read_text()
    assert "d.style.background=r.rarity_color||'#fff'" in source

def test_item_component_selection_event_is_single_action():
    source = (APP / "ui" / "item_search_component" / "index.html").read_text()
    assert "action:'select'" in source

def test_item_control_visual_contract_remains_34px_red_black_square():
    source = (APP / "ui" / "item_search_component" / "index.html").read_text()
    assert "height:34px" in source and "background:#080808" in source and "border:1px solid #ff003a" in source

def test_top_trader_component_file_is_separate_and_untouched():
    trader = (APP / "ui" / "trader_search_component" / "index.html").read_text()
    item = (APP / "ui" / "item_search_component" / "index.html").read_text()
    assert trader != item and "otg_item_search" not in trader
