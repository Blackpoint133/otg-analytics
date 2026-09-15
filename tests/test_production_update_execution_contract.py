import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
OPS = ROOT / "ops" / "production"

def run_ps1(name, *args):
    return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(OPS / name), *args], text=True, capture_output=True, check=False)

def test_sandbox_executes_all_mutating_phases_without_production_target():
    result = run_ps1("validate_production_tooling_sandbox.ps1", "-Execute")
    assert result.returncode == 0, result.stdout + result.stderr
    for marker in ("SANDBOX_BACKUP_EXECUTION_TEST=PASS", "SANDBOX_DEPLOY_EXECUTION_TEST=PASS", "SANDBOX_ROLLBACK_EXECUTION_TEST=PASS", "SANDBOX_FAIL_CLOSED_TESTS=PASS"):
        assert marker in result.stdout
    assert "production_tooling_sandbox_107" in result.stdout
    assert "8502" not in result.stdout

def test_migration_allowlist_and_rollback_policy_are_exact():
    deploy = (OPS / "deploy_production.ps1").read_text()
    rollback = (OPS / "rollback_production.ps1").read_text()
    assert "MIGRATION_PLAN_COUNT=3" in deploy
    assert "NOT_AUTOMATIC" in rollback
    assert "git clean" not in (deploy + rollback).lower()
    assert "manifest-old-head" not in rollback
