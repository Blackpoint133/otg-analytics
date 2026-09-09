import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1]))
sys.path.insert(0, str(Path(__file__).parents[1] / "streamlit_opensea_sales"))

from scripts.refresh_item_class_snapshot import build_snapshot, publish_snapshot
from item_class_data import UNCLASSIFIED, class_options, class_mapping, source_class_mapping
from ui.top_items_overview import attach_item_classes, filter_item_class, paginate_top_items


def test_snapshot_uses_class_only_and_writer_schema(tmp_path):
    payload = build_snapshot([("Weapon", "Weapon"), ("Mystery", None)])
    assert payload["source"] == "public.item_metadata_current.class + public.common_data.class fallback"
    assert payload["items"] == {"Weapon": {"class": "Weapon"}}
    assert "type" not in json.dumps(payload)
    publish_snapshot(payload, tmp_path / "item_class_snapshot.json")
    assert json.loads((tmp_path / "item_class_snapshot.json").read_text())["items"]["Weapon"]["class"] == "Weapon"


def test_class_options_and_unclassified_are_snapshot_derived():
    snapshot = {"items": {"A": {"class": "Weapon"}, "B": {"class": "Profile"}}}
    assert class_options(["A", "B", "C"], snapshot) == ["ALL CLASSES", "Profile", "UNCLASSIFIED", "Weapon"]
    assert source_class_mapping(snapshot) == {"A": "Weapon", "B": "Profile"}


def test_filter_precedes_pagination_and_preserves_global_rank():
    data = pd.DataFrame({"item_name": ["A", "B", "C"], "rank": [1, 2, 3]})
    classified = attach_item_classes(data, {"A": "Weapon", "B": "Profile"})
    filtered = filter_item_class(classified, "Profile")
    page, _, _ = paginate_top_items(filtered, 1, 20)
    assert page.iloc[0]["rank"] == 2


def test_all_classes_keeps_unclassified_rows():
    data = attach_item_classes(pd.DataFrame({"item_name": ["A", "B"]}), {"A": "Weapon"})
    assert set(data["_item_class"]) == {"Weapon", UNCLASSIFIED}
    assert len(filter_item_class(data, "ALL CLASSES")) == 2
