import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]
OPS = ROOT / "ops" / "production"
COMMON = OPS / "production_update_common.ps1"


def run_ps(script: str):
    powershell = os.environ.get("WINDIR", r"C:\Windows") + r"\System32\WindowsPowerShell\v1.0\powershell.exe"
    return subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        text=True,
        capture_output=True,
        check=False,
    )


def ps_path(path: Path) -> str:
    return str(path).replace("'", "''")


def receipt_script(change: str = "") -> str:
    common = ps_path(COMMON)
    return f"""
. '{common}';
$r=[ordered]@{{release='release';runtime='python.exe';child_pid=18502;health='PASS';theme_base='dark';theme_contract='PASS';profile_key_source='OPENSEA_PROFILE_API_KEY';profile_sync_contract='PASS';profile_sync_state_present=$true;profile_sync_state_gate='PASS';profile_coverage_gate='PASS';profile_reader_gate='PASS';profile_count=1343;profile_ok_count=1330;profile_human_username_count=938;profile_human_display_name_count=979;profile_remote_avatar_count=628;metadata_refresh_result='PASS';profile_sync_attempted=20;profile_sync_successful=20;profile_sync_not_found=0;profile_sync_errors=0;profile_sync_rate_limited=0;profile_sync_health='PASS';secret_leak_gate='PASS'}};
{change}
try {{ Assert-DeploymentReceipt $r $true; 'PASS' }} catch {{ 'FAIL='+$_.Exception.Message }}
"""


def test_complete_profile_receipt_passes():
    result = run_ps(receipt_script())
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().endswith("PASS")


def test_profile_receipt_required_fields_and_contract_fail_closed():
    cases = {
        "profile_key_source": "",
        "profile_sync_state_gate": "",
        "profile_coverage_gate": "FAIL",
        "profile_reader_gate": "FAIL",
        "secret_leak_gate": "FAIL",
    }
    for field, value in cases.items():
        change = f"$r['{field}']='{value}'"
        result = run_ps(receipt_script(change))
        assert result.returncode == 0, result.stdout + result.stderr
        assert "FAIL=" in result.stdout, (field, result.stdout, result.stderr)

    missing = run_ps(receipt_script("$r.Remove('profile_key_source')"))
    assert missing.returncode == 0, missing.stdout + missing.stderr
    assert "DEPLOYMENT_RECEIPT_PROFILE_FIELD_MISSING:profile_key_source" in missing.stdout


def test_receipt_does_not_accept_fallback_or_secret_looking_profile_source():
    for value in ("OPENSEA_API_KEY_FALLBACK", "super-secret-api-key-value"):
        result = run_ps(receipt_script(f"$r['profile_key_source']='{value}'"))
        assert result.returncode == 0, result.stdout + result.stderr
        assert "FAIL=DEPLOYMENT_RECEIPT_PROFILE_CONTRACT_FAILED" in result.stdout
    result = run_ps(receipt_script("$r['api_key']='secret-value'"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "FAIL=DEPLOYMENT_RECEIPT_SECRET_FIELD_FORBIDDEN" in result.stdout


def test_historical_receipt_remains_compatible():
    common = ps_path(COMMON)
    result = run_ps(
        f"""
. '{common}';
$r=[ordered]@{{streamlit_theme_base='dark';theme_contract='PASS'}};
try {{ Assert-DeploymentReceipt $r $false; 'PASS' }} catch {{ 'FAIL='+$_.Exception.Message }}
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().endswith("PASS")


def test_profile_sync_capability_is_semantic_not_sha_bound():
    common = ps_path(COMMON)
    result = run_ps(
        f"""
. '{common}';
$m=[pscustomobject]@{{profile_api_key_contract=[pscustomobject]@{{preferred_variable='OPENSEA_PROFILE_API_KEY';fallback_variable='OPENSEA_API_KEY';legacy_variable_ignored='OPENSEA_API_OLD';secret_values_in_manifest='NO'}}}};
Write-Output ('CAPABILITY='+[string](Test-ProfileSyncReleaseCapability $m));
Write-Output ('HISTORICAL='+[string](Test-ProfileSyncReleaseCapability ([pscustomobject]@{{}})))
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CAPABILITY=True" in result.stdout
    assert "HISTORICAL=False" in result.stdout


def test_existing_tooling_sandbox_covers_optional_sidecar_and_receipt_contract():
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(OPS / "validate_production_tooling_sandbox.ps1"), "-Execute"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for marker in (
        "SANDBOX_ABSENT_PROFILE_SYNC_ROLLBACK=PASS",
        "SANDBOX_PRESENT_PROFILE_SYNC_BACKUP=PASS",
        "SANDBOX_PRESENT_PROFILE_SYNC_ROLLBACK=PASS",
        "SANDBOX_REPEATED_ROLLBACK=PASS",
        "SANDBOX_PROFILE_SNAPSHOT_INDEPENDENCE=PASS",
        "SANDBOX_THEME_CONTRACT=PASS",
    ):
        assert marker in result.stdout

    manifests = list(Path(r"C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110\backups").glob("*/BACKUP_MANIFEST.json"))
    manifest = next(path for path in manifests if json.loads(path.read_text(encoding="utf-8"))["profile_sync_state_existed_before"] is False)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["profile_sync_state_contract"] == "OPTIONAL_SIDECAR_V1"
    assert payload["profile_sync_state_existed_before"] is False


def _validate_backup_copy(manifest: Path, copy_root: Path) -> str:
    backup_copy = copy_root / "backup"
    shutil.copytree(manifest.parent, backup_copy)
    copied_manifest = backup_copy / "BACKUP_MANIFEST.json"
    common = ps_path(COMMON)
    root = r"C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110"
    script = f"""
. '{common}';
$ctx=New-SimulationExecutionContext @{{SimulationRoot='{root}';SimulationPort=18502;ExpectedOldHead='old';ExpectedReleaseHead='release';PreparedReleaseManifest='';PreparedReleaseManifestSha256='';BackupManifest='{ps_path(copied_manifest)}';BackupRoot='{ps_path(backup_copy)}'}};
try {{ Read-BackupManifest '{ps_path(copied_manifest)}' $ctx | Out-Null; 'PASS' }} catch {{ 'FAIL='+$_.Exception.Message }}
"""
    result = run_ps(script)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip().splitlines()[-1]


def test_profile_sync_backup_manifest_tamper_and_presence_guards(tmp_path):
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(OPS / "validate_production_tooling_sandbox.ps1"), "-Execute"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    backup_root = Path(r"C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110\backups")
    manifests = [path for path in backup_root.glob("*/BACKUP_MANIFEST.json") if json.loads(path.read_text(encoding="utf-8"))["profile_sync_state_existed_before"]]
    assert manifests
    present = manifests[0]

    tampered_hash = tmp_path / "tampered_hash"
    shutil.copytree(present.parent, tampered_hash)
    tampered_manifest = tampered_hash / "BACKUP_MANIFEST.json"
    payload = json.loads(tampered_manifest.read_text(encoding="utf-8"))
    payload["profile_sync_state_sha256"] = "0" * 64
    tampered_manifest.write_text(json.dumps(payload), encoding="utf-8")
    assert "FAIL=BACKUP_PROFILE_SYNC_STATE_HASH_MISMATCH" in _validate_backup_copy(tampered_manifest, tmp_path / "hash_copy")

    missing_file = tmp_path / "missing_file"
    shutil.copytree(present.parent, missing_file)
    (missing_file / "artifacts" / "opensea_account_profile_sync_state.json").unlink()
    assert "FAIL=BACKUP_PROFILE_SYNC_STATE_HASH_MISMATCH" in _validate_backup_copy(missing_file / "BACKUP_MANIFEST.json", tmp_path / "missing_copy")
