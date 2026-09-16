import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
COMMON = ROOT / "ops" / "production" / "production_update_common.ps1"
EXPECTED_APP = r"C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales\streamlit_opensea_sales\app_opensea_sales.py"
RUNTIME_APP = r"C:\VAMBAM\Projects\OTG\runtime\opensea_sales\releases\release\streamlit_opensea_sales\app_opensea_sales.py"


def ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_powershell(script: str):
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        text=True,
        capture_output=True,
        check=False,
    )


def identity_case(command: str, *, listener_address="127.0.0.1", listener_port=8502, runtime_app="") -> str:
    python = str(Path(sys.executable))
    script = f"""
. {ps(str(COMMON))}
$listener=[pscustomobject]@{{LocalAddress={ps(listener_address)};LocalPort={listener_port};State='Listen';OwningProcess=4242}}
$process=[pscustomobject]@{{ProcessId=4242;ExecutablePath={ps(python)};CommandLine={ps(command)}}}
try {{ Test-8502ProcessIdentity $listener $process $script:ExpectedApp {ps(runtime_app)} | Out-Null; 'ACCEPT' }} catch {{ 'REJECT:' + $_.Exception.Message }}
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip().splitlines()[-1]


def streamlit_command(app: str, port: int = 8502, theme: str = '--theme.base="dark"') -> str:
    return (
        f'python.exe -m streamlit run {app} --server.port {port} '
        f'--server.address 127.0.0.1 --server.fileWatcherType none '
        f'--server.headless true --browser.gatherUsageStats false {theme}'
    ).strip()


def test_canonical_production_launch_contract_is_dark_and_complete():
    script = f"""
. {ps(str(COMMON))}
$parameters=Get-ProductionStreamlitLaunchParameters
Write-Output $parameters
$null=Assert-StreamlitLaunchContract $parameters 8502
Write-Output 'CONTRACT=PASS'
"""
    result = run_powershell(script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '--theme.base="dark"' in result.stdout
    assert "CONTRACT=PASS" in result.stdout


def test_relative_entrypoint_is_accepted_with_strict_listener_identity():
    assert identity_case(streamlit_command("app_opensea_sales.py")) == "ACCEPT"


def test_expected_absolute_and_release_runtime_entrypoints_are_accepted():
    assert identity_case(streamlit_command(f'"{EXPECTED_APP}"')) == "ACCEPT"
    assert identity_case(streamlit_command(f'"{RUNTIME_APP}"'), runtime_app=RUNTIME_APP) == "ACCEPT"


def test_theme_contract_accepts_supported_dark_syntaxes():
    for theme in ('--theme.base dark', '--theme.base=dark', '--theme.base="dark"'):
        assert identity_case(streamlit_command("app_opensea_sales.py", theme=theme)) == "ACCEPT"


def test_theme_contract_rejects_missing_or_non_dark_values():
    for theme in ('', '--theme.base=light', '--theme.base=blue', '--theme.base light --theme.base=dark'):
        assert identity_case(streamlit_command("app_opensea_sales.py", theme=theme)).startswith("REJECT:")


def test_supervisor_validation_accepts_generated_canonical_parameters(tmp_path):
    root = str(tmp_path)
    python = str(Path(sys.executable))
    script = f"""
. {ps(str(COMMON))}
$ctx=[pscustomobject]@{{Mode='SIMULATION';Root={ps(root)};RuntimeRoot={ps(root)};AppPath={ps(str(tmp_path / 'app_opensea_sales.py'))};Port=18520;SupervisorServiceName='SANDBOX_NSSM';SupervisorAppDirectory={ps(root)}}}
$parameters=(Get-ProductionStreamlitLaunchParameters).Replace('--server.port 8502','--server.port 18520')
$configuration=[pscustomobject]@{{ServiceName='SANDBOX_NSSM';NssmExecutable='C:\\tools\\nssm\\win64\\nssm.exe';AppDirectory={ps(root)};Application={ps(python)};AppParameters=$parameters;ServiceState='Stopped'}}
try {{ Assert-ProductionSupervisorIdentity $ctx $configuration; 'SUPERVISOR_CONTRACT=PASS' }} catch {{ 'SUPERVISOR_CONTRACT=REJECT:' + $_.Exception.Message }}
"""
    result = run_powershell(script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SUPERVISOR_CONTRACT=PASS" in result.stdout


def test_forbidden_or_non_matching_processes_are_rejected():
    cases = (
        streamlit_command("app_gaming_marketplace.py"),
        streamlit_command("app_opensea_sales.py", 8501),
        streamlit_command("app_opensea_sales.py", 8504),
        "python.exe -c print('not streamlit') --server.port 8502 --server.address 127.0.0.1",
        streamlit_command(r'"C:\unrelated\checkout\app_opensea_sales.py"'),
        "python.exe -m streamlit run app_opensea_sales.py --server.address 127.0.0.1",
    )
    for command in cases:
        assert identity_case(command).startswith("REJECT:")


def test_wrong_listener_address_or_port_is_rejected():
    command = streamlit_command("app_opensea_sales.py")
    assert identity_case(command, listener_address="0.0.0.0") .startswith("REJECT:")
    assert identity_case(command, listener_port=8504).startswith("REJECT:")
