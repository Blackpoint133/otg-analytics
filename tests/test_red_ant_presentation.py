import copy
import pandas as pd
import pytest
import gunzscope_supply as supply
from ui import top_items_overview as top

SHORTS = "cmmv915bi02pzw0omjj2dpp19"
PANTS = "cmmv8jles00jbw0omw3xc16j4"
PURPOSE = "opensea_sales presentation-only Supply canonicalization"

def rec(pid, name, value, asset="shared"):
    return {"provider_item_id": pid, "provider_item_name": name, "provider_rarity": "Epic", "provider_asset_key": asset, "raw_active_mints": value, "ranking_eligible": True, "status": "ok"}

def snap():
    return {"schema_version": 3, "source": "gunzscope", "provider_scope": {"exclude_zero": True, "exclude_base": False, "sort": "activeMints", "order": "asc"}, "provider_items": {"a": rec("a", "A", 10, "x"), SHORTS: rec(SHORTS, "Red Ant Shorts", 20), PANTS: rec(PANTS, "Red Ant Pants", 30), "b": rec("b", "B", 40, "x"), "c": rec("c", "C", 100)}, "catalog_mappings": {"Red Ant Shorts Epic": {"mapping_status": "DIRECT_CURRENT", "provider_item_id": SHORTS}, "Red Ant Pants Epic": {"mapping_status": "DIRECT_CURRENT", "provider_item_id": PANTS}}, "provider_item_conflicts": []}

def config(groups=None):
    return {"schema_version": 1, "purpose": PURPOSE, "rename_groups": groups if groups is not None else {"red_ant_shorts": {"canonical_provider_item_id": SHORTS, "member_provider_item_ids": [SHORTS, PANTS], "strategy": "sum_raw_supply", "reason": "reviewed"}}}

def test_config_is_strict_and_missing_or_malformed_fails_safe(tmp_path):
    assert supply._validate_supply_presentation_config(config())["red_ant_shorts"]["strategy"] == "sum_raw_supply"
    for groups in [{"g": {**config()["rename_groups"]["red_ant_shorts"], "canonical_provider_item_id": "z"}}, {"g": {**config()["rename_groups"]["red_ant_shorts"], "member_provider_item_ids": [SHORTS]}}, {"g": {**config()["rename_groups"]["red_ant_shorts"], "member_provider_item_ids": [SHORTS, SHORTS]}}, {"g": {**config()["rename_groups"]["red_ant_shorts"], "strategy": "merge"}}]:
        with pytest.raises(ValueError): supply._validate_supply_presentation_config(config(groups))
    assert supply.load_supply_presentation_config(str(tmp_path / "missing")) == {}
    bad = tmp_path / "bad"; bad.write_text("{", encoding="utf-8"); assert supply.load_supply_presentation_config(str(bad)) == {}

def test_presentation_index_explicit_nonmutating_and_asset_safe():
    data = snap(); before = copy.deepcopy(data["provider_items"]); idx = supply.build_v3_supply_presentation_index(data, config())
    assert idx["canonical_by_member_provider_id"][PANTS] == SHORTS and PANTS in idx["suppressed_provider_ids"] and SHORTS not in idx["suppressed_provider_ids"]
    assert idx["effective_supply_by_canonical_provider_id"][SHORTS] == 50 and data["provider_items"] == before
    raw = supply.build_v3_supply_presentation_index(data, config({})); assert len(raw["effective_supply_by_canonical_provider_id"]) == 5

def test_presentation_rank_is_raw_distinct_and_dense(monkeypatch):
    data = snap(); monkeypatch.setattr(supply, "read_supply_presentation_config", lambda: config()["rename_groups"])
    raw = {k: r["raw_active_mints"] for k, r in data["provider_items"].items()}; raw_rank = {v: i + 1 for i, v in enumerate(sorted(set(raw.values())))}
    assert raw_rank[20] == 2 and raw_rank[30] == 3
    assert supply.dense_supply_ranks(data) == {"a": 1, "b": 2, SHORTS: 3, "c": 4} and PANTS not in supply.dense_supply_ranks(data)

def test_item_analytics_aliases_share_effective_value_and_rank(monkeypatch):
    data = snap(); monkeypatch.setattr(supply, "read_supply_presentation_config", lambda: config()["rename_groups"])
    shorts = supply.get_item_supply_with_rank("Red Ant Shorts Epic", data); pants = supply.get_item_supply_with_rank("Red Ant Pants Epic", data)
    assert shorts[0]["supply"] == pants[0]["supply"] == 50 and shorts[1] == pants[1] == 3

def test_market_rows_keep_history_but_share_current_supply_metadata(monkeypatch):
    data = snap(); monkeypatch.setattr(top, "build_v3_supply_presentation_index", lambda d: supply.build_v3_supply_presentation_index(d, config()))
    rows = pd.DataFrame([{"item_key": "Red Ant Shorts Epic", "item_name": "Red Ant Shorts", "rarity": "Epic", "_provider_item_id": SHORTS, "volume": 11}, {"item_key": "Red Ant Pants Epic", "item_name": "Red Ant Pants", "rarity": "Epic", "_provider_item_id": PANTS, "volume": 22}])
    result = top._attach_supply_metadata(rows, data)
    assert result["volume"].tolist() == [11, 22] and result["_supply"].tolist() == [50, 50] and result["_supply_rank"].tolist() == [3, 3]

def test_total_supply_suppresses_only_configured_alias(monkeypatch):
    data = snap(); monkeypatch.setattr(top, "selected_supply_source", lambda: "v3"); monkeypatch.setattr(top, "read_snapshot_v3", lambda: data); monkeypatch.setattr(top, "load_items_index", lambda: ({}, type("D", (), {"success": True})())); monkeypatch.setattr(top, "build_v3_supply_presentation_index", lambda d: supply.build_v3_supply_presentation_index(d, config()))
    rows = top._load_global_total_supply_candidates()
    assert len(rows) == 4 and (rows["_provider_item_id"] == SHORTS).sum() == 1 and not (rows["_provider_item_id"] == PANTS).any()
