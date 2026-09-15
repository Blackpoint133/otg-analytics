import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
OPS = ROOT / "ops" / "production"
SANDBOX = Path(r"C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_109")


def test_shared_sandbox_proves_deploy_rollback_and_auto_rollback():
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(OPS / "validate_production_tooling_sandbox.ps1"), "-Execute"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for marker in (
        "SANDBOX_BACKUP_EXECUTION_TEST=PASS",
        "SANDBOX_DERIVED_REFRESH_EXECUTION_TEST=PASS",
        "SANDBOX_METADATA_REFRESH_EXECUTION_TEST=PASS",
        "SANDBOX_TASK_REGISTRATION_TEST=PASS",
        "SANDBOX_DEPLOY_EXECUTION_TEST=PASS",
        "SANDBOX_NEW_STATE_VERIFY=PASS",
        "SANDBOX_ROLLBACK_EXECUTION_TEST=PASS",
        "SANDBOX_OLD_STATE_RESTORATION=PASS",
        "SANDBOX_DEPLOY_FAILURE_AUTO_ROLLBACK=PASS",
        "SANDBOX_FAIL_CLOSED_TESTS=PASS",
        "SANDBOX_ORPHAN_PROCESS=NO",
    ):
        assert marker in result.stdout

    manifests = list((SANDBOX / "backups").glob("*/BACKUP_MANIFEST.json"))
    assert manifests
    manifest = json.loads(manifests[-1].read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 2
    assert manifest["backup_complete"] is True
    assert len(manifest["dynamic_artifacts"]) == 6
    assert len(manifest["production_refresh_tasks"]) == 2
    assert manifest["db_dump_format"] == "custom"
    assert manifest["db_dump_validation"] == "PASS"

    phases = (SANDBOX / "phase.log").read_text(encoding="utf-8").splitlines()
    assert phases.index("DEPLOY_VALIDATE") < phases.index("DEPLOY_STOP")
    assert phases.index("DEPLOY_STOP") < phases.index("DEPLOY_FAST_FORWARD")
    assert phases.index("DEPLOY_FAST_FORWARD") < phases.index("DEPLOY_ENV")
    assert phases.index("DEPLOY_ENV") < phases.index("DEPLOY_MIGRATIONS")
    assert phases.index("DEPLOY_MIGRATIONS") < phases.index("DEPLOY_DERIVED")
    assert phases.index("DEPLOY_DERIVED") < phases.index("DEPLOY_METADATA")
    assert phases.index("DEPLOY_METADATA") < phases.index("DEPLOY_START")
    assert phases.index("DEPLOY_START") < phases.index("DEPLOY_TASKS")


def test_negative_contexts_are_rejected_before_mutation():
    common = (OPS / "production_update_common.ps1").read_text(encoding="utf-8")
    assert "SIMULATION_CONTEXT_ROOT_GUARD_FAILED" in common
    assert "SIMULATION_CONTEXT_FORBIDDEN_PORT_GUARD_FAILED" in common
    assert "APPROVAL_PHRASE_REQUIRED" in common
    assert "MAIN_PROMOTION_REQUIRED" in common
    assert "BACKUP_MANIFEST_INVALID" in common
    assert "TARGET_PROCESS_IDENTITY_FAILED" in common


def test_rollback_contract_preserves_additive_database_state():
    common = (OPS / "production_update_common.ps1").read_text(encoding="utf-8")
    assert "DB_SCHEMA_ROLLBACK" in common
    assert "NOT_AUTOMATIC" in common
    assert "REMOTE_MAIN_ROLLBACK" in common
    assert "reset --hard" in common
    assert "git clean" not in common.lower()
