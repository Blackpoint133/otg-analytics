import sys
from pathlib import Path

import pytest

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))
import item_class_data as classes


def test_source_and_effective_mappings_are_separate(monkeypatch):
    snapshot = {"items": {"Track Alpha": {"class": "Customization Item"}, "Helmet Beta": {"class": "Customization Item"}}}
    monkeypatch.setattr(classes, "read_item_class_overrides", lambda: {"Track Alpha": {"class": "Music", "reason": "test"}})
    source = classes.source_class_mapping(snapshot)
    effective = classes.effective_class_mapping(snapshot)
    assert source["Track Alpha"] == "Customization Item"
    assert effective["Track Alpha"] == "Music"
    assert source != effective


def test_override_validation_is_strict_and_unknown_does_not_create_options(tmp_path):
    path = tmp_path / "overrides.json"
    path.write_text('{"schema_version":1,"overrides":{"Known":{"class":"Music"},"bad": {"class": 4}, "blank": {"class":""}}}')
    loaded = classes.load_item_class_overrides(str(path), path.stat().st_mtime_ns)
    assert list(loaded) == ["Known"]
    assert classes.class_options(["Unknown"], {"items": {"Unknown": {"class": "Customization Item"}}}) == ["ALL CLASSES", "Customization Item"]


def test_missing_or_malformed_override_fails_safe(tmp_path):
    missing = tmp_path / "missing.json"
    assert classes.load_item_class_overrides(str(missing), 0) == {}
    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"schema_version":9,"overrides":[]}')
    assert classes.load_item_class_overrides(str(malformed), malformed.stat().st_mtime_ns) == {}


def test_class_for_name_uses_effective_mapping_and_preserves_trim_safety(monkeypatch):
    snapshot = {"items": {"Track Alpha": {"class": "Customization Item"}, "Name ": {"class": "A"}, "Name": {"class": "B"}}}
    monkeypatch.setattr(classes, "read_item_class_overrides", lambda: {"Track Alpha": {"class": "Music", "reason": "test"}})
    assert classes.class_for_name("Track Alpha", snapshot) == "Music"
    assert classes.class_for_name(" Track Alpha ", snapshot) == "Music"
    assert classes.class_for_name(" Name ", snapshot) == classes.UNCLASSIFIED
