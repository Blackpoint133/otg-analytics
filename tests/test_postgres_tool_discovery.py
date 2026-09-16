import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]
COMMON = ROOT / "ops" / "production" / "production_update_common.ps1"


def ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_ps(body: str):
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", f". {ps(str(COMMON))}; {body}"],
        text=True,
        capture_output=True,
        check=False,
    )


def make_tool_dir(root: Path, version: str, names):
    directory = root / version / "bin"
    directory.mkdir(parents=True)
    for name in names:
        (directory / f"{name}.exe").write_text("fixture", encoding="utf-8")
    return directory


def test_complete_same_bin_toolset_and_highest_version_are_selected(tmp_path):
    low = make_tool_dir(tmp_path, "17", ("pg_dump", "pg_restore", "psql"))
    high = make_tool_dir(tmp_path, "18", ("pg_dump", "pg_restore", "psql"))
    result = run_ps(f"$s=Select-PostgresToolSet -Directories @({ps(str(low))},{ps(str(high))}); $s.pg_dump")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().endswith(r"18\bin\pg_dump.exe")


def test_incomplete_toolset_is_rejected(tmp_path):
    incomplete = make_tool_dir(tmp_path, "19", ("pg_dump", "psql"))
    result = run_ps(f"$s=Select-PostgresToolSet -Directories @({ps(str(incomplete))}); if($s.Count -eq 0){{'REJECTED'}}else{{'ACCEPTED'}}")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "REJECTED"


def test_live_discovery_returns_all_three_18_3_tools_without_path_mutation():
    before = os.environ.get("PATH")
    result = run_ps("$t=Get-PostgresTools; foreach($n in @('pg_dump','pg_restore','psql')){ Write-Output ($n+'='+$t[$n]) }")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "pg_dump=C:\\Program Files\\PostgreSQL\\18\\bin\\pg_dump.exe" in result.stdout
    assert "pg_restore=C:\\Program Files\\PostgreSQL\\18\\bin\\pg_restore.exe" in result.stdout
    assert "psql=C:\\Program Files\\PostgreSQL\\18\\bin\\psql.exe" in result.stdout
    assert os.environ.get("PATH") == before
