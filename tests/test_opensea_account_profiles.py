import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
APP = ROOT / "streamlit_opensea_sales"
SPEC = importlib.util.spec_from_file_location("profile_refresh", ROOT / "scripts" / "refresh_opensea_account_profiles.py")
refresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)

from opensea_account_profiles import load_profile_snapshot, safe_avatar_css  # noqa: E402


def test_snapshot_rewrite_is_visible_without_cache_clear(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps({"schema_version": 1, "profiles": {"a": {"username": "one"}}}), encoding="utf-8")
    assert load_profile_snapshot(path)["profiles"]["a"]["username"] == "one"
    path.write_text(json.dumps({"schema_version": 1, "profiles": {"a": {"username": "two"}}}), encoding="utf-8")
    assert load_profile_snapshot(path)["profiles"]["a"]["username"] == "two"


def test_remote_avatar_css_accepts_only_http_https():
    assert safe_avatar_css({"profile_image_url": "https://i2c.seadn.io/avatar.png"}).startswith('url("https://')
    assert safe_avatar_css({"profile_image_url": "javascript:alert(1)"}) == ""
    assert safe_avatar_css({"profile_image_url": "data:image/png;base64,abc"}) == ""


def test_wallet_target_does_not_read_snapshot_wallets(monkeypatch, tmp_path):
    output = tmp_path / "profiles.json"
    monkeypatch.setattr(refresh, "PROFILE_SNAPSHOT", output)
    monkeypatch.setattr(refresh, "_load_key", lambda: "test-key")
    monkeypatch.setattr(refresh, "_wallets", lambda: [])
    monkeypatch.setattr(refresh, "_request", lambda wallet, key: ("ok", {"address": wallet, "username": "x"}, {"rate_limit_remaining": 10, "rate_limit_reset": 0}))
    result = refresh.refresh(wallet="0x" + "a" * 40, force=True)
    assert result["successful"] == 1
    assert json.loads(output.read_text(encoding="utf-8"))["profiles"]["0x" + "a" * 40]["username"] == "x"


def test_stale_and_error_are_selected_and_transient_error_preserves_updated_at(monkeypatch, tmp_path):
    output = tmp_path / "profiles.json"
    old_time = "2026-01-01T00:00:00+00:00"
    wallet = "0x" + "b" * 40
    output.write_text(json.dumps({"schema_version": 1, "profiles": {wallet: {"wallet": wallet, "username": "old", "status": "stale", "updated_at": old_time}}}), encoding="utf-8")
    monkeypatch.setattr(refresh, "PROFILE_SNAPSHOT", output)
    monkeypatch.setattr(refresh, "_load_key", lambda: "test-key")
    monkeypatch.setattr(refresh, "_wallets", lambda: [wallet])
    monkeypatch.setattr(refresh, "_request", lambda wallet, key: ("error", {}, {"rate_limit_remaining": 10, "rate_limit_reset": 0}))
    result = refresh.refresh()
    saved = json.loads(output.read_text(encoding="utf-8"))["profiles"][wallet]
    assert result["attempted"] == 1 and saved["status"] == "stale"
    assert saved["updated_at"] == old_time
    assert "last_attempt_at" in saved


def test_rate_limit_stops_batch_without_overwriting_good_profile(monkeypatch, tmp_path):
    output = tmp_path / "profiles.json"
    wallets = ["0x" + "c" * 40, "0x" + "d" * 40]
    output.write_text(json.dumps({"schema_version": 1, "profiles": {wallets[0]: {"wallet": wallets[0], "username": "old", "status": "ok", "updated_at": "2026-01-01T00:00:00+00:00"}}}), encoding="utf-8")
    monkeypatch.setattr(refresh, "PROFILE_SNAPSHOT", output)
    monkeypatch.setattr(refresh, "_load_key", lambda: "test-key")
    monkeypatch.setattr(refresh, "_wallets", lambda: wallets)
    monkeypatch.setattr(refresh, "_request", lambda wallet, key: ("rate_limited", {}, {"rate_limit_remaining": 0, "rate_limit_reset": 123}))
    result = refresh.refresh(force=True)
    saved = json.loads(output.read_text(encoding="utf-8"))["profiles"][wallets[0]]
    assert result["stopped_for_rate_limit"] is True
    assert saved["username"] == "old"
