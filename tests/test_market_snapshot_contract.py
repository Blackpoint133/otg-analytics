import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts import build_market_expansion_metrics as expansion
from scripts import build_market_period_summaries as period
from scripts.market_snapshot_contract import inspect_market_snapshot
from ops.production.validate_prepared_snapshot import INTEGRITY_FILES, sales_enriched_snapshot_sha256, sha256_file, validate


def _snapshot(tmp_path, *, raw_date="2026-09-15T20:55:03Z", daily_date="2026-09-15", month_end="2026-09-30", build_id="build-1"):
    data = tmp_path / "data"
    raw_sales = data / "sales"
    sales = data / "sales_enriched"
    overview = data / "market_overview_enriched"
    price_history = data / "price_history"
    raw_sales.mkdir(parents=True)
    sales.mkdir(parents=True)
    overview.mkdir(parents=True)
    price_history.mkdir(parents=True)
    csv = (
        "sale_date,seller,buyer,price_gun,name,price_usd_at_sale\n"
        f"{raw_date},seller,buyer,1,Item,1\n"
    )
    (raw_sales / "sales.csv").write_text(csv, encoding="utf-8")
    (sales / "sales.csv").write_text(csv, encoding="utf-8")
    (overview / "daily_market_metrics.csv").write_text(
        f"date\n{daily_date}\n", encoding="utf-8"
    )
    (overview / "monthly_market_metrics.csv").write_text(
        f"month,month_start,month_end\n2026-09,2026-09-01,{month_end}\n",
        encoding="utf-8",
    )
    (overview / "market_summary.json").write_text(
        json.dumps({"date_range": {"max_sale_date": raw_date[:10]}}), encoding="utf-8"
    )
    (overview / "market_overview_enriched_manifest.json").write_text(
        json.dumps({"created_at_utc": build_id}), encoding="utf-8"
    )
    (data / "item_class_snapshot.json").write_text(
        json.dumps({"schema_version": 1, "source": "test", "generated_at": "2026-09-15T00:00:00Z", "items": {"Item": {"class": "Weapon"}}}),
        encoding="utf-8",
    )
    (price_history / "gun_usd_price_history.csv").write_text(
        "date,price_usd\n2026-09-15,0.03\n", encoding="utf-8"
    )
    return data


def _frames(data):
    sales = pd.read_csv(next((data / "sales_enriched").glob("*.csv")))
    daily = pd.read_csv(data / "market_overview_enriched" / "daily_market_metrics.csv")
    monthly = pd.read_csv(data / "market_overview_enriched" / "monthly_market_metrics.csv")
    return sales, daily, monthly


def test_coherent_snapshot_contract_reports_dates_and_build_id(tmp_path):
    data = _snapshot(tmp_path)
    result = inspect_market_snapshot(data)
    assert result["raw_latest_timestamp"] == "2026-09-15T20:55:03Z"
    assert result["raw_latest_date"] == "2026-09-15"
    assert result["daily_latest_date"] == "2026-09-15"
    assert result["monthly_coverage_end"] == "2026-09-30"
    assert result["market_build_id"] == "build-1"


def test_stale_axis_fails_period_builder_before_output(tmp_path):
    data = _snapshot(tmp_path, daily_date="2026-09-01")
    sales, daily, _ = _frames(data)
    with pytest.raises(ValueError, match="MARKET_BASE_SNAPSHOT_STALE"):
        period.build_payload(sales, daily)


def test_stale_axis_fails_expansion_builder_before_output(tmp_path):
    data = _snapshot(tmp_path, daily_date="2026-09-01")
    sales, daily, monthly = _frames(data)
    with pytest.raises(ValueError, match="MARKET_BASE_SNAPSHOT_STALE"):
        expansion.build_payload(sales, daily, monthly, "build-1")


def test_monthly_coverage_must_include_raw_latest(tmp_path):
    data = _snapshot(tmp_path, month_end="2026-09-01")
    with pytest.raises(ValueError, match="MARKET_MONTHLY_COVERAGE_MISSING_RAW_LATEST"):
        inspect_market_snapshot(data)


def test_market_build_identity_is_required(tmp_path):
    data = _snapshot(tmp_path, build_id="")
    with pytest.raises(ValueError, match="MARKET_BUILD_ID_MISSING"):
        inspect_market_snapshot(data)


def test_refresh_publishes_fresh_base_before_builders(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "refresh_common_data_for_snapshot_test",
        Path(__file__).parents[1] / "scripts" / "refresh_common_data.py",
    )
    refresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(refresh)
    source = _snapshot(tmp_path / "source")
    target = _snapshot(tmp_path / "target", daily_date="2026-09-01", month_end="2026-09-30")
    target_overview = target / "market_overview_enriched"
    (target_overview / "market_summary.json").write_text(
        json.dumps({"date_range": {"max_sale_date": "2026-09-01"}}), encoding="utf-8"
    )
    calls = []

    def fake_builder(command, **kwargs):
        calls.append(Path(command[1]).name)
        if command[1].endswith("build_trader_analytics.py"):
            (target / "trader_analytics_snapshot.json").write_text(
                json.dumps({"date_max": "2026-09-15T20:55:03Z"}), encoding="utf-8"
            )

    monkeypatch.setattr(refresh.subprocess, "run", fake_builder)
    monkeypatch.setattr(refresh, "write_log", lambda **kwargs: None)
    refresh.run(source, target)
    assert inspect_market_snapshot(target)["daily_latest_date"] == "2026-09-15"
    assert calls == [
        "build_market_period_summaries.py",
        "build_market_expansion_metrics.py",
        "build_trader_analytics.py",
    ]


def test_stale_authoritative_source_fails_closed_before_sync(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "refresh_common_data_stale_source_test",
        Path(__file__).parents[1] / "scripts" / "refresh_common_data.py",
    )
    refresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(refresh)
    source = _snapshot(tmp_path / "source", daily_date="2026-09-01")
    target = _snapshot(tmp_path / "target", daily_date="2026-09-01")
    monkeypatch.setattr(refresh, "write_log", lambda **kwargs: None)
    with pytest.raises(ValueError, match="MARKET_BASE_SNAPSHOT_STALE"):
        refresh.run(source, target)


def _integrity_manifest(data):
    contract = inspect_market_snapshot(data)
    files = {
        name: sha256_file(data / relative)
        for name, relative in INTEGRITY_FILES.items()
    }
    return {
        "prepared_data_integrity": {
            "prepared_raw_max_sale_timestamp": contract["raw_latest_timestamp"],
            "prepared_raw_max_sale_date": contract["raw_latest_date"],
            "prepared_daily_market_max_date": contract["daily_latest_date"],
            "prepared_monthly_market_coverage_end": contract["monthly_coverage_end"],
            "prepared_market_build_id": contract["market_build_id"],
            "sales_enriched_snapshot_sha256": sales_enriched_snapshot_sha256(data),
            "files": files,
        }
    }


def test_final_tree_integrity_manifest_detects_post_validation_mutation(tmp_path):
    data = _snapshot(tmp_path)
    for relative in INTEGRITY_FILES.values():
        path = data / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("{}", encoding="utf-8")
    manifest_path = tmp_path / "PREPARED_RELEASE_MANIFEST.json"
    manifest_path.write_text(json.dumps(_integrity_manifest(data)), encoding="utf-8")
    validate(manifest_path, tmp_path, data)
    (data / INTEGRITY_FILES["market_period_summaries"]).write_text('{"changed":true}', encoding="utf-8")
    with pytest.raises(ValueError, match="(PREPARED_DATA_INTEGRITY_MISMATCH|MARKET_SUMMARY_RAW_DATE_MISMATCH)"):
        validate(manifest_path, tmp_path, data)


def test_final_tree_integrity_detects_sales_copied_after_artifacts(tmp_path):
    data = _snapshot(tmp_path)
    for relative in INTEGRITY_FILES.values():
        path = data / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("{}", encoding="utf-8")
    manifest_path = tmp_path / "PREPARED_RELEASE_MANIFEST.json"
    manifest_path.write_text(json.dumps(_integrity_manifest(data)), encoding="utf-8")
    (data / "sales_enriched" / "later.csv").write_text(
        "sale_date,seller,buyer,price_gun,name,price_usd_at_sale\n2026-09-16T00:00:00Z,s,b,1,N,1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="(PREPARED_DATA_INTEGRITY_MISMATCH|MARKET_SUMMARY_RAW_DATE_MISMATCH)"):
        validate(manifest_path, tmp_path, data)
