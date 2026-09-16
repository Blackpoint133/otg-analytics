import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
COMMON = ROOT / "ops" / "production" / "production_update_common.ps1"
EXPECTED_APP = r"C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales\streamlit_opensea_sales\app_opensea_sales.py"
RUNTIME_APP = r"C:\VAMBAM\Projects\OTG\runtime\opensea_sales\releases\release\streamlit_opensea_sales\app_opensea_sales.py"


def ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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


def streamlit_command(app: str, port: int = 8502) -> str:
    return f'python.exe -m streamlit run {app} --server.port {port} --server.address 127.0.0.1'


def test_relative_entrypoint_is_accepted_with_strict_listener_identity():
    assert identity_case(streamlit_command("app_opensea_sales.py")) == "ACCEPT"


def test_expected_absolute_and_release_runtime_entrypoints_are_accepted():
    assert identity_case(streamlit_command(f'"{EXPECTED_APP}"')) == "ACCEPT"
    assert identity_case(streamlit_command(f'"{RUNTIME_APP}"'), runtime_app=RUNTIME_APP) == "ACCEPT"


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
