import json
import os
import shutil
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
    assert manifest["git_bundle_validation"] == "PASS"
    assert (manifests[-1].parent / "git_bundle_verify.log").is_file()


def _run_child_process_probe(tmp_path: Path, command: str):
    common = OPS / "production_update_common.ps1"
    powershell = os.environ.get("WINDIR", r"C:\Windows") + r"\System32\WindowsPowerShell\v1.0\powershell.exe"
    escaped_common = str(common).replace("'", "''")
    script = f"""
. '{escaped_common}';
$result=Invoke-ChildProcess $env:ComSpec @('/c','{command}') '{str(tmp_path)}' 30 @{{}};
Write-Output ('EXIT='+$result.ExitCode);
Write-Output ('STDOUT='+$result.StdOut.Trim());
Write-Output ('STDERR='+$result.StdErr.Trim());
"""
    return subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        text=True,
        capture_output=True,
        check=False,
    )


def test_controlled_child_process_accepts_exit_zero_with_stderr():
    result = _run_child_process_probe(
        Path.cwd(),
        "echo stdout & echo stderr 1>&2",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "EXIT=0" in result.stdout
    assert "STDOUT=stdout" in result.stdout
    assert "STDERR=stderr" in result.stdout


def test_controlled_child_process_rejects_nonzero_even_with_benign_stderr():
    powershell = os.environ.get("WINDIR", r"C:\Windows") + r"\System32\WindowsPowerShell\v1.0\powershell.exe"
    common = str(OPS / "production_update_common.ps1").replace("'", "''")
    script = f"""
. '{common}';
try {{ Invoke-ChildProcess $env:ComSpec @('/c','echo bundle is okay 1>&2 & exit /b 7') '{str(Path.cwd())}' 30 @{{}}; 'UNEXPECTED_PASS' }}
catch {{ 'CHILD_ERROR='+$_.Exception.Message }}
"""
    result = subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CHILD_ERROR=CHILD_COMMAND_FAILED:" in result.stdout
    assert ":7" in result.stdout
    assert "UNEXPECTED_PASS" not in result.stdout


def test_real_git_bundle_verify_stderr_is_accepted_in_safe_temp_repo(tmp_path):
    git = shutil.which("git")
    assert git
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run([git, "-C", str(repo), "init", "-q"], check=True)
    subprocess.run([git, "-C", str(repo), "config", "user.email", "tests@example.invalid"], check=True)
    subprocess.run([git, "-C", str(repo), "config", "user.name", "Tooling Tests"], check=True)
    (repo / "fixture.txt").write_text("bundle fixture\n", encoding="utf-8")
    subprocess.run([git, "-C", str(repo), "add", "fixture.txt"], check=True)
    subprocess.run([git, "-C", str(repo), "commit", "-qm", "fixture"], check=True)
    bundle = tmp_path / "fixture.bundle"
    created = subprocess.run([git, "-C", str(repo), "bundle", "create", str(bundle), "HEAD"], text=True, capture_output=True)
    assert created.returncode == 0, created.stdout + created.stderr
    common = str(OPS / "production_update_common.ps1").replace("'", "''")
    bundle_ps = str(bundle).replace("'", "''")
    repo_ps = str(repo).replace("'", "''")
    powershell = os.environ.get("WINDIR", r"C:\Windows") + r"\System32\WindowsPowerShell\v1.0\powershell.exe"
    script = f"""
. '{common}';
$git=(Get-Command git.exe).Source;
$result=Invoke-ChildProcess $git @('-c',('safe.directory={repo_ps}'),'-C','{repo_ps}','bundle','verify','{bundle_ps}') '{repo_ps}' 30 @{{}};
Write-Output ('EXIT='+$result.ExitCode);
Write-Output ('STDERR_PRESENT='+(-not [string]::IsNullOrWhiteSpace($result.StdErr)));
"""
    result = subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "EXIT=0" in result.stdout
    assert "STDERR_PRESENT=True" in result.stdout


def _run_git_bundle_verify(repo: Path, bundle: Path):
    common = str(OPS / "production_update_common.ps1").replace("'", "''")
    bundle_ps = str(bundle).replace("'", "''")
    repo_ps = str(repo).replace("'", "''")
    powershell = os.environ.get("WINDIR", r"C:\Windows") + r"\System32\WindowsPowerShell\v1.0\powershell.exe"
    script = f"""
. '{common}';
$git=(Get-Command git.exe).Source;
try {{ Invoke-ChildProcess $git @('-c',('safe.directory={repo_ps}'),'-C','{repo_ps}','bundle','verify','{bundle_ps}') '{repo_ps}' 30 @{{}}; 'PASS' }}
catch {{ 'FAIL:' + $_.Exception.Message }}
"""
    return subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        text=True,
        capture_output=True,
        check=False,
    )


def test_corrupt_or_missing_bundle_fails_closed(tmp_path):
    git = shutil.which("git")
    assert git
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run([git, "-C", str(repo), "init", "-q"], check=True)
    subprocess.run([git, "-C", str(repo), "config", "user.email", "tests@example.invalid"], check=True)
    subprocess.run([git, "-C", str(repo), "config", "user.name", "Tooling Tests"], check=True)
    (repo / "fixture.txt").write_text("bundle fixture\n", encoding="utf-8")
    subprocess.run([git, "-C", str(repo), "add", "fixture.txt"], check=True)
    subprocess.run([git, "-C", str(repo), "commit", "-qm", "fixture"], check=True)
    bundle = tmp_path / "fixture.bundle"
    subprocess.run([git, "-C", str(repo), "bundle", "create", str(bundle), "HEAD"], check=True)
    bundle_bytes = bytearray(bundle.read_bytes())
    bundle_bytes[0] = ord("X")
    bundle.write_bytes(bytes(bundle_bytes))
    corrupt = _run_git_bundle_verify(repo, bundle)
    assert corrupt.returncode == 0, corrupt.stdout + corrupt.stderr
    assert "FAIL:CHILD_COMMAND_FAILED:" in corrupt.stdout
    missing = _run_git_bundle_verify(repo, tmp_path / "missing.bundle")
    assert missing.returncode == 0, missing.stdout + missing.stderr
    assert "FAIL:CHILD_COMMAND_FAILED:" in missing.stdout


def test_production_failure_telemetry_is_outside_checkout():
    orchestrator = (OPS / "production_update_orchestrator.ps1").read_text(encoding="utf-8")
    assert "Join-Path $context.RuntimeRoot 'logs\\EXECUTION_TELEMETRY.json'" in orchestrator
    assert "Join-Path $context.Root 'EXECUTION_TELEMETRY.json'" in orchestrator


def _run_real_log_lock_probe(tmp_path: Path, fatal: bool = False, stale: bool = False):
    common = str(OPS / "production_update_common.ps1").replace("'", "''")
    temp = str(tmp_path).replace("'", "''")
    powershell = os.environ.get("WINDIR", r"C:\Windows") + r"\System32\WindowsPowerShell\v1.0\powershell.exe"
    child_script = tmp_path / "held_child.ps1"
    child_script.write_text(
        "Write-Output 'Traceback'; [Console]::Error.WriteLine('ImportError'); Start-Sleep -Seconds 20\n"
        if fatal
        else "Write-Output 'child_stdout'; [Console]::Error.WriteLine('child_stderr'); Start-Sleep -Seconds 20\n",
        encoding="utf-8",
    )
    child_path = str(child_script).replace("'", "''")
    script = f"""
. '{common}';
$out=Join-Path '{temp}' 'current.out.log';
$err=Join-Path '{temp}' 'current.err.log';
$stale=Join-Path '{temp}' 'older-launch.out.log';
$pwsh=(Get-Process -Id $PID).Path;
$launch=$null;
try {{
    if({'$true' if stale else '$false'}) {{ Write-AtomicText $stale 'Traceback from an older launch' }}
    $launch=Start-RedirectedProcess $pwsh @('-NoProfile','-File','{child_path}') (Get-Location).Path $out $err;
    for($i=0;$i -lt 30;$i++) {{
        Start-Sleep -Milliseconds 100;
        if((Read-SharedText $out).Trim().Length -gt 0 -and (Read-SharedText $err).Trim().Length -gt 0) {{ break }}
    }}
    $stdout=Read-SharedText $out;
    $stderr=Read-SharedText $err;
    Write-Output ('PID='+$launch.Id);
    Write-Output ('STDOUT='+$stdout.Trim());
    Write-Output ('STDERR='+$stderr.Trim());
    Assert-CurrentLaunchLogs $launch;
    Write-Output 'LOG_GATE=PASS';
}} finally {{
    if($launch -and -not $launch.Process.HasExited) {{ Stop-Process -Id $launch.Id -Force -ErrorAction SilentlyContinue }}
}}
"""
    return subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        text=True,
        capture_output=True,
        check=False,
    )


def test_real_windows_child_log_lock_and_current_launch_gate_pass(tmp_path):
    result = _run_real_log_lock_probe(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PID=" in result.stdout
    assert "STDOUT=child_stdout" in result.stdout
    assert "STDERR=child_stderr" in result.stdout
    assert "LOG_GATE=PASS" in result.stdout


def test_current_launch_fatal_log_fails_closed(tmp_path):
    result = _run_real_log_lock_probe(tmp_path, fatal=True)
    assert result.returncode != 0
    assert "CURRENT_LAUNCH_LOG_FAILED" in result.stdout + result.stderr


def test_stale_fatal_log_does_not_fail_current_launch(tmp_path):
    result = _run_real_log_lock_probe(tmp_path, stale=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "LOG_GATE=PASS" in result.stdout


def test_start_context_process_has_no_competing_append_and_uses_unique_logs():
    common = (OPS / "production_update_common.ps1").read_text(encoding="utf-8")
    assert "Add-Content $log" not in common
    assert "StdOutLogPath" in common
    assert "StdErrLogPath" in common
    assert "production_'+$launchId+'.out.log" in common
    assert "production_'+$launchId+'.err.log" in common
