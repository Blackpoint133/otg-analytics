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


def test_enrichment_preserves_exact_identity_order_index_and_nan_overwrite():
    provider = pd.DataFrame([
        {"item_name": "A", "rarity": "Epic", "volume_gun": 123},
        {"item_name": " A", "rarity": "Epic", "volume_gun": 456},
        {"item_name": "B", "rarity": "Rare", "volume_gun": 789},
    ], index=[10, 3, 42])
    market = pd.DataFrame([
        {"item_name": "A", "rarity": "Epic", "volume_gun": float("nan")},
        {"item_name": " A", "rarity": "epic", "volume_gun": 9},
        {"item_name": "B", "rarity": "Rare", "volume_usd": 11},
    ])
    original_provider, original_market = provider.copy(deep=True), market.copy(deep=True)
    result = _enrich_with_all_time_market_metrics(provider, market)
    assert result.index.tolist() == [10, 3, 42]
    assert pd.isna(result.loc[10, "volume_gun"])
    assert result.loc[3, "volume_gun"] == 456
    assert pd.isna(result.loc[42, "volume_gun"])
    assert result.loc[42, "volume_usd"] == 11
    pd.testing.assert_frame_equal(provider, original_provider)
    pd.testing.assert_frame_equal(market, original_market)
