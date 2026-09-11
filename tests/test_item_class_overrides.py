import sys
from pathlib import Path

import pytest

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))
import item_class_data as classes

EXPECTED_NAMES = {
    "Neckbraker", "Welcome to the Circle", "Move To Live", "Tagged for Death", "Dead Pilot",
    "GlykoBitz - Carol of the Damned", "GlykoBitz - Maul Cop", "GlykoBitz - Sleigh Bitch, Big Band Edition",
    "GlykoBitz - It's Beginning to Look a Lot Like Teardrop", "GlykoBitz - Santa Pay Me", "GlykoBitz - North Pole P***y",
    "Snakes in the Sky", "Pulse", "Arp Machine", "The Last Dance", "Respawn Wheel", "No Country For Cheaters",
    "Taste of Freedom", "I'll Fly Before You Die", "Do or Die", "Fried ass", "Face of Death", "Ballgag Beat",
    "Big Top Beat", "First Spin", "Meatport - Enter the Grid", "Bargain Beat", "Meth Made", "Cybernetic Dreams",
    "Cyber Grinder", "Population Control", "One-Way Ticket to the Fight", "Spreading the Hurt", "Love My Limbs",
}


def test_committed_config_contains_exact_music_set():
    payload = __import__('json').loads((APP / 'config' / 'item_class_overrides.json').read_text(encoding='utf-8'))
    assert payload['schema_version'] == 1
    assert {name for name, entry in payload['overrides'].items() if entry['class'] == 'Music'} == EXPECTED_NAMES
    assert len(EXPECTED_NAMES) == 34
    assert all(entry == {'class': 'Music', 'reason': 'In-game music NFT'} for name, entry in payload['overrides'].items() if name in EXPECTED_NAMES)
    assert payload['overrides']['Pierser Red Dot Compact Sight']['class'] == 'Anomalies'
    assert payload['overrides']['Pierser Holographic Sight']['class'] == 'Anomalies'


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
