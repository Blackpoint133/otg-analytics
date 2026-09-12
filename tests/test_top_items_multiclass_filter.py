from pathlib import Path
import sys

import pandas as pd

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

from item_class_data import USER_FACING_CLASSES
from ui.top_items_overview import assign_top_item_filter_ranks, filter_item_classes


def test_user_facing_classes_are_stable_and_exclude_technical_values():
    assert USER_FACING_CLASSES == ("Customization Item", "Weapon", "Weapon Attachment", "Weapon Skin", "Body Part", "Profile Customization", "Music", "Anomalies")
    assert "UNCLASSIFIED" not in USER_FACING_CLASSES
    assert "ALL CLASSES" not in USER_FACING_CLASSES


def test_unclassified_is_total_supply_only_sidebar_bucket():
    source = (Path(__file__).parents[1] / "streamlit_opensea_sales" / "ui" / "sidebar.py").read_text(encoding="utf-8")
    assert "display_classes.append(UNCLASSIFIED)" in source
    assert "if current_mode == 'total_supply':" in source
    assert 'label = "Unclassified" if name == UNCLASSIFIED else name' in source
    assert "defaults[UNCLASSIFIED] = True" in source


def test_multiclass_filter_is_or_preserves_order_and_ranks():
    frame = pd.DataFrame({"_item_class": ["Weapon", "Music", "Customization Item", "UNCLASSIFIED"], "supply_rank": [8, 2, 5, 1]})
    result = filter_item_classes(frame, ("Customization Item", "Weapon"))
    assert result.index.tolist() == [0, 2]
    assert result["supply_rank"].tolist() == [8, 5]
    assert frame.index.tolist() == [0, 1, 2, 3]


def test_zero_classes_returns_empty_without_reinterpreting_all():
    frame = pd.DataFrame({"_item_class": ["Weapon", "Music"]})
    assert filter_item_classes(frame, ()).empty


def test_total_supply_filter_rank_uses_central_supply_rank_eligibility():
    frame = pd.DataFrame({
        "item_name": ["Pierser Red Dot Compact Sight", "Regiment Hoodie", "Cyrix", "Pierser Holographic Sight"],
        "_supply": [1, 7, 7, 15],
        "_supply_rank": [pd.NA, 1, 1, 2],
    })
    result = assign_top_item_filter_ranks(frame, "total_supply")
    assert pd.isna(result.loc[0, "_filter_rank"])
    assert result.loc[1, "_filter_rank"] == 1
    assert result.loc[2, "_filter_rank"] == 1
    assert result.loc[3, "_filter_rank"] == 2


def test_total_supply_all_excluded_rows_remain_unranked():
    frame = pd.DataFrame({"_supply": [1, 2], "_supply_rank": [pd.NA, pd.NA]})
    result = assign_top_item_filter_ranks(frame, "total_supply")
    assert result["_filter_rank"].isna().all()
