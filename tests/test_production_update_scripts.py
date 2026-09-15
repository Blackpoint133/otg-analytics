import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
OPS = ROOT / "ops" / "production"
SANDBOX = Path(r"C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110")


def run(name, *args):
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(OPS / name), *map(str, args)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_entrypoints_use_shared_core_and_are_dry_run_by_default():
    common = (OPS / "production_update_common.ps1").read_text(encoding="utf-8")
    orchestrator = (OPS / "production_update_orchestrator.ps1").read_text(encoding="utf-8")
    for name in ("backup_production.ps1", "deploy_production.ps1", "rollback_production.ps1", "refresh_production_derived.ps1", "refresh_production_metadata.ps1", "configure_production_refresh_tasks.ps1"):
        text = (OPS / name).read_text(encoding="utf-8")
        assert "production_update_orchestrator.ps1" in text
        assert "[switch]$Execute" in text
    for core in ("Invoke-BackupCore", "Invoke-DerivedRefreshCore", "Invoke-MetadataRefreshCore", "Invoke-TaskConfigurationCore", "Invoke-DeployCore", "Invoke-RollbackCore"):
        assert f"function {core}" in common and core in orchestrator
    assert "EXECUTION_REQUIRES_RELEASE_RUNTIME" not in common
    assert "TASK_REGISTRATION_REQUIRES_EXPLICIT_SERVER_EXECUTION_REVIEW" not in common


def test_real_default_backup_is_read_only():
    result = run("backup_production.ps1")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "MODE=DRY_RUN" in result.stdout
    assert "MUTATION_EXECUTED=NO" in result.stdout


def test_guards_and_exact_migrations_are_runtime_contracts():
    common = (OPS / "production_update_common.ps1").read_text(encoding="utf-8")
    assert "SIMULATION_CONTEXT_ROOT_GUARD_FAILED" in common
    assert "SIMULATION_CONTEXT_FORBIDDEN_PORT_GUARD_FAILED" in common
    assert "app_gaming_marketplace.py" in common and "8501" in common and "8504" in common
    assert "sql/add_site_visit_trader_mode.sql" in common
    assert "sql/create_site_product_events.sql" in common
    assert "sql/create_user_feedback.sql" in common
    assert "sql/add_site_product_events_trader_usd_toggle.sql" in common
    assert "MIGRATION_ALLOWLIST_FAILED" in common
    assert "git clean" not in common.lower()


def test_sandbox_proves_exact_head_promotion_and_shared_execution():
    result = run("validate_production_tooling_sandbox.ps1", "-Execute")
    assert result.returncode == 0, result.stdout + result.stderr
    for marker in (
        "SANDBOX_BACKUP_EXECUTION_TEST=PASS",
        "SANDBOX_EXACT_MAIN_PROMOTION=PASS",
        "SANDBOX_DEPLOY_EXECUTION=PASS",
        "SANDBOX_NEW_STATE_VERIFY=PASS",
        "SANDBOX_ROLLBACK_EXECUTION=PASS",
        "SANDBOX_STATE_RESTORED=PASS",
        "SANDBOX_DEPLOY_FAILURE_AUTO_ROLLBACK=PASS",
        "SANDBOX_MUTATION_TELEMETRY=PASS",
        "SANDBOX_FAIL_CLOSED_TESTS=PASS",
        "SANDBOX_ORPHAN_PROCESS=NO",
    ):
        assert marker in result.stdout
    phases = (SANDBOX / "phase.log").read_text(encoding="utf-8").splitlines()
    assert phases.index("DEPLOY_PREPARE_RUNTIME") < phases.index("DEPLOY_PRESTOP_CANARY") < phases.index("DEPLOY_STOP")
    assert phases.index("DEPLOY_STOP") < phases.index("DEPLOY_FAST_FORWARD") < phases.index("DEPLOY_ENV")
    assert phases.index("DEPLOY_RUNTIME_READERS") < phases.index("DEPLOY_START") < phases.index("DEPLOY_TASKS")
    manifests = list((SANDBOX / "backups").glob("*/BACKUP_MANIFEST.json"))
    assert manifests
    manifest = json.loads(manifests[-1].read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 2
    assert manifest["backup_complete"] is True
    assert len(manifest["dynamic_artifacts"]) == 6
    assert len(manifest["production_refresh_tasks"]) == 2


def test_promotion_script_forbids_develop_to_main_literal():
    text = (OPS / "promote_main_prepared_release.ps1").read_text(encoding="utf-8")
    assert "refs/heads/main" in text
    assert "develop:main" not in text
    assert "PROMOTE_OTG_ANALYTICS_MAIN" in text
