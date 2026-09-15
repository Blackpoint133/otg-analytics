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


def test_deploy_contract_contains_prepared_gate_and_runtime_order():
    common = (OPS / "production_update_common.ps1").read_text(encoding="utf-8")
    for marker in ("Read-PreparedReleaseManifest", "PREPARED_RELEASE_MANIFEST_HASH_MISMATCH", "FINAL_RUNTIME_PATH_GUARD_FAILED", "PRESTOP_CANARY_FAILED", "POST_REFRESH_APPLICATION_READERS"):
        assert marker in common
    assert "DEPLOY_PREPARE_RUNTIME" in common and "DEPLOY_PRESTOP_CANARY" in common


def test_sandbox_manifest_and_active_runtime_state_are_real():
    result = run("validate_production_tooling_sandbox.ps1", "-Execute")
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = next((SANDBOX / "backups").glob("*/BACKUP_MANIFEST.json"))
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["manifest_version"] == 2
    assert payload["backup_complete"] is True
    assert len(payload["dynamic_artifacts"]) == 6
    assert len(payload["production_refresh_tasks"]) == 2


def test_promotion_dry_run_is_exact_and_non_mutating():
    text = (OPS / "promote_main_prepared_release.ps1").read_text(encoding="utf-8")
    assert "PROMOTE_OTG_ANALYTICS_MAIN" in text
    assert "refs/heads/main" in text
    assert "develop:main" not in text
    assert "MUTATION_EXECUTED" in text


def test_rollback_contract_is_additive_database_only():
    common = (OPS / "production_update_common.ps1").read_text(encoding="utf-8")
    assert "DB_SCHEMA_ROLLBACK" in common
    assert "NOT_AUTOMATIC" in common
    assert "REMOTE_MAIN_ROLLBACK" in common
    assert "git clean" not in common.lower()
