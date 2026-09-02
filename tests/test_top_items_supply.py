import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

from gunzscope_supply import ATTRIBUTION
import ui.top_items_overview as top_items_overview
from ui.top_items_overview import _format_rank, _prepare_total_supply_data


def snapshot(records):
    return {
        "schema_version": 1,
        "source": "gunzscope",
        "snapshot_fetched_at": "2026-09-02T00:00:00+00:00",
        "attribution": ATTRIBUTION,
        "items": records,
    }


def row(key):
    return {"item_key": key, "item_name": key, "rarity": "Epic", "rank": 99, "volume_gun": 1}


def item(supply, status="ok"):
    return {"supply": supply, "status": status}


def test_total_supply_sorts_ascending_with_item_key_tiebreak():
    data = pd.DataFrame([row("b"), row("a"), row("c")])
    snap = snapshot({"a": item(10), "b": item(10), "c": item(20)})
    result = _prepare_total_supply_data(data, snap)
    assert result["item_key"].tolist() == ["a", "b", "c"]


def test_zero_supply_is_first_and_valid():
    result = _prepare_total_supply_data(pd.DataFrame([row("one"), row("zero")]), snapshot({"one": item(1), "zero": item(0)}))
    assert result.iloc[0]["item_key"] == "zero" and result.iloc[0]["_supply"] == 0


def test_missing_supply_is_last_and_not_zero():
    result = _prepare_total_supply_data(pd.DataFrame([row("missing"), row("known")]), snapshot({"missing": {"status": "unavailable"}, "known": item(4)}))
    assert result.iloc[-1]["item_key"] == "missing" and pd.isna(result.iloc[-1]["_supply"])


def test_global_dense_rank_is_reused():
    result = _prepare_total_supply_data(pd.DataFrame([row("a"), row("b")]), snapshot({"a": item(7), "b": item(7), "other": item(8)}))
    assert result["_supply_rank"].tolist() == [1, 1]


def test_missing_snapshot_is_safe():
    result = _prepare_total_supply_data(pd.DataFrame([row("a")]), {})
    assert pd.isna(result.iloc[0]["_supply"]) and pd.isna(result.iloc[0]["_supply_rank"])


def test_invalid_snapshot_status_is_missing():
    result = _prepare_total_supply_data(pd.DataFrame([row("a")]), snapshot({"a": item(-1), "b": item(2)}))
    assert pd.isna(result.iloc[0]["_supply"])


def test_rank_formatter_is_na_safe():
    assert _format_rank(None) == "-"


def test_period_does_not_change_supply_values():
    data = pd.DataFrame([row("a"), row("b")])
    snap = snapshot({"a": item(2), "b": item(8)})
    for _period in ("all", "30d", "7d", "1d"):
        assert _prepare_total_supply_data(data, snap)["_supply"].tolist() == [2, 8]


def test_old_market_rank_does_not_drive_supply_order():
    data = pd.DataFrame([dict(row("a"), rank=1), dict(row("b"), rank=2)])
    result = _prepare_total_supply_data(data, snapshot({"a": item(20), "b": item(5)}))
    assert result["item_key"].tolist() == ["b", "a"]


def test_global_candidate_loader_uses_complete_catalog(monkeypatch):
    catalog = {
        "a": {"item_key": "a", "display_name": "A", "rarity": "Common"},
        "b": {"item_key": "b", "display_name": "B", "rarity": "Rare"},
        "c": {"item_key": "c", "display_name": "C", "rarity": "Epic"},
    }
    monkeypatch.setattr(
        top_items_overview,
        "load_items_index",
        lambda: (catalog, SimpleNamespace(success=True)),
    )
    result = top_items_overview._load_global_total_supply_candidates()
    assert result["item_key"].tolist() == ["a", "b", "c"]
    assert len(result) == len(catalog)


def test_supply_limit_is_applied_after_global_sort():
    data = pd.DataFrame([row("a"), row("b"), row("c")])
    snap = snapshot({"a": item(30), "b": item(10), "c": item(20)})
    result = _prepare_total_supply_data(data, snap, limit=2)
    assert result["item_key"].tolist() == ["b", "c"]


def test_sidebar_has_fourth_button_and_disabled_period_policy():
    source = (APP / "ui" / "sidebar.py").read_text(encoding="utf-8")
    assert '"TOTAL SUPPLY"' in source
    assert "key=\"top_items_rank_total_supply\"" in source
    assert "st.session_state.top_items_ranking_mode = 'total_supply'" in source
    assert "disabled=current_mode == 'total_supply'" in source
    assert "opacity: 0.42" in source


def test_total_supply_path_is_global_and_has_no_live_client_import():
    source = (APP / "ui" / "top_items_overview.py").read_text(encoding="utf-8")
    assert "_load_global_total_supply_candidates()" in source
    assert "source_ranking_mode" not in source
    assert "gunzscope_client" not in source


def test_total_supply_header_is_period_independent_and_table_columns_are_reachable():
    source = (APP / "ui" / "top_items_overview.py").read_text(encoding="utf-8")
    assert "GLOBAL CURRENT SUPPLY" in source
    assert "<th>Total Supply</th><th>Supply Rank</th>" in source
    assert "_render_top_items_table_view(display_data" in source


def test_market_period_loader_and_usd_resort_remain_in_source():
    source = (APP / "ui" / "top_items_overview.py").read_text(encoding="utf-8")
    assert "ranking_mode=ranking_mode" in source
    assert "ranking_mode == 'volume' and show_usd" in source
    assert "display_data = display_data.sort_values('volume_usd', ascending=False)" in source
