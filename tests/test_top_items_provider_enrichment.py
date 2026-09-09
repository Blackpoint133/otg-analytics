import pandas as pd

from ui.top_items_overview import _enrich_with_all_time_market_metrics


def test_duplicate_provider_identity_is_preserved_without_metric_copy():
    provider = pd.DataFrame([
        {"item_name": "Same", "rarity": "Epic", "_provider_item_id": "a", "_supply": 10},
        {"item_name": "Same", "rarity": "Epic", "_provider_item_id": "b", "_supply": 20},
    ])
    market = pd.DataFrame([{"item_name": "Same", "rarity": "Epic", "volume_gun": 123}])
    result = _enrich_with_all_time_market_metrics(provider, market)
    assert len(result) == 2
    assert result["_provider_item_id"].tolist() == ["a", "b"]
    assert result["volume_gun"].isna().all()
    assert result["_supply"].tolist() == [10, 20]


def test_unique_provider_identity_is_enriched_once():
    provider = pd.DataFrame([{"item_name": "Unique", "rarity": "Epic", "_provider_item_id": "a", "_supply": 10}])
    market = pd.DataFrame([{"item_name": "Unique", "rarity": "Epic", "volume_gun": 123}])
    result = _enrich_with_all_time_market_metrics(provider, market)
    assert len(result) == 1 and result.loc[0, "volume_gun"] == 123


def test_duplicate_market_identity_fails_safe():
    provider = pd.DataFrame([{"item_name": "Unique", "rarity": "Epic", "_provider_item_id": "a", "_supply": 10}])
    market = pd.DataFrame([
        {"item_name": "Unique", "rarity": "Epic", "volume_gun": 123},
        {"item_name": "Unique", "rarity": "Epic", "volume_gun": 456},
    ])
    result = _enrich_with_all_time_market_metrics(provider, market)
    assert len(result) == 1 and pd.isna(result.loc[0, "volume_gun"])
