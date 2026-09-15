import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
OPS = ROOT / "ops" / "production"


def ps1(name, *args):
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(OPS / name), *map(str, args)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_public_entrypoints_dispatch_to_one_orchestrator():
    orchestrator = (OPS / "production_update_orchestrator.ps1").read_text(encoding="utf-8")
    common = (OPS / "production_update_common.ps1").read_text(encoding="utf-8")
    for name in (
        "backup_production.ps1",
        "deploy_production.ps1",
        "rollback_production.ps1",
        "refresh_production_derived.ps1",
        "refresh_production_metadata.ps1",
        "configure_production_refresh_tasks.ps1",
    ):
        text = (OPS / name).read_text(encoding="utf-8")
        assert "production_update_orchestrator.ps1" in text
        assert "[switch]$Execute" in text
    for core in (
        "Invoke-BackupCore",
        "Invoke-DerivedRefreshCore",
        "Invoke-MetadataRefreshCore",
        "Invoke-TaskConfigurationCore",
        "Invoke-DeployCore",
        "Invoke-RollbackCore",
    ):
        assert f"function {core}" in common
        assert core in orchestrator
    assert "PRODUCTION_EXECUTE_REQUIRES_COMPLETED_RELEASE_VALIDATION" not in common
    assert "PRODUCTION_ROLLBACK_REQUIRES_MANIFEST_RESTORE_IMPLEMENTATION" not in common


def test_default_real_entrypoints_are_read_only():
    result = ps1("backup_production.ps1")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "MODE=DRY_RUN" in result.stdout
    assert "MUTATION_EXECUTED=NO" in result.stdout


def test_production_guards_and_exact_migration_contract_are_shared():
    common = (OPS / "production_update_common.ps1").read_text(encoding="utf-8")
    assert "ExpectedRoot" in common
    assert "ForbiddenPorts" in common
    assert "app_gaming_marketplace.py" in common
    assert "8501" in common and "8504" in common
    assert r"C:\Program Files\PostgreSQL\18\bin" in common
    assert "sql/add_site_visit_trader_mode.sql" in common
    assert "sql/create_site_product_events.sql" in common
    assert "sql/create_user_feedback.sql" in common
    assert "sql/add_site_product_events_trader_usd_toggle.sql" in common
    assert "MIGRATION_ALLOWLIST_FAILED" in common
    assert "git clean" not in common.lower()
