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


def test_unknown_period_fails_safely():
    assert mda.load_complete_top_item_metrics("90d") is None


def test_top_n_volume_rows_are_subset_of_complete_all_time_artifact():
    complete = mda.load_complete_top_item_metrics("all")
    ranking = pd.read_csv(mda.get_market_overview_dir() / "top_items_by_volume_ranking.csv")
    assert set(ranking["item_key"]).issubset(set(complete["item_key"]))
    shared = ranking.merge(complete, on="item_key", suffixes=("_top", "_complete"))
    for field in ("volume_gun", "volume_usd", "avg_price_gun", "avg_price_usd", "liquidity_score", "market_strength_score"):
        assert (shared[f"{field}_top"] == shared[f"{field}_complete"]).all()
