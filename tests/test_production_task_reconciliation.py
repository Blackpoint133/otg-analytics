import os
import shutil
import subprocess
import sys
import uuid
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


def test_owned_old_release_tasks_reconcile_and_missing_tasks_are_created():
    sandbox = Path(r"C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110") / f"task_reconciliation_{uuid.uuid4().hex}"
    try:
        script = rf"""
. {ps(str(COMMON))}
$root={ps(str(sandbox))};New-Item -ItemType Directory -Path $root -Force|Out-Null
    $ctx=New-SimulationExecutionContext @{{SimulationRoot=$root;SimulationPort=18530;ExpectedOldHead='old';ExpectedReleaseHead='new';ReleasePython='';PreparedReleaseManifest='';PreparedReleaseManifestSha256='';BackupManifest='';BackupRoot=(Join-Path $root 'backups')}}
$tasks=[ordered]@{{}}
foreach($name in $script:ManagedTasks) {{
    $desired=Get-DesiredTaskDefinition $ctx $name
    $oldPath=Join-Path $ctx.RuntimeRoot 'releases\old\.venv\Scripts\python.exe'
    $oldArgs=$desired.arguments.Replace($ctx.ReleasePython,$oldPath)
    $old=[pscustomobject]$desired;$old.arguments=$oldArgs;$tasks[$name]=$old
}}
Write-AtomicJson $ctx.SimulationStatePath ([ordered]@{{tasks=$tasks}})
$result=Invoke-TaskConfigurationCore $ctx -Execute
$state=Get-ContextState $ctx
foreach($name in $script:ManagedTasks) {{
    $desired=Get-DesiredTaskDefinition $ctx $name
    if(-not(Test-TaskDefinitionMatch $state.tasks.$name $desired)) {{ throw ('RECONCILED_DEFINITION_MISMATCH:'+ $name) }}
    if($state.tasks.$name.arguments -notmatch [regex]::Escape($ctx.ReleasePython)) {{ throw ('NEW_RELEASE_PYTHON_MISSING:'+ $name) }}
}}
Write-Output 'OLD_RELEASE_TASK_RECONCILIATION=PASS'
if(-not (@($result) -match 'TASK_RECONCILIATION=PASS')) {{ throw 'TASK_RECONCILIATION_MARKER_MISSING' }}
$state.tasks=[ordered]@{{}};Save-ContextState $ctx $state;Invoke-TaskConfigurationCore $ctx -Execute|Out-Null
$state=Get-ContextState $ctx
foreach($name in $script:ManagedTasks) {{ if(-not $state.tasks.PSObject.Properties[$name]) {{ throw ('MISSING_TASK_NOT_CREATED:'+ $name) }} }}
Write-Output 'MISSING_TASK_CREATE=PASS'
"""
        result = run_ps(script)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "OLD_RELEASE_TASK_RECONCILIATION=PASS" in result.stdout
        assert "MISSING_TASK_CREATE=PASS" in result.stdout
    finally:
        if sandbox.exists():
            shutil.rmtree(sandbox)


def test_foreign_managed_task_shapes_fail_closed():
    sandbox = Path(r"C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110") / f"task_collision_{uuid.uuid4().hex}"
    try:
        script = f"""
. {ps(str(COMMON))}
$ctx=New-SimulationExecutionContext @{{SimulationRoot={ps(str(sandbox))};SimulationPort=18531;ExpectedOldHead='old';ExpectedReleaseHead='new';ReleasePython='';PreparedReleaseManifest='';PreparedReleaseManifestSha256='';BackupManifest='';BackupRoot=(Join-Path {ps(str(sandbox))} 'backups')}}
$desired=Get-DesiredTaskDefinition $ctx $script:ManagedTasks[0]
$cases=[ordered]@{{EXECUTABLE='cmd.exe';SCRIPT=($desired.arguments -replace 'refresh_production_derived.ps1','foreign.ps1');APPROVAL=($desired.arguments -replace 'REFRESH_OTG_DERIVED_8502','FOREIGN_APPROVAL');CHAIN=($desired.arguments+'; whoami');WORKDIR=($desired.working_directory+'\foreign');PRINCIPAL='Administrator';INTERVAL=30}}
foreach($case in $cases.Keys) {{
    $task=[pscustomobject]$desired
    if($case -eq 'EXECUTABLE'){{$task.executable=$cases[$case]}}
    elseif($case -eq 'SCRIPT' -or $case -eq 'APPROVAL' -or $case -eq 'CHAIN'){{$task.arguments=$cases[$case]}}
    elseif($case -eq 'WORKDIR'){{$task.working_directory=$cases[$case]}}
    elseif($case -eq 'PRINCIPAL'){{$task.principal=$cases[$case]}}
    elseif($case -eq 'INTERVAL'){{$task.interval_minutes=$cases[$case]}}
    try {{ Assert-ManagedTaskOwnershipIdentity $ctx $task.task_name $task|Out-Null;throw ('UNEXPECTED_'+$case+'_PASS') }} catch {{ if($_.Exception.Message -notmatch '^TASK_COLLISION:') {{ throw }};Write-Output ($case+'=FAIL_CLOSED') }}
}}
"""
        result = run_ps(script)
        assert result.returncode == 0, result.stdout + result.stderr
        for case in ("EXECUTABLE", "SCRIPT", "APPROVAL", "CHAIN", "WORKDIR", "PRINCIPAL", "INTERVAL"):
            assert f"{case}=FAIL_CLOSED" in result.stdout
    finally:
        if sandbox.exists():
            shutil.rmtree(sandbox)


def test_task_postwrite_mismatch_is_detected_and_contract_is_explicit():
    common = COMMON.read_text(encoding="utf-8")
    assert "TASK_POSTWRITE_DEFINITION_MISMATCH" in common
    assert "TASK_OWNERSHIP_IDENTITY" in common
    assert "Set-ScheduledTask" in common
    assert "Register-ScheduledTask" in common


def test_rollback_uses_supervisor_application_and_rejects_invalid_authority(tmp_path):
    old_python = tmp_path / "old_venv" / "Scripts" / "python.exe"
    old_python.parent.mkdir(parents=True)
    old_python.write_text("fixture", encoding="utf-8")
    base_python = Path(sys.executable)
    script = f"""
. {ps(str(COMMON))}
$ctx=[pscustomobject]@{{Mode='PRODUCTION';ReleasePython={ps(str(base_python))}}}
$m=[pscustomobject]@{{old_process_executable={ps(str(base_python))};supervisor=[pscustomobject]@{{application={ps(str(old_python))}}}}}
$authority=Get-RollbackPythonAuthority $ctx $m
Write-Output ('AUTHORITY='+$authority)
if($authority -ne {ps(str(old_python))}) {{ throw 'WRONG_ROLLBACK_AUTHORITY' }}
"""
    result = run_ps(script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"AUTHORITY={old_python}" in result.stdout

    invalid_cases = {
        "MISSING": "$null",
        "NONEXISTENT": ps(str(tmp_path / "missing" / "python.exe")),
        "NONPYTHON": ps(str(tmp_path / "old_venv" / "Scripts" / "runner.exe")),
    }
    for name, application in invalid_cases.items():
        result = run_ps(
            f"""
. {ps(str(COMMON))}
$ctx=[pscustomobject]@{{Mode='PRODUCTION';ReleasePython={ps(str(base_python))}}}
$m=[pscustomobject]@{{old_process_executable={ps(str(base_python))};supervisor=[pscustomobject]@{{application={application}}}}}
try {{ Get-RollbackPythonAuthority $ctx $m|Out-Null; 'UNEXPECTED_PASS' }} catch {{ 'REJECTED='+$_.Exception.Message }}
"""
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "UNEXPECTED_PASS" not in result.stdout
        assert "REJECTED=ROLLBACK_SUPERVISOR_APPLICATION_" in result.stdout

    mismatch = run_ps(
        f"""
. {ps(str(COMMON))}
$ctx=[pscustomobject]@{{Mode='PRODUCTION';ReleasePython={ps(str(base_python))}}}
$m=[pscustomobject]@{{old_process_executable={ps(str(base_python))};supervisor=[pscustomobject]@{{application={ps(str(old_python))}}}}}
Get-RollbackPythonAuthority $ctx $m|Out-Null
Write-Output ('MISMATCH='+$ctx.RollbackPythonMismatchAudit)
"""
    )
    assert mismatch.returncode == 0, mismatch.stdout + mismatch.stderr
    assert "MISMATCH=DETECTED_BUT_NONAUTHORITATIVE" in mismatch.stdout


def test_rollback_source_is_not_validated_with_target_release_executable():
    common = COMMON.read_text(encoding="utf-8")
    assert "Get-RollbackPythonAuthority $Context $manifest" in common
    assert "old_process_executable" in common
    assert "ROLLBACK_PYTHON_AUTHORITY" in common
