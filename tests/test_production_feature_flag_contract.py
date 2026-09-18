import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]
OPS = ROOT / "ops" / "production"
COMMON = OPS / "production_update_common.ps1"


def _ps_path(path: Path) -> str:
    return str(path).replace("'", "''")


def _run_flag_transform(tmp_path: Path, env_text: str, approved: bool = False):
    env_path = tmp_path / ".env"
    env_path.write_text(env_text, encoding="utf-8")
    script = f"""
. '{_ps_path(COMMON)}';
$ctx=[pscustomobject]@{{EnvPath='{_ps_path(env_path)}';ApprovedProductionWritePaths=${str(approved).lower()};MutationStarted=$false;MutationPhases=(New-Object Collections.ArrayList)}};
Set-FailClosedEnv $ctx | Out-Null;
Get-Content -LiteralPath '{_ps_path(env_path)}' -Raw
"""
    return subprocess.run(
        [
            os.environ.get("WINDIR", r"C:\Windows") + r"\System32\WindowsPowerShell\v1.0\powershell.exe",
            "-NoProfile",
            "-Command",
            script,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_explicit_enabled_production_flags_are_preserved(tmp_path):
    result = _run_flag_transform(
        tmp_path,
        "\n".join(
            [
                "OTG_ANALYTICS_WRITES_ENABLED=true",
                "OTG_SITE_ANALYTICS_ENABLED=TRUE",
                "OTG_PRODUCT_EVENTS_ENABLED=on",
                "OTG_FEEDBACK_WRITES_ENABLED=yes",
                "OTG_FEEDBACK_TELEGRAM_ENABLED=false",
            ]
        ),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OTG_ANALYTICS_WRITES_ENABLED=true" in result.stdout
    assert "OTG_SITE_ANALYTICS_ENABLED=true" in result.stdout
    assert "OTG_PRODUCT_EVENTS_ENABLED=true" in result.stdout
    assert "OTG_FEEDBACK_WRITES_ENABLED=true" in result.stdout
    assert "OTG_FEEDBACK_TELEGRAM_ENABLED=false" in result.stdout


def test_missing_invalid_and_conflicting_flags_remain_fail_closed(tmp_path):
    result = _run_flag_transform(
        tmp_path,
        "\n".join(
            [
                "OTG_ANALYTICS_WRITES_ENABLED=maybe",
                "OTG_FEEDBACK_WRITES_ENABLED=true",
                "OTG_FEEDBACK_WRITES_ENABLED=false",
            ]
        ),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for name in (
        "OTG_ANALYTICS_WRITES_ENABLED",
        "OTG_SITE_ANALYTICS_ENABLED",
        "OTG_PRODUCT_EVENTS_ENABLED",
        "OTG_FEEDBACK_WRITES_ENABLED",
        "OTG_FEEDBACK_TELEGRAM_ENABLED",
    ):
        assert f"{name}=false" in result.stdout


def test_explicit_approved_production_repair_enables_only_confirmed_write_paths(tmp_path):
    result = _run_flag_transform(
        tmp_path,
        "OTG_ANALYTICS_WRITES_ENABLED=false\nOTG_FEEDBACK_WRITES_ENABLED=false\nOTG_FEEDBACK_TELEGRAM_ENABLED=false\n",
        approved=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for name in (
        "OTG_ANALYTICS_WRITES_ENABLED",
        "OTG_SITE_ANALYTICS_ENABLED",
        "OTG_PRODUCT_EVENTS_ENABLED",
        "OTG_FEEDBACK_WRITES_ENABLED",
    ):
        assert f"{name}=true" in result.stdout
    assert "OTG_FEEDBACK_TELEGRAM_ENABLED=false" in result.stdout


def test_flag_preservation_does_not_emit_secret_values(tmp_path):
    secret = "test-only-secret-must-not-be-printed"
    result = _run_flag_transform(
        tmp_path,
        f"POSTGRES_PASSWORD={secret}\nOTG_FEEDBACK_WRITES_ENABLED=true\n",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert secret not in result.stderr


def test_sandbox_proves_exact_feature_flag_rollback_and_existing_contracts():
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(OPS / "validate_production_tooling_sandbox.ps1"),
            "-Execute",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SANDBOX_FEATURE_FLAG_ROLLBACK=PASS" in result.stdout
    assert "SANDBOX_STATE_RESTORED=PASS" in result.stdout


def test_feedback_and_analytics_code_remain_fail_closed_when_disabled():
    feedback = (ROOT / "streamlit_opensea_sales" / "feedback_store.py").read_text(encoding="utf-8")
    analytics = (ROOT / "streamlit_opensea_sales" / "analytics_config.py").read_text(encoding="utf-8")
    events = (ROOT / "streamlit_opensea_sales" / "site_product_events.py").read_text(encoding="utf-8")
    assert "if not feedback_writes_enabled():" in feedback
    assert 'return "disabled"' in feedback
    assert 'return strict_env_bool("OTG_ANALYTICS_WRITES_ENABLED")' in analytics
    assert "OTG_PRODUCT_EVENTS_ENABLED" in events
