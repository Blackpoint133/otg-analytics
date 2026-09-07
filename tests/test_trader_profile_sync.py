import importlib.util
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("profile_sync", ROOT / "scripts" / "run_trader_profile_sync.py")
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


def test_sync_defaults_and_overlap_protection(monkeypatch, tmp_path):
    lock = tmp_path / "sync.lock"
    monkeypatch.setattr(sync, "LOCK_PATH", lock)
    monkeypatch.setattr(sync, "refresh", lambda **kwargs: {"attempted": 0, "min_remaining": kwargs["min_remaining"]})
    first = sync.acquire_lock(lock)
    assert first is not None
    second = sync.acquire_lock(lock)
    assert second is None
    sync.release_lock(first)
    third = sync.acquire_lock(lock)
    assert third is not None
    sync.release_lock(third)
    result = sync.run_once()
    assert result["status"] == "completed"
    assert result["min_remaining"] == sync.DEFAULT_MIN_REMAINING == 60
    assert "os.kill" not in (ROOT / "scripts" / "run_trader_profile_sync.py").read_text(encoding="utf-8")


def test_sync_entrypoint_uses_one_safe_batch(monkeypatch, tmp_path):
    lock = tmp_path / "sync.lock"
    monkeypatch.setattr(sync, "LOCK_PATH", lock)
    calls = []
    monkeypatch.setattr(sync, "refresh", lambda **kwargs: calls.append(kwargs) or {"attempted": 2})
    result = sync.run_once()
    assert result["status"] == "completed"
    assert calls == [{"limit": 20, "min_remaining": 60, "stale_hours": 720}]


def test_trader_visible_title_is_renamed():
    trader = (ROOT / "streamlit_opensea_sales" / "ui" / "trader_overview.py").read_text(encoding="utf-8")
    mode = (ROOT / "streamlit_opensea_sales" / "ui" / "mode_switch.py").read_text(encoding="utf-8")
    sidebar = (ROOT / "streamlit_opensea_sales" / "ui" / "sidebar.py").read_text(encoding="utf-8")
    assert "TOP TRADERS ANALYTICS" in trader
    assert "TOP TRADERS ANALYTICS" in mode
    assert "Top Traders Analytics Options" in sidebar
