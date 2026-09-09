import os

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
            "provider_scope": {"exclude_zero": True, "exclude_base": True, "sort": "activeMints", "order": "asc"},
            "provider_items": {"x": record or v3_record()},
            "catalog_mappings": {"Item Epic": {"mapping_status": "DIRECT_CURRENT", "provider_item_id": "x"}},
            "provider_item_conflicts": []}


def test_v3_failover_to_v2(monkeypatch):
    monkeypatch.setenv("GUNZSCOPE_SUPPLY_SOURCE", "v3")
    monkeypatch.setattr(supply, "read_snapshot_v3", lambda: None)
    monkeypatch.setattr(supply, "read_shadow_v2", lambda: {"schema_version": 2})
    assert supply.selected_supply_source() == "v2"


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
