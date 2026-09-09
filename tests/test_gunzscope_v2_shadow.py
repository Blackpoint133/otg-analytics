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
