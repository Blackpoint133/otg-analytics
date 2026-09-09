import json
import sys
from pathlib import Path

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP)); sys.path.insert(0, str(APP.parent / "scripts"))
import gunzscope_client as client
import refresh_gunzscope_supply_v2_shadow as v2


def test_client_resolve_retired_is_opt_in():
    class Response:
        status_code = 200
        headers = {}
        def json(self): return {"results": {}}
    class Session:
        def post(self, *args, **kwargs): self.kwargs = kwargs; return Response()
    s = Session(); import os; os.environ["API_GUNZSCOPE"] = "test"
    client.fetch_batch([{"name":"A","rarity":"Epic"}], session=s)
    assert s.kwargs["params"] is None
    client.fetch_batch([{"name":"A","rarity":"Epic"}], session=s, resolve_retired=True)
    assert s.kwargs["params"] == {"resolveRetired":"1"}


def test_resolved_mapping_and_itemid_dedup():
    records = [{"item_key":"A Epic","display_name":"A","rarity":"Epic"},{"item_key":"A Old","display_name":"A","rarity":"Common"}]
    c = {"itemName":"A","rarity":"Rare","itemId":"id1","assetKey":"asset","activeMints":7,"matchedVia":"rarityHistory","queriedRarity":"Common"}
    out = v2.build_shadow(records, [[c],[c]])
    assert len(out["provider_items"]) == 1
    assert out["catalog_mappings"]["A Old"]["mapping_status"] == "RETIRED_RARITY_RESOLVED"


def test_same_asset_different_itemids_stay_separate():
    records = [{"item_key":"S","display_name":"Red Ant Shorts","rarity":"Epic"},{"item_key":"P","display_name":"Red Ant Pants","rarity":"Epic"}]
    def c(name, item): return {"itemName":name,"rarity":"Epic","itemId":item,"assetKey":"shared","activeMints":25}
    out = v2.build_shadow(records, [[c("Red Ant Shorts","shorts")],[c("Red Ant Pants","pants")]])
    assert len(out["provider_items"]) == 2


def test_invalid_supply_types_are_not_valid_provider_records():
    record = {"item_key":"A","display_name":"A","rarity":"Epic"}
    for value in (-1, True, "7", 7.0, None):
        out = v2.build_shadow([record], [[{"itemName":"A","rarity":"Epic","itemId":"id","assetKey":"a","activeMints":value}]])
        assert not out["provider_items"]
        assert out["catalog_mappings"]["A"]["mapping_status"] == "INVALID_PROVIDER_DATA"


def test_validator_rejects_dangling_mapping_and_conflicts():
    with __import__('pytest').raises(ValueError):
        v2.validate_shadow_v2({"schema_version":2,"source":"gunzscope","provider_items":{},"catalog_mappings":{"A":{"mapping_status":"DIRECT_CURRENT","provider_item_id":"missing"}}})
    records = [{"item_key":"A","display_name":"A","rarity":"Epic"},{"item_key":"B","display_name":"B","rarity":"Epic"}]
    out = v2.build_shadow(records, [[{"itemName":"A","rarity":"Epic","itemId":"id","assetKey":"a","activeMints":1}],[{"itemName":"B","rarity":"Epic","itemId":"id","assetKey":"b","activeMints":1}]])
    assert out["catalog_mappings"]["A"]["mapping_status"] == "PROVIDER_ITEM_CONFLICT"
    assert not out["provider_items"]
