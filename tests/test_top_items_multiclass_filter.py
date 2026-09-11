from pathlib import Path
import sys

import pandas as pd

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

from item_class_data import USER_FACING_CLASSES
from ui.top_items_overview import filter_item_classes


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
