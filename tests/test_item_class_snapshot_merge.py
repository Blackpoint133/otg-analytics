import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "refresh_item_class_snapshot.py"
SPEC = importlib.util.spec_from_file_location("refresh_item_class_snapshot", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def classes(legacy=(), current=()):
    payload = MODULE.build_snapshot(legacy, current)
    return {name: value["class"] for name, value in payload["items"].items()}


def test_legacy_only_class():
    assert classes([("Legacy", "Weapon")]) == {"Legacy": "Weapon"}


def test_current_only_class():
    assert classes([], [("Current", "Weapon Attachment")]) == {"Current": "Weapon Attachment"}


def test_current_exact_catalog_name_overrides_legacy():
    assert classes([("Example Item", "OldClass")], [("Example Item", "NewClass")]) == {"Example Item": "NewClass"}


def test_blank_current_class_preserves_legacy():
    assert classes([("Example Item", "OldClass")], [("Example Item", "")]) == {"Example Item": "OldClass"}


def test_provider_name_is_not_a_lookup_key_or_fuzzy_fallback():
    assert classes([], [("Catalog Prefix Item", "Weapon")]) == {"Catalog Prefix Item": "Weapon"}
    assert "Provider Item" not in classes([], [("Catalog Prefix Item", "Weapon")])


def test_case_sensitive_exact_identity_and_no_type_source():
    assert classes([("Example Item", "Weapon")], [("example item", "Skin")]) == {
        "Example Item": "Weapon", "example item": "Skin"
    }
    assert "type" not in MODULE.build_snapshot([], [("Example Item", "Weapon")])["items"]["Example Item"]


def test_schema_compatible_and_unclassified_is_outside_snapshot():
    payload = MODULE.build_snapshot([], [])
    assert payload["schema_version"] == 1
    assert payload["items"] == {}
    assert "source" in payload
