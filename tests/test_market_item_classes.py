import json
import math
import sys
from pathlib import Path

import pandas as pd

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

from charts_market import build_daily_item_class_chart, build_monthly_item_class_chart  # noqa: E402
from market_item_classes import (  # noqa: E402
    CURRENT_ITEM_CLASS_COLORS,
    CURRENT_ITEM_CLASS_ORDER,
    UNCLASSIFIED,
    build_class_metadata,
    build_sales_by_item_class,
    class_for_name,
    payload_to_frames,
    read_item_class_snapshot,
    validate_sales_by_item_class_payload,
)
from scripts.build_market_expansion_metrics import build_from_directory  # noqa: E402


def _snapshot(mapping=None):
    return {"schema_version": 1, "source": "public.item_metadata_current.class + public.common_data.class fallback", "generated_at": "2026-09-18T00:00:00Z", "items": {name: {"class": value} for name, value in (mapping or {"Alpha": "Weapon", "Beta": "Body Part"}).items()}}


def _axes():
    daily = pd.DataFrame({"date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"])})
    monthly = pd.DataFrame({"month": ["2026-01"], "month_start": pd.to_datetime(["2026-01-01"]), "month_end": pd.to_datetime(["2026-01-31"])})
    return daily, monthly


def _sales():
    return pd.DataFrame([
        {"sale_date": "2026-01-01T00:00:00Z", "name": "Alpha"},
        {"sale_date": "2026-01-01T01:00:00Z", "name": " Beta "},
        {"sale_date": "2026-01-02T00:00:00Z", "name": "alpha"},
    ])


def test_resolver_exact_trim_and_rejects_unsafe_normalization():
    mapping = {"Alpha": "Weapon", " Alpha ": "Body Part", "Internal  Space": "Weapon", '"Quoted"': "Body Part"}
    assert class_for_name("Alpha", mapping) == "Weapon"
    assert class_for_name(" Alpha ", mapping) == "Body Part"
    assert class_for_name("  Alpha  ", mapping) == UNCLASSIFIED
    assert class_for_name("alpha", mapping) == UNCLASSIFIED
    assert class_for_name("Internal Space", mapping) == UNCLASSIFIED
    assert class_for_name("Quoted", mapping) == UNCLASSIFIED


def test_ambiguous_trim_collision_is_unclassified():
    assert class_for_name(" Alpha ", {"Alpha": "Weapon", " Alpha ": "Body Part"}) == "Body Part"
    assert class_for_name("  Alpha  ", {"Alpha": "Weapon", " Alpha ": "Body Part"}) == UNCLASSIFIED


def test_class_metadata_preserves_current_contract_and_handles_future_class():
    metadata = build_class_metadata(set(CURRENT_ITEM_CLASS_ORDER) | {"Music"})
    assert [entry["name"] for entry in metadata[:6]] == list(CURRENT_ITEM_CLASS_ORDER)
    assert metadata[-1]["name"] == "Music"
    assert metadata[-1]["color"] not in set(CURRENT_ITEM_CLASS_COLORS.values())
    assert metadata[-1] == build_class_metadata(set(CURRENT_ITEM_CLASS_ORDER) | {"Music"})[-1]
    assert {entry["name"]: entry["color"] for entry in metadata if entry["name"] in CURRENT_ITEM_CLASS_ORDER} == {name: CURRENT_ITEM_CLASS_COLORS[name] for name in CURRENT_ITEM_CLASS_ORDER}


def test_prepared_payload_zero_fills_and_reconciles():
    snapshot = _snapshot()
    daily, monthly = _axes()
    payload = build_sales_by_item_class(_sales().assign(name=["Alpha", " Alpha ", "Beta"]), daily, monthly, snapshot, {"sha256": "a" * 64, "schema_version": 1, "source": snapshot["source"], "generated_at": snapshot["generated_at"]})
    assert payload["coverage"] == {"total_sales": 3, "classified_sales": 3, "unclassified_sales": 0, "mapping_coverage_percent": 100.0}
    assert payload["daily"][2]["total_sales"] == 0
    assert sum(row["total_sales"] for row in payload["daily"]) == 3
    assert sum(row["total_sales"] for row in payload["monthly"]) == 3
    assert validate_sales_by_item_class_payload(payload)


def test_current_snapshot_reconciles_current_22297_sales():
    data_dir = Path(__file__).parents[1] / "streamlit_opensea_sales" / "data_opensea_sales"
    payload = build_from_directory(data_dir)["sales_by_item_class"]
    assert payload["coverage"] == {"total_sales": 22297, "classified_sales": 22297, "unclassified_sales": 0, "mapping_coverage_percent": 100.0}
    daily, monthly, classes = payload_to_frames(payload)
    daily_totals = {entry["id"]: int(daily[entry["id"]].sum()) for entry in classes}
    monthly_totals = {entry["id"]: int(monthly[entry["id"]].sum()) for entry in classes}
    assert daily_totals == monthly_totals
    assert [daily_totals[entry["id"]] for entry in classes] == [11128, 6162, 2575, 1036, 1047, 349]


def test_payload_validator_rejects_bad_counts_and_snapshot_identity():
    data_dir = Path(__file__).parents[1] / "streamlit_opensea_sales" / "data_opensea_sales"
    payload = build_from_directory(data_dir)["sales_by_item_class"]
    malformed = json.loads(json.dumps(payload))
    malformed["daily"][0]["counts"][0]["sales"] = -1
    assert not validate_sales_by_item_class_payload(malformed)
    assert not validate_sales_by_item_class_payload(payload, expected_snapshot_identity={"sha256": "b" * 64})


def test_item_class_charts_have_stable_stacked_series_and_single_total_helper():
    data_dir = Path(__file__).parents[1] / "streamlit_opensea_sales" / "data_opensea_sales"
    payload = build_from_directory(data_dir)["sales_by_item_class"]
    daily, monthly, classes = payload_to_frames(payload)
    daily_fig = build_daily_item_class_chart(daily.head(3), classes)
    monthly_fig = build_monthly_item_class_chart(monthly, classes)
    assert [trace.name for trace in daily_fig.data[:-1]] == [entry["name"] for entry in classes]
    assert all(trace.type == "scatter" and trace.stackgroup == "item_classes" for trace in daily_fig.data[:-1])
    assert [trace.name for trace in monthly_fig.data[:-1]] == [entry["name"] for entry in classes]
    assert all(trace.type == "bar" for trace in monthly_fig.data[:-1])
    assert monthly_fig.layout.barmode == "stack"
    assert daily_fig.data[-1].name == monthly_fig.data[-1].name == "Total sales"
    assert daily_fig.data[-1].showlegend is False and monthly_fig.data[-1].showlegend is False
    assert all("Total sales" not in (trace.hovertemplate or "") for trace in daily_fig.data[:-1] + monthly_fig.data[:-1])
    assert [trace.line.color for trace in daily_fig.data[:-1]] == [entry["color"] for entry in classes]
    assert [trace.marker.color for trace in monthly_fig.data[:-1]] == [entry["color"] for entry in classes]


def test_snapshot_identity_is_hash_of_exact_bytes(tmp_path):
    path = tmp_path / "item_class_snapshot.json"
    path.write_text(json.dumps(_snapshot()), encoding="utf-8")
    payload, mapping, identity = read_item_class_snapshot(path)
    assert payload["items"] and mapping["Alpha"] == "Weapon"
    assert len(identity["sha256"]) == 64
