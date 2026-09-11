import sys
from pathlib import Path

import pytest

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))
import item_class_data as classes


def test_valid_fallback_config_contains_only_expected_normal_classes():
    assert classes.read_asset_key_fallbacks() == {
        "CustomizationItemTemplate": "Customization Item", "Weapon": "Weapon",
        "WeaponAttachment": "Weapon Attachment", "WeaponSkin": "Weapon Skin",
        "ProfileCustomization": "Profile Customization", "BodyPart": "Body Part",
        "PartItem": "Weapon Skin",
    }


@pytest.mark.parametrize("entry", [
    {"": "Weapon"}, {"Weapon_Foo": "Weapon"}, {" Weapon": "Weapon"},
    {"Weapon": "Music"}, {"Weapon": "Anomalies"}, {"Weapon": "UNCLASSIFIED"},
    {"Weapon": "Unknown"},
])
def test_any_invalid_family_entry_fails_closed(tmp_path, entry):
    payload = {"schema_version": 1, "purpose": "opensea_sales presentation-only assetKey class fallbacks",
               "families": {"Valid": "Weapon", **entry}}
    path = tmp_path / "fallbacks.json"
    import json
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert classes.load_asset_key_fallbacks(str(path), 1) == {}


def test_provider_precedence_and_unknown_family(monkeypatch):
    monkeypatch.setattr(classes, "read_item_class_overrides", lambda: {"Music Item": {"class": "Music"}, "Anomaly Item": {"class": "Anomalies"}})
    source = {"items": {"Source Item": {"class": "Weapon"}, "Conflict Item": {"class": "Weapon Attachment"}}}
    assert classes.class_for_provider_item("Music Item", "CustomizationItemTemplate_X", source) == "Music"
    assert classes.class_for_provider_item("Anomaly Item", "WeaponAttachment_X", source) == "Anomalies"
    assert classes.class_for_provider_item("Source Item", "WeaponSkin_X", source) == "Weapon"
    assert classes.class_for_provider_item("New Item", "CustomizationItemTemplate_X", source) == "Customization Item"
    assert classes.class_for_provider_item("Unknown Item", "NewFamily_X", source) == classes.UNCLASSIFIED


def test_general_mapping_is_source_and_manual_only(monkeypatch):
    monkeypatch.setattr(classes, "read_item_class_overrides", lambda: {"Manual Item": {"class": "Music"}})
    result = classes.effective_class_mapping({"items": {"Source Item": {"class": "Weapon"}}})
    assert result == {"Source Item": "Weapon", "Manual Item": "Music"}
