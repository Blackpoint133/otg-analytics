import pytest

import gunzscope_supply as supply


def v3_record(pid="x", supply_value=10, eligible=True, status=None):
    return {
        "provider_item_id": pid, "provider_item_name": "Item", "provider_rarity": "Epic",
        "raw_active_mints": supply_value, "ranking_eligible": eligible,
        "status": status or ("ok" if eligible else "catalog_only"),
        **({} if eligible else {"scope_reason": "catalog_only_outside_current_rankings"}),
    }


def v3_payload(record=None):
    return {"schema_version": 3, "source": "gunzscope",
            "provider_scope": {"exclude_zero": True, "exclude_base": False, "sort": "activeMints", "order": "asc"},
            "provider_items": {"x": record or v3_record()},
            "catalog_mappings": {"Item Epic": {"mapping_status": "DIRECT_CURRENT", "provider_item_id": "x"}},
            "provider_item_conflicts": []}


def test_v3_failover_to_v2(monkeypatch):
    monkeypatch.setenv("GUNZSCOPE_SUPPLY_SOURCE", "v3")
    monkeypatch.setattr(supply, "read_snapshot_v3", lambda: None)
    monkeypatch.setattr(supply, "read_shadow_v2", lambda: {"schema_version": 2})
    assert supply.selected_supply_source() == "v2"


@pytest.mark.parametrize(("requested", "v3", "v2", "expected"), [
    ("v3", {"schema_version": 3}, {"schema_version": 2}, "v3"),
    ("v3", None, {"schema_version": 2}, "v2"),
    ("v3", None, None, "v1"),
    ("v2", {"schema_version": 3}, {"schema_version": 2}, "v2"),
    ("v2", {"schema_version": 3}, None, "v1"),
    ("", {"schema_version": 3}, {"schema_version": 2}, "v1"),
    ("unknown", {"schema_version": 3}, {"schema_version": 2}, "v1"),
])
def test_source_selector_contract(monkeypatch, requested, v3, v2, expected):
    monkeypatch.setenv("GUNZSCOPE_SUPPLY_SOURCE", requested)
    monkeypatch.setattr(supply, "read_snapshot_v3", lambda: v3)
    monkeypatch.setattr(supply, "read_shadow_v2", lambda: v2)
    assert supply.selected_supply_source() == expected


def test_v3_catalog_only_supply_and_no_rank():
    payload = v3_payload(v3_record(eligible=False, status="catalog_only"))
    supply.validate_snapshot_v3(payload)
    assert supply.get_item_supply("Item Epic", payload)["supply"] == 10
    assert supply.get_item_supply("Item Epic", payload)["status"] == "catalog_only"
    assert supply.get_item_supply_with_rank("Item Epic", payload)[1] is None
    assert supply.dense_supply_ranks(payload) == {}


@pytest.mark.parametrize("value", [-1, True, "10"])
def test_v3_catalog_only_invalid_supply_rejected(value):
    with pytest.raises(ValueError):
        supply.validate_snapshot_v3(v3_payload(v3_record(eligible=False, status="catalog_only", supply_value=value)))


def test_v3_status_and_scope_invariants_rejected():
    with pytest.raises(ValueError):
        supply.validate_snapshot_v3(v3_payload(v3_record(status="mystery")))
    with pytest.raises(ValueError):
        supply.validate_snapshot_v3(v3_payload(v3_record(eligible=True, status="catalog_only")))
    with pytest.raises(ValueError):
        supply.validate_snapshot_v3(v3_payload(v3_record(eligible=False, status="catalog_only", supply_value=1)) | {"provider_items": {"x": {**v3_record(eligible=False), "scope_reason": "wrong"}}})
    with pytest.raises(ValueError):
        bad = v3_payload(); bad["catalog_mappings"]["Item Epic"]["provider_item_id"] = "missing"; supply.validate_snapshot_v3(bad)


def test_v3_normal_dense_rank_and_v2_unchanged():
    payload = v3_payload(v3_record(supply_value=25))
    payload["provider_items"].update({"y": {**v3_record("y", 25), "provider_item_name": "Y"}, "z": {**v3_record("z", 100), "provider_item_name": "Z"}})
    assert supply.dense_supply_ranks(payload) == {"x": 1, "y": 1, "z": 2}
    assert supply.dense_supply_ranks({"schema_version": 1, "items": {"a": {"status": "ok", "supply": 5}}}) == {"a": 1}


def test_missing_v3_requested_falls_back_v1(monkeypatch):
    monkeypatch.setenv("GUNZSCOPE_SUPPLY_SOURCE", "v3")
    monkeypatch.setattr(supply, "read_snapshot_v3", lambda: None)
    monkeypatch.setattr(supply, "read_shadow_v2", lambda: None)
    assert supply.selected_supply_source() == "v1"


def test_provider_only_total_supply_candidate_survives(monkeypatch):
    from ui import top_items_overview as top
    payload = v3_payload()
    payload["provider_items"]["x"]["provider_image_url"] = "https://example.test/item.png"
    monkeypatch.setenv("GUNZSCOPE_SUPPLY_SOURCE", "v3")
    monkeypatch.setattr(top, "selected_supply_source", lambda: "v3")
    monkeypatch.setattr(top, "read_snapshot_v3", lambda: payload)
    monkeypatch.setattr(top, "load_items_index", lambda: ({}, type("D", (), {"success": True})()))
    rows = top._load_global_total_supply_candidates()
    assert len(rows) == 1 and rows.loc[0, "_provider_item_id"] == "x"
    assert rows.loc[0, "image_url"] == "https://example.test/item.png"


def test_same_asset_key_different_item_ids_are_not_merged():
    payload = v3_payload()
    payload["provider_items"]["y"] = {**v3_record("y", 3338), "provider_asset_key": "shared"}
    payload["provider_items"]["x"]["provider_asset_key"] = "shared"
    payload["catalog_mappings"]["Other Epic"] = {"mapping_status": "DIRECT_CURRENT", "provider_item_id": "y"}
    supply.validate_snapshot_v3(payload)
    assert len(supply.dense_supply_ranks(payload)) == 2
