from pathlib import Path

ROOT = Path(__file__).parents[1]
OPS = ROOT / "ops/production"

def test_refresh_tasks_are_separate_and_guarded():
    derived = (OPS / "refresh_production_derived.ps1").read_text()
    metadata = (OPS / "refresh_production_metadata.ps1").read_text()
    tasks = (OPS / "configure_production_refresh_tasks.ps1").read_text()
    assert "OTG_Derived_Data_Refresh_Production" in derived + tasks
    assert "OTG_Metadata_Refresh_Production" in metadata + tasks
    assert "REFRESH_OTG_DERIVED_8502" in derived
    assert "REFRESH_OTG_METADATA_8502" in metadata
    assert "EVERY_15_MINUTES" in tasks and "EVERY_60_MINUTES" in tasks
    assert "FAIL_CLOSED" in tasks
    assert "STAGING_TASKS_TOUCHED=NO" in tasks

def test_common_module_centralizes_guards_and_env_mapping():
    text = (OPS / "production_update_common.ps1").read_text()
    assert "Assert-ProductionTarget" in text
    assert "ForbiddenPorts" in text
    assert "CaddyMutationAllowed" in text
    assert "Get-PostgresTools" in text
    assert "Get-8502Process" in text
    assert "Get-SafeEnv" in text
    assert "PGPASSWORD" not in text  # common module does not expose secrets

def test_execute_paths_require_approval_and_guarded_dispatch():
    for name in ("backup_production.ps1", "deploy_production.ps1", "rollback_production.ps1", "refresh_production_derived.ps1", "refresh_production_metadata.ps1", "configure_production_refresh_tasks.ps1"):
        text = (OPS / name).read_text()
        assert "Assert-Approval" in text
        assert "Invoke-GuardedAction" in text
        assert "MUTATION_EXECUTED" in text
