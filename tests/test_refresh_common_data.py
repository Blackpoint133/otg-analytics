from pathlib import Path
import importlib.util
import json
import subprocess

SPEC = importlib.util.spec_from_file_location("refresh_common_data", Path(__file__).parents[1] / "scripts" / "refresh_common_data.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_sync_requires_distinct_existing_paths(tmp_path):
    source = tmp_path / "source"; target = tmp_path / "target"
    source.mkdir(); target.mkdir()
    try:
        MODULE.run(source, source)
    except ValueError:
        pass
    else:
        raise AssertionError("same source and target must be rejected")
    try:
        MODULE.run(source / "missing", target)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing source must be rejected")


def test_sales_files_are_published_without_touching_unrelated_files(tmp_path, monkeypatch):
    source = tmp_path / "source"; target = tmp_path / "target"
    (source / "sales_enriched").mkdir(parents=True); (target / "sales_enriched").mkdir(parents=True)
    (source / "sales_enriched" / "item.csv").write_text("new", encoding="utf-8")
    unrelated = target / "keep.txt"; unrelated.write_text("keep", encoding="utf-8")
    assert MODULE.sync_sales(source, target) == 1
    assert (target / "sales_enriched" / "item.csv").read_text(encoding="utf-8") == "new"
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_no_production_default_and_atomic_publisher(tmp_path):
    source = tmp_path / "source.txt"; target = tmp_path / "target.txt"
    source.write_text("fresh", encoding="utf-8")
    assert MODULE.publish_file(source, target)
    assert target.read_text(encoding="utf-8") == "fresh"


def _dirs(tmp_path, source_date="2026-09-12T18:42:37Z", target_date=None):
    source = tmp_path / "source"; target = tmp_path / "target"
    (source / "sales_enriched").mkdir(parents=True); (target / "sales_enriched").mkdir(parents=True)
    (source / "sales_enriched" / "one.csv").write_text(f"sale_date\n{source_date}\n", encoding="utf-8")
    if target_date is not None:
        (target / "sales_enriched" / "one.csv").write_text(f"sale_date\n{target_date}\n", encoding="utf-8")
    return source, target


def _snapshot(target, date_max="2026-09-12T18:42:37Z"):
    (target / "trader_analytics_snapshot.json").write_text(json.dumps({"date_max": date_max}), encoding="utf-8")


def test_identical_file_is_not_rewritten(tmp_path):
    source, target = _dirs(tmp_path); content = (source / "sales_enriched" / "one.csv").read_text()
    (target / "sales_enriched" / "one.csv").write_text(content)
    assert MODULE.sync_sales(source, target) == 0
    assert (target / "sales_enriched" / "one.csv").read_text() == content


def test_get_sales_date_max_uses_newest_valid_timestamp(tmp_path):
    source, _ = _dirs(tmp_path)
    (source / "sales_enriched" / "two.csv").write_text("sale_date\nnot-a-date\n2026-09-12T18:42:37Z\n", encoding="utf-8")
    assert MODULE.get_sales_date_max(source).isoformat() == "2026-09-12T18:42:37+00:00"


def test_no_parseable_source_dates_stops_before_builders(tmp_path, monkeypatch):
    source, target = _dirs(tmp_path, "invalid")
    calls = []; monkeypatch.setattr(MODULE.subprocess, "run", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(MODULE, "write_log", lambda **k: calls.append(k))
    try: MODULE.run(source, target)
    except ValueError: pass
    else: raise AssertionError("invalid source must fail")
    assert not any(isinstance(x, tuple) for x in calls)


def test_stale_target_stops_before_builders(tmp_path, monkeypatch):
    source, target = _dirs(tmp_path, target_date="2026-09-11T00:00:00Z")
    monkeypatch.setattr(MODULE, "sync_sales", lambda *_: 0)
    calls = []; monkeypatch.setattr(MODULE.subprocess, "run", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(MODULE, "write_log", lambda **k: calls.append(k))
    try: MODULE.run(source, target)
    except ValueError: pass
    else: raise AssertionError("stale target must fail")
    assert calls == [{"status": "failed", "stage": "target_freshness", "error_type": "ValueError", "duration": calls[0]["duration"]}]


def test_builders_run_in_exact_order(tmp_path, monkeypatch):
    source, target = _dirs(tmp_path); calls = []
    def fake(command, **kwargs):
        calls.append(Path(command[1]).name)
        if command[1].endswith("build_trader_analytics.py"): _snapshot(target)
    monkeypatch.setattr(MODULE.subprocess, "run", fake); monkeypatch.setattr(MODULE, "write_log", lambda **k: None)
    MODULE.run(source, target)
    assert calls == ["build_market_period_summaries.py", "build_market_expansion_metrics.py", "build_trader_analytics.py"]


def _run_failure(tmp_path, monkeypatch, fail_index):
    source, target = _dirs(tmp_path); calls = []
    def fake(command, **kwargs):
        calls.append(Path(command[1]).name)
        if len(calls) - 1 == fail_index: raise subprocess.CalledProcessError(1, command)
        if command[1].endswith("build_trader_analytics.py"): _snapshot(target)
    logs = []; monkeypatch.setattr(MODULE.subprocess, "run", fake); monkeypatch.setattr(MODULE, "write_log", lambda **k: logs.append(k))
    try: MODULE.run(source, target)
    except subprocess.CalledProcessError: pass
    else: raise AssertionError("builder failure must propagate")
    return calls, logs


def test_first_builder_failure_stops_pipeline(tmp_path, monkeypatch):
    calls, _ = _run_failure(tmp_path, monkeypatch, 0)
    assert calls == ["build_market_period_summaries.py"]


def test_second_builder_failure_stops_trader(tmp_path, monkeypatch):
    calls, _ = _run_failure(tmp_path, monkeypatch, 1)
    assert calls == ["build_market_period_summaries.py", "build_market_expansion_metrics.py"]


def test_trader_builder_failure_fails_pipeline(tmp_path, monkeypatch):
    calls, _ = _run_failure(tmp_path, monkeypatch, 2)
    assert len(calls) == 3


def test_missing_snapshot_fails_validation(tmp_path, monkeypatch):
    source, target = _dirs(tmp_path); monkeypatch.setattr(MODULE.subprocess, "run", lambda *a, **k: None); monkeypatch.setattr(MODULE, "write_log", lambda **k: None)
    try: MODULE.run(source, target)
    except FileNotFoundError: pass
    else: raise AssertionError("missing snapshot must fail")


def test_invalid_snapshot_fails_validation(tmp_path, monkeypatch):
    source, target = _dirs(tmp_path); monkeypatch.setattr(MODULE.subprocess, "run", lambda *a, **k: (target / "trader_analytics_snapshot.json").write_text("{", encoding="utf-8")); monkeypatch.setattr(MODULE, "write_log", lambda **k: None)
    try: MODULE.run(source, target)
    except json.JSONDecodeError: pass
    else: raise AssertionError("invalid snapshot must fail")


def test_stale_snapshot_fails_validation(tmp_path):
    _, target = _dirs(tmp_path, target_date="2026-09-12T18:42:37Z"); _snapshot(target, "2026-09-11T00:00:00Z")
    try: MODULE.validate_snapshot(target, MODULE.get_sales_date_max(target))
    except ValueError: pass
    else: raise AssertionError("stale snapshot must fail")


def test_fresh_snapshot_passes_validation(tmp_path):
    _, target = _dirs(tmp_path, target_date="2026-09-12T18:42:37Z"); _snapshot(target)
    MODULE.validate_snapshot(target, MODULE.get_sales_date_max(target))


def test_success_log_emitted_after_validation(tmp_path, monkeypatch):
    source, target = _dirs(tmp_path); _snapshot(target); logs = []
    monkeypatch.setattr(MODULE.subprocess, "run", lambda *a, **k: None); monkeypatch.setattr(MODULE, "write_log", lambda **k: logs.append(k))
    MODULE.run(source, target)
    assert len(logs) == 1 and logs[0]["status"] == "success"


def test_builder_failure_logs_safe_stage(tmp_path, monkeypatch):
    _, logs = _run_failure(tmp_path, monkeypatch, 0)
    assert logs[0]["status"] == "failed" and logs[0]["stage"] == "market_period" and logs[0]["error_type"] == "CalledProcessError"


def test_source_failure_logs_source_stage(tmp_path, monkeypatch):
    source, target = _dirs(tmp_path, "invalid"); logs=[]; monkeypatch.setattr(MODULE, "write_log", lambda **k: logs.append(k))
    try: MODULE.run(source, target)
    except ValueError: pass
    assert logs[0]["stage"] == "source_freshness"


def test_target_failure_logs_target_stage(tmp_path, monkeypatch):
    source, target = _dirs(tmp_path, target_date="2026-09-11T00:00:00Z"); logs=[]; monkeypatch.setattr(MODULE, "sync_sales", lambda *_: 0); monkeypatch.setattr(MODULE, "write_log", lambda **k: logs.append(k))
    try: MODULE.run(source, target)
    except ValueError: pass
    assert logs[0]["stage"] == "target_freshness"


def test_snapshot_failure_logs_snapshot_stage(tmp_path, monkeypatch):
    source, target = _dirs(tmp_path); logs=[]; monkeypatch.setattr(MODULE.subprocess, "run", lambda *a, **k: None); monkeypatch.setattr(MODULE, "write_log", lambda **k: logs.append(k))
    try: MODULE.run(source, target)
    except FileNotFoundError: pass
    assert logs[0]["stage"] == "snapshot_validation"


def test_no_canonical_production_path_is_hardcoded():
    text = (Path(__file__).parents[1] / "scripts" / "refresh_common_data.py").read_text(encoding="utf-8")
    assert "data_streamlit" not in text and "--source" in text and "--target" in text
