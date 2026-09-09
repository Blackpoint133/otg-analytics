import json
from pathlib import Path

import pandas as pd

from gunzscope_supply import build_v3_supply_presentation_index, get_item_supply_with_rank
from ui.top_items_overview import _attach_supply_metadata, _load_global_total_supply_candidates


def snapshot():
    path = Path(__file__).parents[1] / "streamlit_opensea_sales" / "data_opensea_sales" / "gunzscope_supply_snapshot_v3_provider.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_red_ant_presentation_config_keeps_raw_ids_and_sums_supply():
    data = snapshot()
    index = build_v3_supply_presentation_index(data)
    shorts = "cmmv915bi02pzw0omjj2dpp19"
    pants = "cmmv8jles00jbw0omw3xc16j4"
    assert index["canonical_by_member_provider_id"][pants] == shorts
    assert pants in index["suppressed_provider_ids"]
    assert len(index["effective_supply_by_canonical_provider_id"]) == len(data["provider_items"]) - 1
    assert data["provider_items"][shorts]["raw_active_mints"] + data["provider_items"][pants]["raw_active_mints"] == index["effective_supply_by_canonical_provider_id"][shorts]


def test_red_ant_market_rows_share_canonical_supply_rank():
    data = snapshot()
    rows = pd.DataFrame([{"item_key": "Red Ant Pants Epic", "item_name": "Red Ant Pants", "rarity": "Epic", "_provider_item_id": "cmmv8jles00jbw0omw3xc16j4"}])
    result = _attach_supply_metadata(rows, data)
    assert result.loc[0, "_supply"] == 3363
    assert pd.notna(result.loc[0, "_supply_rank"])
    assert get_item_supply_with_rank("Red Ant Pants Epic", data)[1] == result.loc[0, "_supply_rank"]


def test_red_ant_pants_is_not_a_total_supply_row(monkeypatch):
    data = snapshot()
    monkeypatch.setattr("ui.top_items_overview.selected_supply_source", lambda: "v3")
    monkeypatch.setattr("ui.top_items_overview.read_snapshot_v3", lambda: data)
    rows = _load_global_total_supply_candidates()
    assert rows[rows["_provider_item_id"] == "cmmv8jles00jbw0omw3xc16j4"].empty
