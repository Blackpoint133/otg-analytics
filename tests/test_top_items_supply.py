import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

from gunzscope_supply import ATTRIBUTION
import ui.top_items_overview as top_items_overview
from ui.top_items_overview import (
    _attach_canonical_item_keys,
    _attach_supply_metadata,
    _enrich_with_all_time_market_metrics,
    _format_rank,
    _prepare_total_supply_data,
)


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
    data = pd.DataFrame([
        {"item_key": "a", "item_name": "a", "rarity": "Epic", "volume_gun": 1},
        {"item_key": "b", "item_name": "b", "rarity": "Epic", "volume_gun": 1},
    ])
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
    assert "<th>Total Supply</th>" in source
    assert "<th>Supply Rank</th>" in source
    assert "_render_top_items_table_view(display_data" in source


def test_market_period_loader_and_usd_resort_remain_in_source():
    source = (APP / "ui" / "top_items_overview.py").read_text(encoding="utf-8")
    assert "ranking_mode=ranking_mode" in source
    assert "ranking_mode == 'volume' and show_usd" in source
    assert "display_data = display_data.sort_values('volume_usd', ascending=False)" in source


def test_total_supply_render_does_not_require_market_rank(monkeypatch):
    captured = {}
    data = pd.DataFrame([
        {"item_key": "a", "item_name": "a", "rarity": "Epic", "volume_gun": 1},
        {"item_key": "b", "item_name": "b", "rarity": "Epic", "volume_gun": 1},
    ])
    snap = snapshot({"a": item(2), "b": item(5)})
    monkeypatch.setattr(top_items_overview.mda, "get_market_data_status", lambda: {"status": "OK"})
    monkeypatch.setattr(top_items_overview.mda, "_get_cache_buster", lambda: "test")
    monkeypatch.setattr(top_items_overview, "_load_global_total_supply_candidates", lambda: data)
    monkeypatch.setattr(top_items_overview, "_load_all_time_market_metrics", lambda: None)
    monkeypatch.setattr(top_items_overview, "read_current_snapshot", lambda: snap)
    monkeypatch.setattr(top_items_overview.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        top_items_overview,
        "_render_top_items_card_view",
        lambda frame, **kwargs: captured.setdefault("frame", frame.copy()),
    )
    top_items_overview._render_top_items_section("test", ranking_mode="total_supply", top_items_view="cards")
    result = captured["frame"]
    assert result["display_rank"].tolist() == [1, 2]


def test_market_modes_keep_market_rank_as_display_rank(monkeypatch):
    source = (APP / "ui" / "top_items_overview.py").read_text(encoding="utf-8")
    assert "display_data['display_rank'] = display_data['_supply_rank']" in source
    assert "display_data['display_rank'] = display_data['rank']" in source
    assert "ranking_mode == 'volume' and show_usd" in source


def market_row(name, rarity="Common", **values):
    base = {"item_name": name, "rarity": rarity, "item_key": "provider|key"}
    base.update(values)
    return base


def test_exact_name_rarity_bridge_enriches_without_raw_item_key_join():
    catalog = pd.DataFrame([{"item_key": "catalog-key", "item_name": "A", "rarity": "Common"}])
    market = pd.DataFrame([market_row("A", volume_gun=12, market_strength_score=3.5)])
    result = _enrich_with_all_time_market_metrics(catalog, market)
    assert result.iloc[0]["item_key"] == "catalog-key"
    assert result.iloc[0]["volume_gun"] == 12
    assert result.iloc[0]["market_strength_score"] == 3.5


def test_exact_bridge_transfers_market_image_url_not_raw_market_key():
    catalog = pd.DataFrame([{"item_key": "catalog-key", "item_name": "A", "rarity": "Common"}])
    market = pd.DataFrame([market_row("A", image_url="https://cdn.example/a.png")])
    result = _enrich_with_all_time_market_metrics(catalog, market)
    assert result.iloc[0]["item_key"] == "catalog-key"
    assert result.iloc[0]["image_url"] == "https://cdn.example/a.png"


def test_missing_market_image_preserves_empty_image_fallback():
    catalog = pd.DataFrame([{"item_key": "catalog-key", "item_name": "A", "rarity": "Common"}])
    market = pd.DataFrame([market_row("A", image_url=pd.NA)])
    result = _enrich_with_all_time_market_metrics(catalog, market)
    assert pd.isna(result.iloc[0]["image_url"])
    assert top_items_overview._normalize_top_item_image_url(result.iloc[0]["image_url"]) == ""


def test_image_renderer_paths_use_shared_image_url_helper():
    source = (APP / "ui" / "top_items_overview.py").read_text(encoding="utf-8")
    assert source.count("_normalize_top_item_image_url") >= 3
    assert "'image_url'," in source


def test_bridge_rejects_duplicate_catalog_identity():
    catalog = pd.DataFrame([
        {"item_key": "a", "item_name": "A", "rarity": "Common"},
        {"item_key": "b", "item_name": "A", "rarity": "Common"},
    ])
    with pytest.raises(ValueError, match="duplicate catalog"):
        _enrich_with_all_time_market_metrics(catalog, pd.DataFrame([market_row("A")] ))


def test_bridge_rejects_duplicate_market_identity():
    catalog = pd.DataFrame([{"item_key": "a", "item_name": "A", "rarity": "Common"}])
    market = pd.DataFrame([market_row("A"), market_row("A")])
    with pytest.raises(ValueError, match="duplicate market"):
        _enrich_with_all_time_market_metrics(catalog, market)


def test_missing_market_row_is_preserved_for_supply_display():
    catalog = pd.DataFrame([{"item_key": "a", "item_name": "A", "rarity": "Common"}])
    result = _enrich_with_all_time_market_metrics(catalog, pd.DataFrame([market_row("B")]))
    assert len(result) == 1 and pd.isna(result.iloc[0]["volume_gun"])


def test_market_rows_keep_order_while_supply_joins_by_canonical_key(monkeypatch):
    catalog = {"catalog-a": {"display_name": "A", "rarity": "Common"}, "catalog-b": {"display_name": "B", "rarity": "Common"}}
    monkeypatch.setattr(top_items_overview, "load_items_index", lambda: (catalog, SimpleNamespace(success=True)))
    rows = pd.DataFrame([market_row("B"), market_row("A")])
    joined = _attach_supply_metadata(_attach_canonical_item_keys(rows), snapshot({"catalog-a": item(2), "catalog-b": item(9)}))
    assert joined["item_name"].tolist() == ["B", "A"]
    assert joined["_supply"].tolist() == [9, 2]
