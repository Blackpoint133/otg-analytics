import pandas as pd

from item_class_data import USER_FACING_CLASSES
from ui.top_items_overview import filter_item_classes


def test_user_facing_classes_are_stable_and_exclude_technical_values():
    assert USER_FACING_CLASSES == ("Customization Item", "Weapon", "Weapon Attachment", "Weapon Skin", "Body Part", "Profile Customization", "Music")
    assert "UNCLASSIFIED" not in USER_FACING_CLASSES
    assert "ALL CLASSES" not in USER_FACING_CLASSES


def test_multiclass_filter_is_or_preserves_order_and_ranks():
    frame = pd.DataFrame({"_item_class": ["Weapon", "Music", "Customization Item", "UNCLASSIFIED"], "supply_rank": [8, 2, 5, 1]})
    result = filter_item_classes(frame, ("Customization Item", "Weapon"))
    assert result.index.tolist() == [0, 2]
    assert result["supply_rank"].tolist() == [8, 5]
    assert frame.index.tolist() == [0, 1, 2, 3]


def test_zero_classes_returns_empty_without_reinterpreting_all():
    frame = pd.DataFrame({"_item_class": ["Weapon", "Music"]})
    assert filter_item_classes(frame, ()).empty
