import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]
OPS = ROOT / "ops" / "production"
COMMON = OPS / "production_update_common.ps1"


def run_ps(command: str):
    powershell = os.environ.get("WINDIR", r"C:\Windows") + r"\System32\WindowsPowerShell\v1.0\powershell.exe"
    return subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        text=True,
        capture_output=True,
        check=False,
    )


def ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def test_supervisor_backup_contract_rejects_missing_required_state(tmp_path):
    script = f"""
. {ps(str(COMMON))}
$ctx=[pscustomobject]@{{Mode='SIMULATION';Root={ps(str(tmp_path))};Port=18520;AppPath={ps(str(tmp_path / 'app.py'))};SupervisorServiceName='SANDBOX_NSSM';SupervisorAppDirectory={ps(str(tmp_path))}}}
$base={ps(str(tmp_path))};New-Item -ItemType Directory -Path $base -Force|Out-Null
$manifest=[ordered]@{{manifest_version=2;backup_complete=$true;target_root=$ctx.Root;target_port=18520;target_app=$ctx.AppPath;env_backup_relative_path='env';git_bundle_relative_path='bundle';db_dump_relative_path='dump';env_sha256='x';git_bundle_sha256='x';db_dump_sha256='x';db_dump_format='custom';db_dump_validation='PASS';dynamic_artifacts=@();production_refresh_tasks=@();supervisor=[ordered]@{{service_name='SANDBOX_NSSM'}}}}
Write-AtomicJson (Join-Path $base 'bad.json') $manifest
try {{ Read-BackupManifest (Join-Path $base 'bad.json') $ctx; 'UNEXPECTED_PASS' }} catch {{ 'REJECTED='+$_.Exception.Message }}
"""
    result = run_ps(script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "REJECTED=BACKUP_SUPERVISOR_STATE_INCOMPLETE" in result.stdout


def test_real_nssm_sandbox_proves_service_ownership_respawn_cutover_and_rollback():
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(OPS / "validate_production_supervisor_sandbox.ps1"),
            "-Execute",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    output = result.stdout
    for marker in (
        "SANDBOX_NSSM_RESPAWN_REPRODUCTION=PASS",
        "SANDBOX_SUPERVISOR_BACKUP=PASS",
        "SANDBOX_SUPERVISOR_STOP=PASS",
        "SANDBOX_PORT_RELEASE=PASS",
        "SANDBOX_SUPERVISOR_RECONFIGURE=PASS",
        "SANDBOX_SUPERVISOR_START=PASS",
        "SANDBOX_NEW_CHILD_IDENTITY=PASS",
        "SANDBOX_NEW_CHILD_HEALTH=PASS",
        "SANDBOX_CURRENT_LOG_GATE=PASS",
        "SANDBOX_STALE_LOG_IGNORED=PASS",
        "SANDBOX_THEME_CONTRACT=PASS",
        "SANDBOX_INVALID_THEME_FAIL_CLOSED=PASS",
        "SANDBOX_SOURCE_OWNERSHIP=PASS",
        "SANDBOX_SOURCE_THEME_BASE=MISSING",
        "SANDBOX_CORRECTION_PREFLIGHT=PASS",
        "SANDBOX_ROLLBACK_CONFIG_RESTORE=PASS",
        "SANDBOX_ROLLBACK_CHILD_IDENTITY=PASS",
        "SANDBOX_ROLLBACK_SOURCE_THEME=LEGACY_MISSING_RESTORED",
        "SANDBOX_ROLLBACK_HEALTH=PASS",
        "SANDBOX_ROLLBACK_LOG_GATE=PASS",
        "SANDBOX_ROLLBACK_STATE_RESTORED=PASS",
        "SANDBOX_FOREIGN_LISTENER_GATE=PASS",
        "SANDBOX_FOREIGN_PROCESS_UNTOUCHED=YES",
        "SANDBOX_SERVICE_LEFTOVER=NO",
        "SANDBOX_PROCESS_LEFTOVER=NO",
        "SANDBOX_LISTENER_LEFTOVER=NO",
    ):
        assert marker in output


def test_production_supervisor_source_policy_accepts_legacy_but_activation_remains_strict():
    root = Path(os.environ.get("TEMP", str(ROOT / ".test-temp"))) / "otg-supervisor-source-policy"
    script = f"""
. {ps(str(COMMON))}
$root={ps(str(root))};$app=Join-Path $root 'streamlit_opensea_sales/app_opensea_sales.py';$python=Join-Path $root '.venv/Scripts/python.exe';New-Item -ItemType Directory -Path (Split-Path $app), (Split-Path $python) -Force|Out-Null;New-Item -ItemType File -Path $app,$python -Force|Out-Null
$ctx=[pscustomobject]@{{SupervisorServiceName='SANDBOX_NSSM';SupervisorAppDirectory=(Split-Path $app);Port=18520}}
$config=[pscustomobject]@{{ServiceName='SANDBOX_NSSM';NssmExecutable='C:/sandbox/nssm.exe';AppDirectory=(Split-Path $app);Application=$python;AppParameters='-m streamlit run app_opensea_sales.py --server.address 127.0.0.1 --server.port 18520 --server.fileWatcherType none --server.headless true --browser.gatherUsageStats false';ServiceState='Running'}}
try {{ $source=Assert-ProductionSupervisorOwnershipIdentity $ctx $config -RequireRunning -AllowLegacyMissingThemeSource; 'SOURCE='+$source.SourceThemeBase+'/'+$source.SourceThemeContract; try {{ $null=Assert-ProductionSupervisorActivationIdentity $ctx $config -RequireRunning; 'UNEXPECTED_STRICT_PASS' }} catch {{ 'STRICT_REJECTED='+$_.Exception.Message }} }} catch {{ 'SOURCE_REJECTED='+$_.Exception.Message }}
"""
    result = run_ps(script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SOURCE_REJECTED=" not in result.stdout
    assert "SOURCE=MISSING/KNOWN_LEGACY_DRIFT" in result.stdout
    assert "STRICT_REJECTED=SUPERVISOR_THEME_BASE_DARK_REQUIRED" in result.stdout
    assert "UNEXPECTED_STRICT_PASS" not in result.stdout


def test_nssm_supervisor_contract_is_explicit_and_production_lifecycle_is_not_direct_pid_control():
    source = COMMON.read_text(encoding="utf-8")
    assert "function Get-ProductionSupervisor" in source
    assert "function Stop-ProductionSupervisor" in source
    assert "function Set-ProductionSupervisorReleaseConfiguration" in source
    assert "function Start-ProductionSupervisor" in source
    assert "Stop-Service -Name (Get-SupervisorServiceName $Context)" in source
    lifecycle = source.split("function Start-ContextProcess", 1)[1].split("function Invoke-HealthCheck", 1)[0]
    assert "Start-RedirectedProcess" not in lifecycle
    assert "Stop-Process -Id $process" not in lifecycle
