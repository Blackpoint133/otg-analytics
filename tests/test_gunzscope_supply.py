import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
SCRIPT = Path(__file__).parents[1] / "scripts" / "refresh_gunzscope_supply.py"
sys.path.insert(0, str(APP))
import gunzscope_client as client
import gunzscope_supply as supply


def load_refresh():
    spec = importlib.util.spec_from_file_location("refresh_gunzscope_supply_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


refresh = load_refresh()


def rec(value, status="ok"):
    return {"supply": value, "status": status, "fetched_at": "2026-09-02T00:00:00+00:00"}


def snap(items):
    return {"schema_version": 1, "source": "gunzscope", "snapshot_fetched_at": "2026-09-02T00:00:00+00:00", "attribution": supply.ATTRIBUTION, "items": items}


def record(name="Item", rarity="Epic", key="key"):
    return {"item_key": key, "display_name": name, "rarity": rarity}


def response(status=200, payload=None, headers=None):
    result = Mock(status_code=status, headers=headers or {})
    result.json = Mock(return_value=payload)
    return result


def test_leading_whitespace_is_trimmed():
    assert supply.provider_lookup_pair(" Item", "Epic") == ("Item", "Epic")


def test_trailing_whitespace_is_trimmed():
    assert supply.provider_lookup_pair("Item ", "Epic") == ("Item", "Epic")


def test_surrounding_rarity_whitespace_is_trimmed():
    assert supply.provider_lookup_pair("Item", "  Epic\t") == ("Item", "Epic")


def test_internal_whitespace_is_not_collapsed():
    assert supply.normalize_provider_lookup_name("A  B") == "A  B"


def test_punctuation_is_preserved():
    assert supply.normalize_provider_lookup_name("Bob's #1") == "Bob's #1"


def test_case_is_preserved():
    assert supply.normalize_provider_lookup_name("PHOSPHOR FURY") == "PHOSPHOR FURY"


def test_normalized_pair_collision_is_detected():
    with pytest.raises(ValueError, match="collision"):
        refresh.mapping_dry_run([record("A", "Epic", "1"), record(" A ", "Epic", "2")])


def test_empty_after_strip_is_invalid():
    assert refresh.mapping_dry_run([record("  ", "Epic")])["invalid"] == 1


def test_empty_rarity_after_strip_is_invalid():
    assert refresh.mapping_dry_run([record("Item", " \t")])["invalid"] == 1


def test_invalid_identity_is_not_sent_to_provider():
    records = [record(" ", "Epic", "bad"), record("Good", "Epic", "good")]
    assert refresh.valid_request_records(records) == [records[1]]


def test_active_mints_is_primary_supply():
    payload = {"results": {"A::Epic": {"items": [{"activeMints": 37}], "totalSupply": 999}}}
    assert client._validate_batch_payload(payload)["results"]["A::Epic"]["items"][0]["activeMints"] == 37


def test_empty_provider_result_is_unavailable():
    item, outcome = refresh.build_item_record(record(), {"items": []})
    assert item["status"] == "unavailable" and outcome == "empty"


def test_provider_identity_mismatch_is_not_accepted():
    item, outcome = refresh.build_item_record(record(), {"items": [{"itemName": "Other", "rarity": "Epic", "activeMints": 1}]})
    assert item["status"] == "unavailable" and outcome == "mismatch"


def test_missing_active_mints_is_invalid():
    item, _ = refresh.build_item_record(record(), {"items": [{"itemName": "Item", "rarity": "Epic"}]})
    assert item["status"] == "unavailable"


def test_negative_active_mints_is_invalid():
    item, _ = refresh.build_item_record(record(), {"items": [{"itemName": "Item", "rarity": "Epic", "activeMints": -1}]})
    assert item["status"] == "unavailable"


def test_non_integer_active_mints_is_invalid():
    item, _ = refresh.build_item_record(record(), {"items": [{"itemName": "Item", "rarity": "Epic", "activeMints": "1"}]})
    assert item["status"] == "unavailable"


def test_trimmed_request_and_identity_are_used():
    item, outcome = refresh.build_item_record(record(" Item ", " Epic "), {"items": [{"itemName": "Item", "rarity": "Epic", "activeMints": 4}]})
    assert outcome == "ok" and item["request_name"] == "Item" and item["request_rarity"] == "Epic"


def test_malformed_json_is_rejected():
    r = response(payload=None); r.json.side_effect = ValueError
    session = Mock(); session.post.return_value = r
    with pytest.raises(client.GunzscopeError, match="malformed"):
        client.fetch_batch([{"name": "A", "rarity": "Epic"}], session=session)


def test_timeout_retries_are_bounded():
    session = Mock(); session.post.side_effect = requests.Timeout()
    with pytest.raises(client.GunzscopeError):
        client.fetch_batch([{"name": "A", "rarity": "Epic"}], session=session, sleep=lambda _: None)
    assert session.post.call_count == 3


def test_5xx_retries_are_bounded():
    session = Mock(); session.post.side_effect = [response(500), response(500), response(500)]
    with pytest.raises(client.GunzscopeError):
        client.fetch_batch([{"name": "A", "rarity": "Epic"}], session=session, sleep=lambda _: None)
    assert session.post.call_count == 3


def test_429_honors_retry_after():
    session = Mock(); session.post.side_effect = [response(429, headers={"Retry-After": "7"}), response(payload={"results": {}})]
    sleeps = []
    assert client.fetch_batch([{"name": "A", "rarity": "Epic"}], session=session, sleep=sleeps.append) == {"results": {}}
    assert sleeps == [7.0]


def test_missing_api_key_is_safe(monkeypatch):
    monkeypatch.delenv("API_GUNZSCOPE", raising=False)
    with pytest.raises(client.GunzscopeError, match="not configured"):
        client.fetch_batch([{"name": "A", "rarity": "Epic"}])


def test_secret_is_not_in_error_or_logs(monkeypatch, caplog):
    secret = "TEST_SECRET_DO_NOT_LOG"; monkeypatch.setenv("API_GUNZSCOPE", secret)
    session = Mock(); session.post.side_effect = requests.Timeout()
    with pytest.raises(client.GunzscopeError) as exc:
        client.fetch_batch([{"name": "A", "rarity": "Epic"}], session=session, sleep=lambda _: None)
    assert secret not in str(exc.value) and secret not in caplog.text


def test_atomic_publication_success(tmp_path, monkeypatch):
    monkeypatch.setattr(refresh, "DATA_DIR", tmp_path); monkeypatch.setattr(refresh, "SNAPSHOT_PATH", tmp_path / "snapshot.json")
    payload = snap({}); refresh.publish(payload)
    assert json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8")) == payload


def test_failed_publication_preserves_previous(tmp_path, monkeypatch):
    monkeypatch.setattr(refresh, "DATA_DIR", tmp_path); target = tmp_path / "snapshot.json"; monkeypatch.setattr(refresh, "SNAPSHOT_PATH", target)
    refresh.publish(snap({"a": rec(1)})); monkeypatch.setattr(refresh.os, "replace", Mock(side_effect=OSError("disk")))
    with pytest.raises(OSError): refresh.publish(snap({"a": rec(2)}))
    assert json.loads(target.read_text(encoding="utf-8"))["items"]["a"]["supply"] == 1


def test_last_known_good_becomes_stale():
    old = {"supply": 7, "status": "ok", "request_name": "Item", "request_rarity": "Epic"}
    item, outcome = refresh.build_item_record(record(), {"items": []}, old)
    assert outcome == "stale" and item["supply"] == 7 and item["status"] == "stale"


def test_stale_state_is_ranked():
    assert supply.dense_supply_ranks(snap({"a": rec(2, "stale")})) == {"a": 1}


def test_duplicate_refresh_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(refresh, "LOCK_PATH", tmp_path / "lock"); first = refresh.acquire_lock(); second = refresh.acquire_lock()
    assert first is not None and second is None; refresh.release_lock(first)


def test_lock_cleanup_after_exception(tmp_path, monkeypatch):
    monkeypatch.setattr(refresh, "LOCK_PATH", tmp_path / "lock"); handle = refresh.acquire_lock()
    try: raise RuntimeError("synthetic")
    except RuntimeError: refresh.release_lock(handle)
    assert not (tmp_path / "lock").exists()


def test_dry_run_mapping_is_offline(monkeypatch):
    called = []; monkeypatch.setattr(refresh, "fetch_batch", lambda *args, **kwargs: called.append(1))
    result = refresh.mapping_dry_run([record("A", "Epic")])
    assert result["batches"] == 1 and called == []


def test_unavailable_is_excluded_from_rank():
    assert supply.dense_supply_ranks(snap({"a": rec(1), "b": {"status": "unavailable"}})) == {"a": 1}


def test_zero_supply_is_valid_and_lowest_dense_rank():
    data = snap({"zero": rec(0), "one": rec(1), "tie": rec(1)})
    assert supply.dense_supply_ranks(data) == {"zero": 1, "one": 2, "tie": 2}


def test_attribution_validation_and_fallback():
    data = snap({}); data["attribution"] = {"text": "bad", "url": "https://evil"}
    with pytest.raises(ValueError): supply.validate_snapshot(data)
    assert supply.ATTRIBUTION["text"] == "Data by GUNZscope"


def test_no_snapshot_ui_fallback(tmp_path):
    assert supply.load_snapshot(str(tmp_path / "none.json"), None) is None


def test_batch_chunking_1919_is_20_batches():
    records = [record(f"Item {i}", "Epic", str(i)) for i in range(1919)]
    assert len(list(refresh.chunks(records))) == 20


def test_batch_response_order_does_not_change_item_assignment():
    results = {"B::Epic": {"items": [{"itemName": "B", "rarity": "Epic", "activeMints": 2}]}, "A::Epic": {"items": [{"itemName": "A", "rarity": "Epic", "activeMints": 1}]}}
    a, _ = refresh.build_item_record(record("A", "Epic", "a"), results["A::Epic"]); b, _ = refresh.build_item_record(record("B", "Epic", "b"), results["B::Epic"])
    assert a["supply"] == 1 and b["supply"] == 2


def test_valid_record_keeps_exact_otg_key_outside_lookup():
    item, _ = refresh.build_item_record(record(" Item ", "Epic", "otg-original"), {"items": [{"itemName": "Item", "rarity": "Epic", "activeMints": 3}]})
    assert item["request_name"] == "Item"
