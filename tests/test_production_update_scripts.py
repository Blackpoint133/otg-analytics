from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPTS = [ROOT / "ops/production" / n for n in ("backup_production.ps1", "deploy_production.ps1", "rollback_production.ps1")]

def test_scripts_have_dry_run_guard_and_approval():
    for path in SCRIPTS:
        text = path.read_text(encoding="utf-8")
        assert "[switch]$Execute" in text
        assert "PLAN_ONLY" in text or "PLAN_ONLY" in (ROOT / "ops/production/production_update_common.ps1").read_text(encoding="utf-8")
        assert "Invoke-GuardedAction" in text
        assert "ApprovalPhrase" in text
        common = (ROOT / "ops/production/production_update_common.ps1").read_text(encoding="utf-8")
        assert ("8501" in text and "8504" in text) or ("ForbiddenPorts" in common)
        assert "app_gaming_marketplace.py" in text or "ForbiddenApp" in common
        assert "C:\\VAMBAM\\Projects\\OTG\\data_streamlit\\opensea_sales" in text or "ExpectedRoot" in common

def test_deploy_contract_is_fail_closed():
    text = SCRIPTS[1].read_text(encoding="utf-8")
    assert "ExpectedOldHead" in text
    assert "BackupManifest" in text
    assert "merge --ff-only" in text
    assert "MAIN_PROMOTION_REQUIRED" in text
    assert "production_worktree_not_clean" in text.lower()
    assert "git clean" not in text.lower()

def test_rollback_does_not_automatically_restore_database():
    text = SCRIPTS[2].read_text(encoding="utf-8")
    assert "NOT_AUTOMATIC" in text
    assert "git clean" not in text.lower()
