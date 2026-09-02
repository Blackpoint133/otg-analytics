import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))
import gunzscope_client as client
import gunzscope_supply as supply


def rec(value, status="ok"):
    return {"supply": value, "status": status, "fetched_at": "2026-09-02T00:00:00+00:00"}


def snap(items):
    return {"schema_version": 1, "source": "gunzscope", "snapshot_fetched_at": "2026-09-02T00:00:00+00:00", "attribution": supply.ATTRIBUTION, "items": items}


def test_active_mints_is_primary_supply():
    assert client._validate_batch_payload({"results": {"A::Epic": {"items": [{"activeMints": 37}], "totalSupply": 999}}})["results"]["A::Epic"]["items"][0]["activeMints"] == 37


def test_dense_ascending_rank_and_exclusions():
    data = snap({"A": rec(37), "B": rec(37), "C": rec(40), "D": {"status": "unavailable"}})
    assert supply.dense_supply_ranks(data) == {"A": 1, "B": 1, "C": 2}


def test_stale_value_is_preserved_for_rank():
    data = snap({"A": rec(2, "stale")})
    assert supply.get_item_supply_with_rank("A", data)[1] == 1


def test_invalid_attribution_rejected():
    data = snap({}); data["attribution"] = dict(data["attribution"]); data["attribution"]["url"] = "https://evil.example"
    with pytest.raises(ValueError): supply.validate_snapshot(data)


def test_missing_snapshot_is_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(supply, "SNAPSHOT_PATH", tmp_path / "missing.json")
    assert supply.read_current_snapshot() is None


def test_missing_key_and_429_retry(monkeypatch):
    monkeypatch.delenv("API_GUNZSCOPE", raising=False)
    with pytest.raises(client.GunzscopeError): client.fetch_batch([{"name": "A", "rarity": "Epic"}])
    monkeypatch.setenv("API_GUNZSCOPE", "synthetic-key")
    r429 = Mock(status_code=429, headers={"Retry-After": "0"})
    r200 = Mock(status_code=200, headers={}, json=lambda: {"results": {}})
    session = Mock(); session.post.side_effect = [r429, r200]; sleeps = []
    assert client.fetch_batch([{"name": "A", "rarity": "Epic"}], session=session, sleep=sleeps.append) == {"results": {}}
    assert session.post.call_count == 2 and sleeps == [0.0]


def test_chunking_1919_is_20_batches():
    import runpy
    module = runpy.run_path(str(Path(__file__).parents[1] / "scripts" / "refresh_gunzscope_supply.py"))
    records = [{"item_key": str(i), "display_name": f"Item {i}", "rarity": "Epic"} for i in range(1919)]
    assert len(list(module["chunks"](records))) == 20


def test_item_request_is_available_for_bounded_sanity(monkeypatch):
    monkeypatch.setenv("API_GUNZSCOPE", "synthetic-key")
    response = Mock(status_code=200, json=lambda: {"items": []})
    session = Mock(); session.get.return_value = response
    assert client.fetch_item("Kestrel Adaptive Stock", "Epic", session=session)["items"] == []
    assert session.get.call_count == 1
