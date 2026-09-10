import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
APP = ROOT / "streamlit_opensea_sales"
SPEC = importlib.util.spec_from_file_location("profile_refresh", ROOT / "scripts" / "refresh_opensea_account_profiles.py")
refresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)

from opensea_account_profiles import allocate_fallback_names, avatar_style_attribute, fallback_avatar_filename, load_profile_snapshot, profile_name, safe_avatar_css  # noqa: E402


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


def test_fallback_avatar_is_deterministic_and_normalized():
    assert fallback_avatar_filename(" 0xABC123 ") == fallback_avatar_filename("0xabc123")
    assert fallback_avatar_filename("") == "avatar_001.png"
    assert fallback_avatar_filename("0xabc123").startswith("avatar_")
    assert 1 <= int(fallback_avatar_filename("0xabc123")[7:10]) <= 94


def test_fallback_avatar_set_is_fixed_and_legacy_reference_is_gone():
    avatar_dir = ROOT / "img" / "profile_avatar"
    assert sorted(p.name for p in avatar_dir.glob("avatar_*.png")) == [f"avatar_{i:03d}.png" for i in range(1, 95)]
    source = (ROOT / "streamlit_opensea_sales" / "opensea_account_profiles.py").read_text(encoding="utf-8")
    assert "profile_" + "avatar_1.png" not in source
    assert "random(" not in source


def test_avatar_style_attribute_escapes_complete_style_value():
    fallback = avatar_style_attribute({}, "0xabc123")
    remote = avatar_style_attribute({"profile_image_url": "https://example.com/avatar.png"}, "0xabc123")
    assert fallback.startswith('style="') and fallback.endswith('"')
    assert 'url("data:' not in fallback
    assert "--trader-fallback-avatar:url(&#x27;data:image/png;base64," in fallback
    assert "--trader-remote-avatar:none;" in fallback
    assert "--trader-remote-avatar:url(&quot;https://example.com/avatar.png&quot;);" in remote
    assert "--trader-fallback-avatar:none;" in remote
    assert "data:image/png;base64" not in remote
    assert remote.index("--trader-remote-avatar") < remote.index("--trader-fallback-avatar")


def test_mixed_avatar_rows_keep_structural_markup_and_wallet_mapping():
    rows = []
    for index in range(30):
        wallet = f"0x{index:040x}"
        profile = {"profile_image_url": "https://example.com/avatar.png"} if index % 2 else {}
        style = avatar_style_attribute(profile, wallet)
        rows.append(f'<span class="trader-avatar trader-avatar-small" {style}></span>')
    markup = "".join(rows)
    assert markup.count('<span class="trader-avatar trader-avatar-small"') == 30
    assert markup.count("</span>") == 30
    assert "<span class=\"trader-avatar" not in markup.replace('<span class="trader-avatar trader-avatar-small"', "")
    assert all(fallback_avatar_filename(f"0x{index:040x}").startswith("avatar_") for index in range(30))


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


def test_1334_aliases_are_unique_and_stable_when_wallets_are_added():
    wallets = [f"0x{i:040x}" for i in range(1334)]
    first = allocate_fallback_names(wallets)
    second = allocate_fallback_names(wallets, first)
    expanded = allocate_fallback_names(wallets + ["0x" + "f" * 40], first)
    assert len(first) == len(set(first.values())) == 1334
    assert all(__import__("re").fullmatch(r"NoName\d{4}", value) for value in first.values())
    assert second == first
    assert all(expanded[wallet] == first[wallet] for wallet in wallets)


def test_alias_collision_uses_deterministic_linear_probe(monkeypatch):
    monkeypatch.setattr("opensea_account_profiles.zlib.crc32", lambda value: 7)
    aliases = allocate_fallback_names(["0x" + "a" * 40, "0x" + "b" * 40])
    assert len(set(aliases.values())) == 2
    assert set(aliases.values()) == {"NoName0007", "NoName0008"}


def test_whitespace_profile_names_use_username_then_persisted_alias():
    wallet = "0x" + "a" * 40
    assert profile_name(wallet, {"display_name": "   ", "username": " TraderOne\t"}, {wallet: "NoName0001"}) == "TraderOne"
    assert profile_name(wallet, {"display_name": " ", "username": "\t"}, {wallet: "NoName0001"}) == "NoName0001"


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


def test_default_request_cap_and_reserve_are_conservative():
    assert refresh.DEFAULT_REQUEST_LIMIT == 20
    assert refresh.DEFAULT_MIN_REMAINING == 60


def test_reserve_stops_before_next_request_and_persists_current_result(monkeypatch, tmp_path):
    output = tmp_path / "profiles.json"
    wallets = [f"0x{i:040x}" for i in range(3)]
    output.write_text(json.dumps({"schema_version": 1, "profiles": {}}), encoding="utf-8")
    calls = []
    monkeypatch.setattr(refresh, "PROFILE_SNAPSHOT", output)
    monkeypatch.setattr(refresh, "_load_key", lambda: "test-key")
    monkeypatch.setattr(refresh, "_wallets", lambda: wallets)
    def request(wallet, key):
        calls.append(wallet)
        return "ok", {"address": wallet, "username": "x"}, {"rate_limit_limit": 120, "rate_limit_remaining": 60, "rate_limit_reset": 123}
    monkeypatch.setattr(refresh, "_request", request)
    result = refresh.refresh(limit=100)
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert calls == [wallets[0]]
    assert result["stopped_for_reserve"] is True
    assert result["remaining_targets"] == 2
    assert wallets[0] in saved["profiles"]


def test_remaining_above_reserve_may_proceed(monkeypatch, tmp_path):
    output = tmp_path / "profiles.json"
    wallets = [f"0x{i:040x}" for i in range(2)]
    output.write_text(json.dumps({"schema_version": 1, "profiles": {}}), encoding="utf-8")
    calls = []
    monkeypatch.setattr(refresh, "PROFILE_SNAPSHOT", output)
    monkeypatch.setattr(refresh, "_load_key", lambda: "test-key")
    monkeypatch.setattr(refresh, "_wallets", lambda: wallets)
    def request(wallet, key):
        calls.append(wallet)
        return "ok", {"address": wallet}, {"rate_limit_limit": 120, "rate_limit_remaining": 61, "rate_limit_reset": 123}
    monkeypatch.setattr(refresh, "_request", request)
    result = refresh.refresh(limit=2)
    assert len(calls) == 2
    assert result["stopped_for_reserve"] is False


def test_limit_zero_does_housekeeping_without_request(monkeypatch, tmp_path):
    output = tmp_path / "profiles.json"
    wallet = "0x" + "a" * 40
    output.write_text(json.dumps({"schema_version": 1, "profiles": {}}), encoding="utf-8")
    monkeypatch.setattr(refresh, "PROFILE_SNAPSHOT", output)
    monkeypatch.setattr(refresh, "_wallets", lambda: [wallet])
    monkeypatch.setattr(refresh, "_request", lambda *args: (_ for _ in ()).throw(AssertionError("network request")))
    monkeypatch.setattr(refresh, "_load_key", lambda: (_ for _ in ()).throw(AssertionError("key load")))
    result = refresh.refresh(limit=0)
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert result["attempted"] == 0
    assert result["requested_limit"] == 0
    assert wallet in saved["fallback_names"]
