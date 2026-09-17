import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]
OPS = ROOT / "ops" / "production"
COMMON = OPS / "production_update_common.ps1"
POWERSHELL = os.environ.get("WINDIR", r"C:\Windows") + r"\System32\WindowsPowerShell\v1.0\powershell.exe"


def run_ps(script: str):
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        text=True,
        capture_output=True,
        check=False,
    )


def test_launch_shape_validator_accepts_one_canonical_object_and_rejects_invalid_shapes():
    common = str(COMMON).replace("'", "''")
    script = f"""
. '{common}';
$ctx=[pscustomobject]@{{Mode='SIMULATION'}}
$valid=[pscustomobject]@{{Id=18520;ProcessId=18520;Process=$null;StdOutLogPath='out.log';StdErrLogPath='err.log';StartedAt='now';SupervisorConfiguration=[pscustomobject]@{{ServiceName='SANDBOX_NSSM'}}}}
$validItems=@(Assert-SupervisorLaunchResult $ctx $valid);if($validItems.Count -ne 1 -or $validItems[0].Id -ne 18520){{throw 'VALID_CANONICAL_LAUNCH_FAILED'}};Write-Output 'VALID_CANONICAL_LAUNCH=PASS'
function Reject([string]$Name,[object]$Value) {{ try {{ $null=Assert-SupervisorLaunchResult $ctx $Value; Write-Output ($Name+'=FAIL') }} catch {{ Write-Output ($Name+'=PASS') }} }}
Reject 'STRING_RETURN_REJECTION' 'C:\\Python\\python.exe'
$multi=@('C:\\Python\\python.exe',$valid);Reject 'MULTI_OUTPUT_ARRAY_REJECTION' $multi
try {{ $null=Assert-SupervisorLaunchResult $ctx $null;Write-Output 'NULL_RETURN_REJECTION=FAIL' }} catch {{ Write-Output 'NULL_RETURN_REJECTION=PASS' }}
$missingId=[pscustomobject]@{{ProcessId=18520;Process=$null;StdOutLogPath='out.log';StdErrLogPath='err.log';StartedAt='now';SupervisorConfiguration=[pscustomobject]@{{ServiceName='SANDBOX_NSSM'}}}};Reject 'MISSING_ID_REJECTION' $missingId
$missingLogs=[pscustomobject]@{{Id=18520;ProcessId=18520;Process=$null;StartedAt='now';SupervisorConfiguration=[pscustomobject]@{{ServiceName='SANDBOX_NSSM'}}}};Reject 'MISSING_LOG_PATH_REJECTION' $missingLogs
$mismatch=[pscustomobject]@{{Id=18520;ProcessId=18521;Process=$null;StdOutLogPath='out.log';StdErrLogPath='err.log';StartedAt='now';SupervisorConfiguration=[pscustomobject]@{{ServiceName='SANDBOX_NSSM'}}}};Reject 'PID_MISMATCH_REJECTION' $mismatch
$badConfig=[pscustomobject]@{{Id=18520;ProcessId=18520;Process=$null;StdOutLogPath='out.log';StdErrLogPath='err.log';StartedAt='now';SupervisorConfiguration=[pscustomobject]@{{ConfigurationFingerprint='bad'}}}};Reject 'INVALID_SUPERVISOR_CONFIG_REJECTION' $badConfig
$emptyLogs=[pscustomobject]@{{Id=18520;ProcessId=18520;Process=$null;StdOutLogPath='';StdErrLogPath='';StartedAt='now';SupervisorConfiguration=[pscustomobject]@{{ServiceName='SANDBOX_NSSM'}}}};Reject 'EMPTY_LOG_PATH_REJECTION' $emptyLogs
"""
    result = run_ps(script)
    assert result.returncode == 0, result.stdout + result.stderr
    for marker in (
        "VALID_CANONICAL_LAUNCH=PASS",
        "STRING_RETURN_REJECTION=PASS",
        "MULTI_OUTPUT_ARRAY_REJECTION=PASS",
        "NULL_RETURN_REJECTION=PASS",
        "MISSING_ID_REJECTION=PASS",
        "MISSING_LOG_PATH_REJECTION=PASS",
        "PID_MISMATCH_REJECTION=PASS",
        "INVALID_SUPERVISOR_CONFIG_REJECTION=PASS",
        "EMPTY_LOG_PATH_REJECTION=PASS",
    ):
        assert marker in result.stdout
    assert "=FAIL" not in result.stdout


def test_start_context_process_simulation_returns_exactly_one_canonical_object():
    common = str(COMMON).replace("'", "''")
    script = f"""
. '{common}';
$root=Join-Path 'C:\\VAMBAM\\Projects\\OTG\\DEV\\production_tooling_sandbox_110' ('launch_contract_'+[guid]::NewGuid().ToString('N'));
try {{
    New-Item -ItemType Directory -Path $root -Force|Out-Null
    $ctx=New-SimulationExecutionContext @{{SimulationRoot=$root;SimulationPort=18531;ReleasePython=(Get-Command powershell.exe).Source;ExpectedOldHead='old';ExpectedReleaseHead='release';PreparedReleaseManifest='';PreparedReleaseManifestSha256='';BackupManifest='';BackupRoot=(Join-Path $root 'backups')}}
    Write-AtomicJson $ctx.SimulationStatePath ([pscustomobject]@{{process='old-healthy';fail_new_health=$false}})
    $items=@(Start-ContextProcess $ctx $ctx.ReleasePython $ctx.AppPath)
    if($items.Count -ne 1){{throw 'START_CONTEXT_PROCESS_MULTIPLE_OUTPUT'}}
    $launch=$items[0]
    $null=Assert-SupervisorLaunchResult $ctx $launch
    if($launch.SupervisorConfiguration.ServiceName -ne 'SANDBOX_NSSM'){{throw 'SIMULATION_CONFIGURATION_MISSING'}}
    Write-Output 'START_CONTEXT_PROCESS_RETURN_CONTRACT=PASS'
}} finally {{ if(Test-Path -LiteralPath $root){{Remove-Item -LiteralPath $root -Recurse -Force}} }}
"""
    result = run_ps(script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "START_CONTEXT_PROCESS_RETURN_CONTRACT=PASS" in result.stdout


def test_launch_contract_is_enforced_before_deploy_downstream_writes():
    common = COMMON.read_text(encoding="utf-8")
    start = common.split("function Start-ProductionSupervisor", 1)[1].split("function Get-FinalRuntimeRoot", 1)[0]
    context = common.split("function Start-ContextProcess", 1)[1].split("function Invoke-HealthCheck", 1)[0]
    deploy = common.split("function Invoke-DeployCore", 1)[1]
    assert "$null=Assert-SupervisorLaunchResult $Context $launch" in start
    assert "$null=Assert-SupervisorLaunchResult $Context $launch" in context
    assert "$null=Assert-SupervisorLaunchResult $Context $new" in deploy
    launch_assertion = deploy.index("$null=Assert-SupervisorLaunchResult $Context $new")
    assert launch_assertion < deploy.index("Write-ActiveRuntime $Context $new.Id")
    assert launch_assertion < deploy.index("Invoke-TaskConfigurationCore $Context -Execute")
    assert launch_assertion < deploy.index("Assert-DeploymentReceipt $receipt")
    assert "SUPERVISOR_LAUNCH_RESULT_INVALID" in common
    assert "$null=$config|Add-Member" in common
    assert "$null=$Configuration | Add-Member" in common
