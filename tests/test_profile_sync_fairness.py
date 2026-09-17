from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("profile_sync_fairness", ROOT / "scripts" / "refresh_opensea_account_profiles.py")
sync = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(sync)


def wallet(index: int) -> str:
    return f"0x{index:040x}"


def make_profile(address: str, status: str = "ok", **fields):
    profile = {
        "wallet": address,
        "username": None,
        "display_name": None,
        "profile_image_url": None,
        "is_verified": False,
        "ens_name": None,
        "bio": None,
        "website": None,
        "status": status,
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    profile.update(fields)
    return profile


def configure(monkeypatch, tmp_path, wallets, profiles=None, clock=None):
    output = tmp_path / "profiles.json"
    profiles = profiles or {}
    output.write_text(
        json.dumps({
            "schema_version": 1,
            "generated_at": "2026-01-01T00:00:00+00:00",
            "source": "opensea",
            "profiles": profiles,
            "fallback_names": sync.allocate_fallback_names(wallets),
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(sync, "PROFILE_SNAPSHOT", output)
    monkeypatch.setattr(sync, "_wallets", lambda: list(wallets))
    monkeypatch.setattr(sync, "_load_key", lambda: "unit-test-secret-key")
    if clock is not None:
        monkeypatch.setattr(sync, "_now", lambda: clock[0])
    return output, output.with_name(sync.SYNC_STATE_FILENAME)


def error_result(status="error", http_status=503, response_class="http_error"):
    return status, {}, {"http_status": http_status, "response_class": response_class, "exception_class": "HTTPError", "rate_limit_remaining": None, "rate_limit_reset": None}


def ok_result(wallet_address, username="fresh"):
    return "ok", {"address": wallet_address, "username": username, "display_name": username}, {"http_status": 200, "response_class": "success_response", "rate_limit_remaining": 100, "rate_limit_reset": None}


def test_failing_first_batch_does_not_starve_later_wallets(monkeypatch, tmp_path):
    wallets = [wallet(i) for i in range(25)]
    clock = [datetime(2026, 9, 17, tzinfo=timezone.utc)]
    configure(monkeypatch, tmp_path, wallets, clock=clock)
    calls = []
    monkeypatch.setattr(sync, "_request", lambda address, key: calls.append(address) or error_result())
    first = sync.refresh(limit=20, min_remaining=0, stale_hours=10000)
    assert first["candidate_count"] == 25 and first["selected_count"] == 20
    assert calls == wallets[:20]
    clock[0] += timedelta(hours=1)
    calls.clear()
    second = sync.refresh(limit=20, min_remaining=0, stale_hours=10000)
    assert calls[:5] == wallets[20:]
    assert set(wallets[20:]).issubset(calls)
    assert second["candidate_count"] == 25


def test_generic_error_persists_attempt_state(monkeypatch, tmp_path):
    address = wallet(1)
    clock = [datetime(2026, 9, 17, tzinfo=timezone.utc)]
    _, state_path = configure(monkeypatch, tmp_path, [address], clock=clock)
    monkeypatch.setattr(sync, "_request", lambda *_: error_result(http_status=502))
    result = sync.refresh(limit=1, min_remaining=0)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    entry = state["wallets"][address]
    assert result["errors"] == 1
    assert entry["last_attempt_result"] == "error"
    assert entry["last_http_status"] == 502
    assert entry["last_response_class"] == "http_error"
    assert entry["consecutive_failures"] == 1
    assert entry["next_retry_at"]


def test_missing_wallet_error_tracks_retry_without_fabricating_profile(monkeypatch, tmp_path):
    address = wallet(2)
    clock = [datetime(2026, 9, 17, tzinfo=timezone.utc)]
    output, state_path = configure(monkeypatch, tmp_path, [address], clock=clock)
    monkeypatch.setattr(sync, "_request", lambda *_: error_result())
    sync.refresh(limit=1, min_remaining=0)
    payload = json.loads(output.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert address not in payload["profiles"]
    assert state["wallets"][address]["last_attempt_result"] == "error"


def test_transient_error_preserves_good_profile_and_snapshot_bytes(monkeypatch, tmp_path):
    address = wallet(3)
    original = make_profile(address, username="KnownUser", display_name="Known User", profile_image_url="https://example.com/a.png", bio="keep", status="ok")
    clock = [datetime(2026, 9, 17, tzinfo=timezone.utc)]
    output, state_path = configure(monkeypatch, tmp_path, [address], {address: original}, clock=clock)
    before = output.read_bytes()
    monkeypatch.setattr(sync, "_request", lambda *_: error_result())
    result = sync.refresh(limit=1, force=True, min_remaining=0)
    saved = json.loads(output.read_text(encoding="utf-8"))["profiles"][address]
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert result["snapshot_write_executed"] is False
    assert output.read_bytes() == before
    assert saved == original
    assert state["wallets"][address]["last_attempt_result"] == "error"


def test_rate_limit_is_persisted_and_does_not_pin_next_run(monkeypatch, tmp_path):
    wallets = [wallet(i) for i in range(3)]
    clock = [datetime(2026, 9, 17, tzinfo=timezone.utc)]
    _, state_path = configure(monkeypatch, tmp_path, wallets, clock=clock)
    calls = []

    def request(address, _):
        calls.append(address)
        if address == wallets[0]:
            return "rate_limited", {}, {"http_status": 429, "response_class": "rate_limited", "exception_class": "HTTPError", "rate_limit_remaining": 0, "rate_limit_reset": int(clock[0].timestamp()) + 7200}
        return ok_result(address)

    monkeypatch.setattr(sync, "_request", request)
    first = sync.refresh(limit=1, min_remaining=0)
    assert first["rate_limited"] == 1 and first["stopped_for_rate_limit"] is True
    saved_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved_state["last_run"]["rate_limited"] == 1
    calls.clear()
    second = sync.refresh(limit=1, min_remaining=0)
    assert calls == [wallets[1]]
    assert second["successful"] == 1


def test_unattempted_wallets_outrank_just_failed_wallet(monkeypatch, tmp_path):
    wallets = [wallet(i) for i in range(3)]
    clock = [datetime(2026, 9, 17, tzinfo=timezone.utc)]
    configure(monkeypatch, tmp_path, wallets, clock=clock)
    calls = []
    monkeypatch.setattr(sync, "_request", lambda address, _: calls.append(address) or error_result())
    sync.refresh(limit=1, min_remaining=0)
    calls.clear()
    sync.refresh(limit=1, min_remaining=0)
    assert calls == [wallets[1]]


def test_backoff_prevents_immediate_retry_hammering(monkeypatch, tmp_path):
    address = wallet(4)
    clock = [datetime(2026, 9, 17, tzinfo=timezone.utc)]
    configure(monkeypatch, tmp_path, [address], clock=clock)
    calls = []
    monkeypatch.setattr(sync, "_request", lambda address, _: calls.append(address) or error_result())
    sync.refresh(limit=1, min_remaining=0)
    calls.clear()
    result = sync.refresh(limit=1, min_remaining=0)
    assert calls == [] and result["attempted"] == 0


def test_successful_retry_resets_failure_state(monkeypatch, tmp_path):
    address = wallet(5)
    clock = [datetime(2026, 9, 17, tzinfo=timezone.utc)]
    _, state_path = configure(monkeypatch, tmp_path, [address], clock=clock)
    responses = [error_result(), ok_result(address, "Recovered")]
    monkeypatch.setattr(sync, "_request", lambda *_: responses.pop(0))
    sync.refresh(limit=1, min_remaining=0)
    clock[0] += timedelta(hours=1)
    result = sync.refresh(limit=1, min_remaining=0)
    entry = json.loads(state_path.read_text(encoding="utf-8"))["wallets"][address]
    assert result["successful"] == 1
    assert entry["last_attempt_result"] == "ok"
    assert entry["consecutive_failures"] == 0
    assert entry["next_retry_at"] is None


def test_authoritative_not_found_updates_profile_state(monkeypatch, tmp_path):
    address = wallet(6)
    clock = [datetime(2026, 9, 17, tzinfo=timezone.utc)]
    output, state_path = configure(monkeypatch, tmp_path, [address], clock=clock)
    monkeypatch.setattr(sync, "_request", lambda *_: ("not_found", {}, {"http_status": 404, "response_class": "http_error", "exception_class": "HTTPError", "rate_limit_remaining": 100, "rate_limit_reset": None}))
    result = sync.refresh(limit=1, min_remaining=0)
    saved = json.loads(output.read_text(encoding="utf-8"))["profiles"][address]
    state = json.loads(state_path.read_text(encoding="utf-8"))["wallets"][address]
    assert result["not_found"] == 1 and saved["status"] == "not_found"
    assert state["consecutive_failures"] == 0 and state["next_retry_at"] is None


def test_successful_profile_response_is_atomically_published(monkeypatch, tmp_path):
    address = wallet(7)
    clock = [datetime(2026, 9, 17, tzinfo=timezone.utc)]
    output, _ = configure(monkeypatch, tmp_path, [address], clock=clock)
    monkeypatch.setattr(sync, "_request", lambda *_: ok_result(address, "NewUser"))
    result = sync.refresh(limit=1, min_remaining=0)
    saved = json.loads(output.read_text(encoding="utf-8"))["profiles"][address]
    assert result["snapshot_write_executed"] is True
    assert saved["status"] == "ok" and saved["username"] == "NewUser"
    assert not list(tmp_path.glob("profiles.json.*.tmp"))


def test_no_semantic_change_keeps_profile_snapshot_sha(monkeypatch, tmp_path):
    address = wallet(8)
    fresh = make_profile(address, username="Stable", display_name="Stable", updated_at="2026-09-17T00:00:00+00:00")
    clock = [datetime(2026, 9, 17, 1, tzinfo=timezone.utc)]
    output, state_path = configure(monkeypatch, tmp_path, [address], {address: fresh}, clock=clock)
    before_sha = hashlib.sha256(output.read_bytes()).hexdigest()
    result = sync.refresh(limit=0, min_remaining=0)
    assert hashlib.sha256(output.read_bytes()).hexdigest() == before_sha
    assert result["snapshot_write_executed"] is False
    assert state_path.exists()


def test_malformed_sync_state_recovers_safely(monkeypatch, tmp_path):
    address = wallet(9)
    _, state_path = configure(monkeypatch, tmp_path, [address])
    state_path.write_text("{not-json", encoding="utf-8")
    result = sync.refresh(limit=0, min_remaining=0)
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert result["attempted"] == 0 and saved["schema_version"] == 1 and saved["wallets"] == {}


def test_full_universe_makes_progress_across_bounded_cycles(monkeypatch, tmp_path):
    wallets = [wallet(i) for i in range(1343)]
    clock = [datetime(2026, 9, 17, tzinfo=timezone.utc)]
    configure(monkeypatch, tmp_path, wallets, clock=clock)
    attempted = []

    def request(address, _):
        attempted.append(address)
        return error_result() if address in wallets[:20] else ok_result(address, "User")

    monkeypatch.setattr(sync, "_request", request)
    for _ in range(68):
        sync.refresh(limit=20, min_remaining=0, stale_hours=10000)
        clock[0] += timedelta(hours=1)
    assert set(attempted) == set(wallets)
    assert len(set(attempted)) == 1343


def test_no_api_key_leaks_to_state_or_diagnostics(monkeypatch, tmp_path):
    address = wallet(10)
    output, state_path = configure(monkeypatch, tmp_path, [address])
    monkeypatch.setattr(sync, "_request", lambda *_: error_result())
    result = sync.refresh(limit=1, min_remaining=0)
    serialized = output.read_text(encoding="utf-8") + state_path.read_text(encoding="utf-8") + json.dumps(result)
    assert "unit-test-secret-key" not in serialized


def test_profile_and_sync_state_contract_is_explicit():
    source = (ROOT / "scripts" / "refresh_opensea_account_profiles.py").read_text(encoding="utf-8")
    assert "SYNC_STATE_FILENAME" in source
    assert "_atomic_write_json(_sync_state_file(), state)" in source
    assert "profile_data_changed" in source
    assert "_eligible_targets" in source
