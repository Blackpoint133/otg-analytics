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


def test_refresh_dry_runs_are_mutation_free_and_task_plan_is_exact():
    derived = run("refresh_production_derived.ps1", "-ReleasePython", "C:\\Python311\\python.exe")
    metadata = run("refresh_production_metadata.ps1", "-ReleasePython", "C:\\Python311\\python.exe")
    tasks = run("configure_production_refresh_tasks.ps1", "-ReleasePython", "C:\\Python311\\python.exe")
    for result in (derived, metadata, tasks):
        assert result.returncode == 0, result.stdout + result.stderr
        assert "MODE=DRY_RUN" in result.stdout
        assert "MUTATION_EXECUTED=NO" in result.stdout
    assert "OTG_Derived_Data_Refresh_Production" in tasks.stdout
    assert "OTG_Metadata_Refresh_Production" in tasks.stdout
    assert '"interval_minutes":15' in tasks.stdout
    assert '"interval_minutes":60' in tasks.stdout
    assert '"multiple_instances":"IgnoreNew"' in tasks.stdout
    assert '"start_when_available":true' in tasks.stdout


def test_refresh_cores_are_ordered_and_use_release_python():
    common = (OPS / "production_update_common.ps1").read_text(encoding="utf-8")
    for marker in (
        "market_period",
        "market_expansion",
        "trader_analytics",
        "item_class",
        "gunzscope_v3",
        "profile_sync",
        "RELEASE_PYTHON_MISSING",
    ):
        assert marker in common
    assert common.index("market_period") < common.index("market_expansion") < common.index("trader_analytics")
    assert common.index("item_class") < common.index("gunzscope_v3") < common.index("profile_sync")


def test_simulation_task_collision_is_fail_closed():
    common = (OPS / "production_update_common.ps1").read_text(encoding="utf-8")
    assert "TASK_COLLISION" in common
    assert "PRODUCTION_REFRESH_TASK_COLLISION_POLICY" in common
