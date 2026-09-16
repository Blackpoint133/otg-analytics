import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]
OPS = ROOT / "ops" / "production"
SANDBOX = Path(r"C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110")
PRODUCTION = Path(r"C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales")


def run_ps(name, *args):
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(OPS / name),
            *map(str, args),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def run_sandbox():
    result = run_ps("validate_production_tooling_sandbox.ps1", "-Execute")
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_shared_sandbox_proves_first_deploy_without_active_runtime_and_listenerless_rollback():
    output = run_sandbox()
    assert "SANDBOX_ACTIVE_RUNTIME_ABSENT_BEFORE=PASS" in output
    assert "SANDBOX_DERIVED_REFRESH_EXECUTION_TEST=PASS" in output
    assert "SANDBOX_METADATA_REFRESH_EXECUTION_TEST=PASS" in output
    assert "SANDBOX_ACTIVE_RUNTIME_POST_HEALTH=PASS" in output
    assert "SANDBOX_LISTENERLESS_ROLLBACK=PASS" in output
    assert "SANDBOX_DEPLOY_FAILURE_AUTO_ROLLBACK=PASS" in output
    assert "SANDBOX_MUTATION_TELEMETRY=PASS" in output
    assert "SANDBOX_STATE_RESTORED=PASS" in output
    assert not (SANDBOX / "runtime" / "ACTIVE_RUNTIME.json").exists()


def test_wrong_approval_is_rejected_before_simulation_mutation():
    run_sandbox()
    state_path = SANDBOX / "simulation_state.json"
    before = state_path.read_bytes()
    backup_count_before = len(list((SANDBOX / "backups").glob("*/BACKUP_MANIFEST.json")))
    result = run_ps(
        "backup_production.ps1",
        "-Execute",
        "-Simulation",
        "-SimulationRoot",
        SANDBOX,
        "-SimulationPort",
        18502,
        "-ApprovalPhrase",
        "WRONG",
    )
    assert result.returncode != 0
    assert "APPROVAL_PHRASE_REQUIRED" in result.stdout + result.stderr
    assert "MUTATION_EXECUTED=NO" in result.stdout
    assert state_path.read_bytes() == before
    assert len(list((SANDBOX / "backups").glob("*/BACKUP_MANIFEST.json"))) == backup_count_before


def test_deployment_runtime_override_requires_exact_final_path():
    common = OPS / "production_update_common.ps1"
    powershell = os.environ.get("WINDIR", r"C:\Windows") + r"\System32\WindowsPowerShell\v1.0\powershell.exe"
    command = f"""
. '{common}';
$ctx=New-ProductionExecutionContext @{{ExpectedOldHead='old';ExpectedReleaseHead='release';PreparedReleaseRoot='x';PreparedReleaseManifest='x';PreparedReleaseManifestSha256='x';BackupManifest='x';BackupRoot='x'}};
$ctx.DeploymentRefreshPython='{powershell}';
try {{ Get-RefreshPython $ctx | Out-Null; 'ACCEPTED' }} catch {{ 'REJECTED:' + $_.Exception.Message }}
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().splitlines()[-1].startswith("REJECTED:FINAL_RUNTIME_PATH_GUARD_FAILED")


def test_real_dry_run_does_not_change_production_state():
    env_path = PRODUCTION / ".env"
    before_env = env_path.read_bytes()
    before_head = subprocess.check_output(
        ["git", "-c", f"safe.directory={PRODUCTION}", "-C", str(PRODUCTION), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    result = run_ps("backup_production.ps1")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "MUTATION_EXECUTED=NO" in result.stdout
    assert env_path.read_bytes() == before_env
    after_head = subprocess.check_output(
        ["git", "-c", f"safe.directory={PRODUCTION}", "-C", str(PRODUCTION), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    assert after_head == before_head


def test_sandbox_backup_manifest_records_absent_active_runtime_and_six_artifacts():
    run_sandbox()
    manifests = sorted((SANDBOX / "backups").glob("*/BACKUP_MANIFEST.json"))
    assert manifests
    manifest = json.loads(manifests[-1].read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 2
    assert manifest["backup_complete"] is True
    assert manifest["active_runtime_existed"] is False
    assert len(manifest["dynamic_artifacts"]) == 6
    assert {entry["existed_before"] for entry in manifest["dynamic_artifacts"]} == {False, True}
