import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
COMMON = ROOT / "ops" / "production" / "production_update_common.ps1"


def ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_ps(script: str):
    powershell = os.environ.get("WINDIR", r"C:\Windows") + r"\System32\WindowsPowerShell\v1.0\powershell.exe"
    return subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        text=True,
        capture_output=True,
        check=False,
    )


def context_and_configuration(tmp_path: Path, parameters: str) -> str:
    root = str(tmp_path)
    python = str(Path(sys.executable))
    return f"""
. {ps(str(COMMON))}
$ctx=[pscustomobject]@{{Mode='SIMULATION';Root={ps(root)};RuntimeRoot={ps(root)};AppPath={ps(str(tmp_path / 'app_opensea_sales.py'))};Port=18520;SupervisorServiceName='SANDBOX_NSSM';SupervisorAppDirectory={ps(root)}}}
$configuration=[pscustomobject]@{{ServiceName='SANDBOX_NSSM';NssmExecutable='nssm.exe';AppDirectory={ps(root)};Application={ps(python)};AppParameters={ps(parameters)};ServiceState='Running'}}
"""


def canonical_source_parameters(theme: str = "") -> str:
    base = (
        "-m streamlit run app_opensea_sales.py --server.address 127.0.0.1 "
        "--server.port 18520 --server.fileWatcherType none --server.headless true "
        "--browser.gatherUsageStats false"
    )
    return (base + (" " + theme if theme else "")).strip()


def test_legacy_missing_theme_is_ownership_safe_but_activation_strict(tmp_path):
    parameters = canonical_source_parameters()
    result = run_ps(
        context_and_configuration(tmp_path, parameters)
        + """
$source=Assert-ProductionSupervisorOwnershipIdentity $ctx $configuration -AllowLegacyMissingThemeSource
Write-Output ('SOURCE='+$source.SourceThemeBase+'/'+$source.SourceThemeContract)
try { Assert-ProductionSupervisorActivationIdentity $ctx $configuration | Out-Null; 'UNEXPECTED_ACTIVATION_PASS' }
catch { 'ACTIVATION_REJECTED='+$_.Exception.Message }
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SOURCE=MISSING/KNOWN_LEGACY_DRIFT" in result.stdout
    assert "ACTIVATION_REJECTED=SUPERVISOR_THEME_BASE_DARK_REQUIRED" in result.stdout
    assert "UNEXPECTED_ACTIVATION_PASS" not in result.stdout


def test_source_policy_accepts_only_missing_or_dark_and_rejects_invalid_theme(tmp_path):
    themes = ("", "--theme.base=dark", "--theme.base=light", "--theme.base=blue", "--theme.base=dark --theme.base=light")
    script = ". " + ps(str(COMMON)) + "\n"
    script += f"$ctx=[pscustomobject]@{{Mode='SIMULATION';Root={ps(str(tmp_path))};RuntimeRoot={ps(str(tmp_path))};AppPath={ps(str(tmp_path / 'app_opensea_sales.py'))};Port=18520;SupervisorServiceName='SANDBOX_NSSM';SupervisorAppDirectory={ps(str(tmp_path))}}}\n"
    script += f"$python={ps(str(Path(sys.executable)))}\n"
    for index, theme in enumerate(themes):
        parameters = canonical_source_parameters(theme)
        script += f"$c{index}=[pscustomobject]@{{ServiceName='SANDBOX_NSSM';NssmExecutable='nssm.exe';AppDirectory={ps(str(tmp_path))};Application=$python;AppParameters={ps(parameters)};ServiceState='Running'}}\n"
        script += f"$s{index}=Get-StreamlitThemeBaseState $c{index}.AppParameters;Write-Output ('STATE{index}='+$s{index}.State);try{{Assert-ProductionSupervisorOwnershipIdentity $ctx $c{index} -AllowLegacyMissingThemeSource|Out-Null;Write-Output 'OWN{index}=PASS'}}catch{{Write-Output ('OWN{index}=FAIL:'+ $_.Exception.Message)}}\n"
    result = run_ps(script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "STATE0=MISSING" in result.stdout and "OWN0=PASS" in result.stdout
    assert "STATE1=DARK" in result.stdout and "OWN1=PASS" in result.stdout
    assert "OWN2=FAIL:SUPERVISOR_THEME_BASE_DARK_REQUIRED" in result.stdout
    assert "OWN3=FAIL:SUPERVISOR_THEME_BASE_DARK_REQUIRED" in result.stdout
    assert "OWN4=FAIL:SUPERVISOR_THEME_BASE_DARK_REQUIRED" in result.stdout


def test_source_process_identity_allows_legacy_missing_theme_only_with_explicit_policy(tmp_path):
    command = canonical_source_parameters()
    script = f"""
. {ps(str(COMMON))}
$listener=[pscustomobject]@{{LocalAddress='127.0.0.1';LocalPort=18520;State='Listen';OwningProcess=4242}}
$process=[pscustomobject]@{{ProcessId=4242;ExecutablePath={ps(str(Path(sys.executable)))};CommandLine={ps(command)}}}
$null=Test-8502ProcessIdentity $listener $process {ps(str(tmp_path / 'app_opensea_sales.py'))} '' 18520 -AllowLegacyMissingThemeSource
Write-Output 'SOURCE_PROCESS=PASS'
try {{ Test-8502ProcessIdentity $listener $process {ps(str(tmp_path / 'app_opensea_sales.py'))} '' 18520 | Out-Null; 'UNEXPECTED_STRICT_PASS' }} catch {{ 'STRICT_PROCESS='+$_.Exception.Message }}
"""
    result = run_ps(script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SOURCE_PROCESS=PASS" in result.stdout
    assert "STRICT_PROCESS=SUPERVISOR_THEME_BASE_DARK_REQUIRED" in result.stdout


def test_backup_manifest_accepts_and_preserves_missing_theme_source(tmp_path):
    root = str(tmp_path)
    app = str(tmp_path / "app_opensea_sales.py")
    python = str(Path(sys.executable))
    script = f"""
. {ps(str(COMMON))}
$ctx=[pscustomobject]@{{Mode='SIMULATION';Root={ps(root)};RuntimeRoot={ps(root)};AppPath={ps(app)};Port=18520;SupervisorServiceName='SANDBOX_NSSM';SupervisorAppDirectory={ps(root)}}}
$base={ps(root)};New-Item -ItemType Directory -Path $base -Force|Out-Null
Set-Content (Join-Path $base 'env') 'safe=1';Set-Content (Join-Path $base 'bundle') 'bundle';Set-Content (Join-Path $base 'dump') 'dump'
$super=[pscustomobject]@{{service_name='SANDBOX_NSSM';supervisor_type='NSSM';service_display_name='Sandbox';service_start_mode='Manual';service_was_running=$true;service_binary_path='nssm.exe';nssm_executable='nssm.exe';application={ps(python)};app_directory={ps(root)};app_parameters={ps(canonical_source_parameters())};source_theme_base='MISSING';source_theme_contract='LEGACY_MISSING_ALLOWED_FOR_CORRECTION';app_stdout='out.log';app_stderr='err.log';app_restart_delay='0';app_throttle='1500';app_exit_default='Restart';app_stop_method_console='1500';app_stop_method_window='1500';app_stop_method_threads='1500';app_stop_method_skip='0';app_kill_process_tree='1';app_stdout_share_mode='3';app_stderr_share_mode='3';app_rotate_files='0';app_rotate_online='0';app_rotate_seconds='0';app_rotate_bytes='0';app_timestamp_log='0';windows_service_failure_actions='failure'}}
$super | Add-Member NoteProperty configuration_fingerprint (Get-SupervisorManifestFingerprint $super)
$manifest=[ordered]@{{manifest_version=2;backup_complete=$true;target_root=$ctx.Root;target_port=18520;target_app=$ctx.AppPath;old_git_head='old';old_git_branch='main';old_git_clean=$true;old_process_pid=4242;old_process_executable={ps(python)};old_process_command_line_sanitized={ps(canonical_source_parameters())};old_app_path=$ctx.AppPath;old_port=18520;old_runtime_root=$ctx.RuntimeRoot;supervisor=$super;env_backup_relative_path='env';git_bundle_relative_path='bundle';db_dump_relative_path='dump';db_dump_format='custom';db_dump_validation='PASS';git_bundle_validation='PASS';env_sha256=Get-Sha256 (Join-Path $base 'env');git_bundle_sha256=Get-Sha256 (Join-Path $base 'bundle');db_dump_sha256=Get-Sha256 (Join-Path $base 'dump');dynamic_artifacts=@();active_runtime_existed=$false;production_refresh_tasks=@()}}
for($i=0;$i -lt 6;$i++){{$manifest.dynamic_artifacts+=,[pscustomobject]@{{existed_before=$false}}}}
for($i=0;$i -lt 2;$i++){{$manifest.production_refresh_tasks+=,[pscustomobject]@{{existed_before=$false}}}}
$path=Join-Path $base 'BACKUP_MANIFEST.json';Write-AtomicJson $path $manifest;$read=Read-BackupManifest $path $ctx
Write-Output ('BACKUP_THEME='+$read.Manifest.supervisor.source_theme_base+'/'+$read.Manifest.supervisor.source_theme_contract)
Write-Output ('BACKUP_PARAMETERS='+$read.Manifest.supervisor.app_parameters)
"""
    result = run_ps(script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "BACKUP_THEME=MISSING/LEGACY_MISSING_ALLOWED_FOR_CORRECTION" in result.stdout
    assert canonical_source_parameters() in result.stdout


def test_ownership_rejects_foreign_service_app_and_forbidden_port(tmp_path):
    python = str(Path(sys.executable))
    script = f"""
. {ps(str(COMMON))}
$ctx=[pscustomobject]@{{Mode='SIMULATION';Root={ps(str(tmp_path))};RuntimeRoot={ps(str(tmp_path))};AppPath={ps(str(tmp_path / 'app_opensea_sales.py'))};Port=18520;SupervisorServiceName='SANDBOX_NSSM';SupervisorAppDirectory={ps(str(tmp_path))}}}
$base=[ordered]@{{ServiceName='SANDBOX_NSSM';NssmExecutable='nssm.exe';AppDirectory={ps(str(tmp_path))};Application={ps(python)};AppParameters={ps(canonical_source_parameters('--theme.base=dark'))};ServiceState='Running'}}
$service=[pscustomobject]$base; $service.ServiceName='OTHER'
try {{ Assert-ProductionSupervisorOwnershipIdentity $ctx $service -AllowLegacyMissingThemeSource | Out-Null; 'SERVICE=PASS' }} catch {{ 'SERVICE='+$_.Exception.Message }}
$app=[pscustomobject]$base; $app.AppParameters={ps(canonical_source_parameters('--theme.base=dark').replace('app_opensea_sales.py','app_gaming_marketplace.py'))}
try {{ Assert-ProductionSupervisorOwnershipIdentity $ctx $app -AllowLegacyMissingThemeSource | Out-Null; 'APP=PASS' }} catch {{ 'APP='+$_.Exception.Message }}
$port=[pscustomobject]$base; $port.AppParameters={ps(canonical_source_parameters('--theme.base=dark').replace('--server.port 18520','--server.port 8501'))}
try {{ Assert-ProductionSupervisorOwnershipIdentity $ctx $port -AllowLegacyMissingThemeSource | Out-Null; 'PORT=PASS' }} catch {{ 'PORT='+$_.Exception.Message }}
"""
    result = run_ps(script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SERVICE=SUPERVISOR_SERVICE_NAME_MISMATCH" in result.stdout
    assert "APP=SUPERVISOR_FORBIDDEN_TARGET" in result.stdout
    assert "PORT=SUPERVISOR_LAUNCH_CONTRACT_REQUIRED" in result.stdout
