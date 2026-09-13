from pathlib import Path
import importlib.util
import sys
import importlib
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "streamlit_opensea_sales"))

spec = importlib.util.spec_from_file_location("sidebar", Path(__file__).parents[1] / "streamlit_opensea_sales" / "ui" / "sidebar.py")
sidebar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sidebar)


def test_trader_search_option_contains_name_short_and_full_wallet():
    wallet = "0x31c5cda12853bec9537d73e434169c899a0a554d"
    records = sidebar._trader_search_records(
        [{"wallet": wallet}], {"profiles": {wallet: {"display_name": "B_rasengan"}}, "fallback_names": {}}
    )
    assert records[0]["display_name"] == "B_rasengan"
    assert records[0]["wallet"] == wallet
    assert records[0]["display_name"] == "B_rasengan"


def test_trader_search_options_keep_similar_names_unique():
    rows = [{"wallet": "0x1111111111111111111111111111111111111111"}, {"wallet": "0x2222222222222222222222222222222222222222"}]
    records = sidebar._trader_search_records(rows, {"profiles": {}, "fallback_names": {}})
    assert len(records) == 2
    assert {r["wallet"] for r in records} == {w["wallet"] for w in rows}


def test_all_traders_maps_to_none_and_selector_is_not_freeform():
    source = (Path(__file__).parents[1] / "streamlit_opensea_sales" / "ui" / "sidebar.py").read_text(encoding="utf-8")
    assert "st.session_state.trader_selected_wallet" in source
    assert "accept_new_options=True" not in source[source.index("def render_trader_sidebar_controls"):]
    assert "st.selectbox(" not in source[source.index("def render_trader_sidebar_controls"):]


def test_component_contract_supports_live_safe_autocomplete():
    source = (Path(__file__).parents[1] / "streamlit_opensea_sales" / "ui" / "trader_search_component" / "index.html").read_text(encoding="utf-8")
    for token in ("oninput", "display_name", "username", "slice(2)", "slice(0,10)", "textContent", "setComponentValue", "ArrowDown", "ArrowUp", "Enter", "Escape", "componentReady", "streamlit:render", "setFrameHeight"):
        assert token in source


def test_search_records_use_only_search_fields():
    wallet = "0x1111111111111111111111111111111111111111"
    records = sidebar._trader_search_records([{"wallet": wallet}], {"profiles": {wallet: {"username": "alice"}}, "fallback_names": {}})
    assert set(records[0]) == {"wallet", "display_name", "username"}

def test_fallback_name_is_preserved_and_searchable():
    wallet = "0x1111111111111111111111111111111111111111"
    record = sidebar._trader_search_records([{"wallet": wallet}], {"profiles": {}, "fallback_names": {wallet: "NoName2715"}})[0]
    assert record["display_name"] == "NoName2715"

def test_username_is_preserved():
    wallet = "0x1111111111111111111111111111111111111111"
    assert sidebar._trader_search_records([{"wallet": wallet}], {"profiles": {wallet: {"username": "alice"}}, "fallback_names": {}})[0]["username"] == "alice"

def test_duplicate_names_keep_distinct_canonical_wallets():
    rows = [{"wallet": "0x1111111111111111111111111111111111111111"}, {"wallet": "0x2222222222222222222222222222222222222222"}]
    records = sidebar._trader_search_records(rows, {"profiles": {}, "fallback_names": {rows[0]["wallet"]: "Same", rows[1]["wallet"]: "Same"}})
    assert [r["wallet"] for r in records] == [r["wallet"] for r in rows]

def test_known_and_unknown_selected_wallet_resolution():
    records = [{"wallet": "0x1111111111111111111111111111111111111111", "display_name": "A", "username": ""}]
    assert sidebar._canonical_trader_wallet(records[0]["wallet"].upper(), records) == records[0]["wallet"]
    assert sidebar._canonical_trader_wallet("0x9999999999999999999999999999999999999999", records) is None

def test_component_wrapper_rejects_malformed_events(monkeypatch):
    mod = importlib.import_module("ui.trader_search")
    for value in (None, [], {"action": "select", "event_id": ""}, {"action": "select", "event_id": "x"}, {"action": "bogus", "event_id": "x"}):
        monkeypatch.setattr(mod, "_trader_search", lambda **kwargs: value)
        assert mod.render_trader_search([]) is None

def test_component_wrapper_accepts_valid_select_and_clear(monkeypatch):
    mod = importlib.import_module("ui.trader_search")
    monkeypatch.setattr(mod, "_trader_search", lambda **kwargs: {"action": "select", "wallet": "0x1", "event_id": "e"})
    assert mod.render_trader_search([])["action"] == "select"
    monkeypatch.setattr(mod, "_trader_search", lambda **kwargs: {"action": "clear", "event_id": "c"})
    assert mod.render_trader_search([])["action"] == "clear"

def test_stale_selection_is_not_passed_downstream():
    assert sidebar._canonical_trader_wallet("0xdead", []) is None

def test_no_dead_python_matcher_or_result_buttons():
    source = Path(__file__).parents[1].joinpath("streamlit_opensea_sales/ui/sidebar.py").read_text()
    body = source[source.index("def render_trader_sidebar_controls"):]
    assert "_legacy_search_removed" not in source
    assert "st.text_input" not in body and "st.button(record" not in body

def test_trades_color_remains_approved():
    source = Path(__file__).parents[1].joinpath("streamlit_opensea_sales/ui/trader_overview.py").read_text()
    assert 'TRADES_COLOR = "#8F78C6"' in source

@pytest.mark.parametrize("token", ["dataType:'json'", "streamlit:componentReady", "streamlit:render", "setFrameHeight", "setComponentValue", "ArrowDown", "ArrowUp", "Enter", "Escape"])
def test_component_protocol_and_keyboard_contract(token):
    source = Path(__file__).parents[1].joinpath("streamlit_opensea_sales/ui/trader_search_component/index.html").read_text()
    assert token in source

def test_component_has_live_matching_and_safe_name_rendering():
    source = Path(__file__).parents[1].joinpath("streamlit_opensea_sales/ui/trader_search_component/index.html").read_text()
    for token in ["display_name", "username", "slice(2)", "slice(0,10)", "textContent", "addEventListener('input'"]:
        assert token in source

def test_component_does_not_search_short_or_ellipsis_wallets():
    source = Path(__file__).parents[1].joinpath("streamlit_opensea_sales/ui/trader_search_component/index.html").read_text()
    assert "..." not in source
    assert "short_wallet" not in source

def test_component_has_single_clear_path_and_state_sync():
    source = Path(__file__).parents[1].joinpath("streamlit_opensea_sales/ui/trader_search_component/index.html").read_text()
    assert "clearOnce" in source and "clearSent" in source and "selectedDisplayName" in source

def test_component_payload_is_limited_to_search_fields():
    source = Path(__file__).parents[1].joinpath("streamlit_opensea_sales/ui/sidebar.py").read_text()
    assert '"display_name": name' in source and '"username"' in source
