import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "streamlit_opensea_sales"))

import pandas as pd

from streamlit_opensea_sales import market_data_access as mda


def test_complete_period_loader_is_untruncated_and_uses_stable_identity():
    frame = mda.load_complete_top_item_metrics("all")
    assert frame is not None
    assert len(frame) > 20
    assert frame["item_key"].is_unique


def test_supported_periods_load_without_limit():
    for period in ("all", "30d", "7d", "1d"):
        frame = mda.load_complete_top_item_metrics(period)
        assert frame is not None
        assert len(frame) > 0
        assert frame["item_key"].is_unique


def test_complete_loader_matches_authoritative_source_for_each_period():
    for period in ("all", "30d", "7d", "1d"):
        source = pd.read_csv(mda.get_complete_top_item_metrics_path(period))
        loaded = mda.load_complete_top_item_metrics(period, cache_buster="source-test")
        assert len(loaded) == len(source)
        assert list(loaded.columns) == list(source.columns)
        pd.testing.assert_frame_equal(loaded, source)


def test_unknown_period_fails_safely():
    assert mda.load_complete_top_item_metrics("90d") is None


def test_missing_authoritative_source_fails_safely(monkeypatch, tmp_path):
    monkeypatch.setattr(mda, "get_complete_top_item_metrics_path", lambda period: tmp_path / "missing.csv")
    assert mda.load_complete_top_item_metrics("all", cache_buster="missing-test") is None


def test_compatibility_loader_still_honors_limit():
    frame = mda.load_top_items_ranking("volume", "all", cache_buster="limit-test", limit=20)
    assert len(frame) == 20


def test_top_n_volume_rows_are_subset_of_complete_all_time_artifact():
    complete = mda.load_complete_top_item_metrics("all")
    ranking = pd.read_csv(mda.get_market_overview_dir() / "top_items_by_volume_ranking.csv")
    assert set(ranking["item_key"]).issubset(set(complete["item_key"]))
    shared = ranking.merge(complete, on="item_key", suffixes=("_top", "_complete"))
    for field in ("volume_gun", "volume_usd", "avg_price_gun", "avg_price_usd", "liquidity_score", "market_strength_score"):
        assert (shared[f"{field}_top"] == shared[f"{field}_complete"]).all()
