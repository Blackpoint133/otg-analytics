from pathlib import Path
import importlib.util
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "streamlit_opensea_sales"))

spec = importlib.util.spec_from_file_location("sidebar", Path(__file__).parents[1] / "streamlit_opensea_sales" / "ui" / "sidebar.py")
sidebar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sidebar)


def test_trader_search_option_contains_name_short_and_full_wallet():
    wallet = "0x31c5cda12853bec9537d73e434169c899a0a554d"
    options, mapping = sidebar._trader_search_options(
        [{"wallet": wallet}], {"profiles": {wallet: {"display_name": "B_rasengan"}}, "fallback_names": {}}
    )
    assert options[1].startswith("B_rasengan  ")
    assert sidebar._short_wallet_label(wallet) in options[1]
    assert wallet in options[1]
    assert mapping[options[1]] == wallet


def test_trader_search_options_keep_similar_names_unique():
    rows = [{"wallet": "0x1111111111111111111111111111111111111111"}, {"wallet": "0x2222222222222222222222222222222222222222"}]
    options, mapping = sidebar._trader_search_options(rows, {"profiles": {}, "fallback_names": {w["wallet"]: "Trader" for w in rows}})
    assert len(set(options[1:])) == 2
    assert {mapping[x] for x in options[1:]} == {w["wallet"] for w in rows}


def test_all_traders_maps_to_none_and_selector_is_not_freeform():
    source = (Path(__file__).parents[1] / "streamlit_opensea_sales" / "ui" / "sidebar.py").read_text(encoding="utf-8")
    assert '"ALL TRADERS"' in source
    assert "accept_new_options=True" not in source[source.index("def render_trader_sidebar_controls"):]
