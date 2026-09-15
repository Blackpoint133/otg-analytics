import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
OPS = ROOT / "ops" / "production"


def run(name, *args):
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(OPS / name), *map(str, args)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_refresh_dry_runs_and_task_plan_are_exact():
    derived = run("refresh_production_derived.ps1")
    metadata = run("refresh_production_metadata.ps1")
    tasks = run("configure_production_refresh_tasks.ps1")
    for result in (derived, metadata, tasks):
        assert result.returncode == 0, result.stdout + result.stderr
        assert "MODE=DRY_RUN" in result.stdout
        assert "MUTATION_EXECUTED=NO" in result.stdout
    assert '"interval_minutes":15' in tasks.stdout
    assert '"interval_minutes":60' in tasks.stdout
    assert '"multiple_instances":"IgnoreNew"' in tasks.stdout
    assert '"start_when_available":true' in tasks.stdout


def test_refresh_cores_invoke_all_steps_in_order():
    common = (OPS / "production_update_common.ps1").read_text(encoding="utf-8")
    for marker in ("market_period", "market_expansion", "trader_analytics", "item_class", "gunzscope_v3", "profile_sync"):
        assert marker in common
    assert common.index("market_period") < common.index("market_expansion") < common.index("trader_analytics")
    assert common.index("item_class") < common.index("gunzscope_v3") < common.index("profile_sync")


def test_reader_helper_is_tracked_and_read_only():
    helper = OPS / "validate_dynamic_artifacts.py"
    assert helper.exists()
    text = helper.read_text(encoding="utf-8")
    assert "load_market_period_summaries" in text
    assert "validate_snapshot_v3" in text
    assert "selected_supply_source" in text
    assert "load_current_snapshot" in text
    assert "load_item_class_snapshot" in text
    assert "load_profile_snapshot" in text
