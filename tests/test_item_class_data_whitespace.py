import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "streamlit_opensea_sales"))

from item_class_data import UNCLASSIFIED, class_for_name, class_options, trim_alias_mapping


def snapshot(items):
    return {"schema_version": 1, "source": "test", "items": {name: {"class": value} for name, value in items.items()}}


def test_outer_whitespace_fallbacks():
    s = snapshot({"Rampart": "Weapon", "GridOps Jetpack": "Weapon"})
    assert class_for_name(" Rampart", s) == "Weapon"
    assert class_for_name("Rampart ", s) == "Weapon"
    assert class_for_name("  Rampart  ", s) == "Weapon"


def test_exact_key_wins_over_trim_alias():
    s = snapshot({"Rampart": "Weapon", "Rampart ": "Customization Item"})
    assert class_for_name("Rampart ", s) == "Customization Item"
    assert class_for_name("Rampart", s) == "Weapon"


def test_trim_collision_is_unclassified_for_fallback():
    s = snapshot({"Item": "Weapon", " Item ": "Customization Item"})
    aliases, collisions = trim_alias_mapping(s)
    assert "Item" in collisions
    assert "Item" not in aliases
    assert class_for_name("  Item  ", s) == UNCLASSIFIED


def test_case_internal_whitespace_and_punctuation_are_not_normalized():
    s = snapshot({"GridOps Jetpack": "Weapon", "Red-Ant": "Skin"})
    assert class_for_name("gridops jetpack", s) == UNCLASSIFIED
    assert class_for_name("GridOps  Jetpack", s) == UNCLASSIFIED
    assert class_for_name("Red Ant", s) == UNCLASSIFIED


def test_class_options_uses_same_resolver_and_preserves_unclassified():
    s = snapshot({"Rampart": "Weapon", "Attachment": "Weapon Attachment"})
    assert class_options(["Rampart ", "Attachment"], s) == ["ALL CLASSES", "Weapon", "Weapon Attachment"]
    assert class_options(["Rampart ", "Unknown"], s) == ["ALL CLASSES", "UNCLASSIFIED", "Weapon"]


def test_type_and_provider_name_are_not_used():
    s = {"schema_version": 1, "provider_name": "Provider", "items": {"Catalog": {"class": "Weapon", "type": "Skin"}}}
    assert class_for_name("Provider", s) == UNCLASSIFIED
    assert class_for_name("Catalog", s) == "Weapon"
