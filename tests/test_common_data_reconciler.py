import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from streamlit_opensea_sales.common_data_sync import (
    MAX_METADATA_FETCHES_PER_RUN,
    merge_nonblank_metadata,
    normalize_item_name,
    normalization_collisions,
    select_reconciliation_targets,
)


def test_normalization_is_conservative_and_collision_visible():
    assert normalize_item_name("  GridOps   Jetpack  ") == "GridOps Jetpack"
    assert normalization_collisions(["Rampart", " Rampart "]) == {"Rampart": [" Rampart ", "Rampart"]}


def test_missing_names_are_prioritized_then_oldest():
    targets = select_reconciliation_targets(["new", "old", "fresh"], ["old"], {"old": {"last_success_at": "2026-09-08"}}, 2)
    assert targets == ["fresh", "new"]


def test_reconciliation_budget_is_bounded():
    names = [f"item-{n}" for n in range(200)]
    assert len(select_reconciliation_targets(names, [], limit=MAX_METADATA_FETCHES_PER_RUN)) == 100


def test_blank_metadata_does_not_wipe_existing_values():
    merged = merge_nonblank_metadata({"name": "x", "image": "old", "class": "Weapon", "type": "Gun"}, {"name": "x", "image": "", "class": None, "type": "New"})
    assert merged == {"name": "x", "image": "old", "class": "Weapon", "type": "New"}


def test_reconciler_is_item_bounded_and_does_not_crawl_all_tokens():
    source = (Path(__file__).resolve().parents[1] / "scripts" / "refresh_common_data.py").read_text(encoding="utf-8")
    assert "MAX_METADATA_FETCHES_PER_RUN" in source
    assert "24252" not in source


def test_sales_parser_contract_uses_safe_upsert():
    source = Path(r"C:\VAMBAM\Projects\OTG\parsers\parser_sales\db\save.py").read_text(encoding="utf-8")
    assert "ON CONFLICT (name) DO UPDATE SET" in source
    assert "ON CONFLICT (name) DO NOTHING" not in source
    assert "common_data.class" in source
