"""Refresh OpenSea account profiles with fair scheduling and safe diagnostics."""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))
from opensea_account_profiles import allocate_fallback_names  # noqa: E402

TRADER_SNAPSHOT = APP / "data_opensea_sales" / "trader_analytics_snapshot.json"
PROFILE_SNAPSHOT = APP / "data_opensea_sales" / "opensea_account_profiles_snapshot.json"
SYNC_STATE_FILENAME = "opensea_account_profile_sync_state.json"
SYNC_STATE_PATH = PROFILE_SNAPSHOT.with_name(SYNC_STATE_FILENAME)
ENV_FILE = Path(r"C:\VAMBAM\Projects\OTG\parsers\.env")
API = "https://api.opensea.io/api/v2/accounts/"
DEFAULT_REQUEST_LIMIT = 20
DEFAULT_MIN_REMAINING = 60
BACKOFF_BASE_SECONDS = 3600
BACKOFF_MAX_SECONDS = 24 * 3600
RETRYABLE_RESULTS = {"error", "rate_limited"}


def _load_key() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("OPENSEA_API_KEY="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    raise RuntimeError("OPENSEA_API_KEY was not found in the approved .env")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else copy.deepcopy(default)
    except (OSError, ValueError, TypeError):
        return copy.deepcopy(default)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _sync_state_file() -> Path:
    """Resolve beside the active profile path so tests and isolated runs stay isolated."""
    return PROFILE_SNAPSHOT.with_name(SYNC_STATE_FILENAME)


def _load_sync_state(path: Path | None = None) -> dict[str, Any]:
    payload = _load_json(path or _sync_state_file(), {})
    raw_wallets = payload.get("wallets")
    wallets: dict[str, dict[str, Any]] = {}
    if isinstance(raw_wallets, dict):
        for wallet, entry in raw_wallets.items():
            if isinstance(entry, dict) and str(wallet).strip():
                try:
                    failures = int(entry.get("consecutive_failures") or 0)
                except (TypeError, ValueError):
                    failures = 0
                wallets[str(wallet).strip().lower()] = {
                    "last_attempt_at": entry.get("last_attempt_at"),
                    "last_attempt_result": entry.get("last_attempt_result"),
                    "consecutive_failures": max(0, failures),
                    "next_retry_at": entry.get("next_retry_at"),
                    "last_http_status": entry.get("last_http_status"),
                    "last_response_class": entry.get("last_response_class"),
                    "last_exception_class": entry.get("last_exception_class"),
                    "last_rate_limit_remaining": entry.get("last_rate_limit_remaining"),
                    "last_rate_limit_reset": entry.get("last_rate_limit_reset"),
                }
    last_run = payload.get("last_run")
    return {
        "schema_version": 1,
        "wallets": wallets,
        "last_run": copy.deepcopy(last_run) if isinstance(last_run, dict) else {},
    }


def _wallets() -> list[str]:
    payload = _load_json(TRADER_SNAPSHOT, {})
    result: list[str] = []
    seen: set[str] = set()
    for row in payload.get("wallets", []):
        if not isinstance(row, dict) or not row.get("wallet"):
            continue
        wallet = str(row["wallet"]).strip().lower()
        if wallet not in seen:
            result.append(wallet)
            seen.add(wallet)
    return result


def _rate_metadata(status: int | None, headers: dict[str, str], response_class: str = "") -> dict[str, Any]:
    def number(name: str) -> int | None:
        try:
            return int(headers.get(name, ""))
        except (TypeError, ValueError):
            return None

    return {
        "http_status": status,
        "response_class": response_class,
        "exception_class": None,
        "rate_limit_limit": number("x-ratelimit-limit"),
        "rate_limit_remaining": number("x-ratelimit-remaining"),
        "rate_limit_reset": number("x-ratelimit-reset"),
    }


def _request(wallet: str, key: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
    request = urllib.request.Request(
        API + wallet,
        headers={"X-API-KEY": key, "Accept": "application/json", "User-Agent": "OTG-Analytics-profile-refresh/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            headers = {name.lower(): value for name, value in response.headers.items()}
            status = "ok" if data.get("address") else "no_profile"
            return status, data, _rate_metadata(response.status, headers, "success_response")
    except urllib.error.HTTPError as exc:
        headers = {name.lower(): value for name, value in exc.headers.items()}
        status = "rate_limited" if exc.code == 429 else "not_found" if exc.code == 404 else "error"
        metadata = _rate_metadata(exc.code, headers, "rate_limited" if exc.code == 429 else "http_error")
        metadata["exception_class"] = type(exc).__name__
        return status, {}, metadata
    except OSError as exc:
        metadata = _rate_metadata(None, {}, "network_error")
        metadata["exception_class"] = type(exc).__name__
        return "error", {}, metadata
    except (ValueError, UnicodeError) as exc:
        metadata = _rate_metadata(None, {}, "invalid_response")
        metadata["exception_class"] = type(exc).__name__
        return "error", {}, metadata


def _parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _retry_delay(failures: int) -> int:
    return min(BACKOFF_MAX_SECONDS, BACKOFF_BASE_SECONDS * (2 ** max(0, failures - 1)))


def _next_retry_at(now: datetime, failures: int, rate: dict[str, Any], result: str) -> str:
    retry_at = now + timedelta(seconds=_retry_delay(failures))
    reset = rate.get("rate_limit_reset")
    if result == "rate_limited":
        try:
            reset_at = datetime.fromtimestamp(int(reset), timezone.utc)
            if now < reset_at:
                retry_at = max(retry_at, reset_at)
        except (TypeError, ValueError, OSError, OverflowError):
            pass
    return retry_at.isoformat()


def _record_attempt(state: dict[str, Any], wallet: str, result: str, now: datetime, rate: dict[str, Any]) -> None:
    previous = state["wallets"].get(wallet, {})
    failures = int(previous.get("consecutive_failures") or 0)
    if result in RETRYABLE_RESULTS:
        failures += 1
        next_retry = _next_retry_at(now, failures, rate, result)
    else:
        failures = 0
        next_retry = None
    state["wallets"][wallet] = {
        "last_attempt_at": now.isoformat(),
        "last_attempt_result": result,
        "consecutive_failures": failures,
        "next_retry_at": next_retry,
        "last_http_status": rate.get("http_status"),
        "last_response_class": rate.get("response_class"),
        "last_exception_class": rate.get("exception_class"),
        "last_rate_limit_remaining": rate.get("rate_limit_remaining"),
        "last_rate_limit_reset": rate.get("rate_limit_reset"),
    }


def _is_due(wallet: str, profiles: dict[str, Any], state: dict[str, Any], cutoff: datetime, now: datetime, force: bool) -> bool:
    history = state["wallets"].get(wallet, {})
    if not force:
        next_retry = _parse_time(history.get("next_retry_at"))
        if next_retry and next_retry > now:
            return False
    profile = profiles.get(wallet)
    if force or not isinstance(profile, dict) or not profile:
        return True
    if profile.get("status") in {"stale", "error"}:
        return True
    updated = _parse_time(profile.get("updated_at"))
    return updated is None or updated < cutoff


def _eligible_targets(targets: list[str], profiles: dict[str, Any], state: dict[str, Any], cutoff: datetime, now: datetime, force: bool) -> list[str]:
    eligible = [wallet for wallet in targets if _is_due(wallet, profiles, state, cutoff, now, force)]
    position = {wallet: index for index, wallet in enumerate(targets)}

    def key(wallet: str) -> tuple[int, datetime, int]:
        history = state["wallets"].get(wallet, {})
        attempted = _parse_time(history.get("last_attempt_at"))
        if attempted is None:
            return 0, datetime.min.replace(tzinfo=timezone.utc), position[wallet]
        return 1, attempted, position[wallet]

    return sorted(eligible, key=key)


def _profile_from_response(wallet: str, data: dict[str, Any], status: str, now: datetime) -> dict[str, Any]:
    return {
        "wallet": wallet,
        "username": data.get("username"),
        "display_name": data.get("display_name"),
        "profile_image_url": data.get("profile_image_url"),
        "is_verified": bool(data.get("is_verified")),
        "ens_name": data.get("ens_name"),
        "bio": data.get("bio"),
        "website": data.get("website"),
        "status": status,
        "updated_at": now.isoformat(),
    }


def refresh(
    limit: int | None = None,
    wallet: str | None = None,
    force: bool = False,
    stale_hours: float = 168,
    min_remaining: int = DEFAULT_MIN_REMAINING,
) -> dict[str, Any]:
    started = _now()
    existing = _load_json(PROFILE_SNAPSHOT, {"schema_version": 1, "source": "opensea", "profiles": {}})
    existing_profiles = existing.get("profiles", {}) if isinstance(existing.get("profiles"), dict) else {}
    profiles = copy.deepcopy(existing_profiles)
    existing_fallback_names = existing.get("fallback_names", {}) if isinstance(existing.get("fallback_names"), dict) else {}
    targets = [wallet.strip().lower()] if wallet else _wallets()
    all_wallets = list(dict.fromkeys(_wallets() + targets))
    fallback_names = allocate_fallback_names(all_wallets, existing_fallback_names)
    requested_limit = DEFAULT_REQUEST_LIMIT if limit is None else max(0, limit)
    state = _load_sync_state()
    cutoff = started - timedelta(hours=stale_hours)
    eligible = _eligible_targets(targets, profiles, state, cutoff, started, force)
    selected = eligible[:requested_limit]
    key = _load_key() if selected else ""
    diagnostics: dict[str, Any] = {
        "started_at": started.isoformat(),
        "completed_at": None,
        "requested_limit": requested_limit,
        "candidate_count": len(eligible),
        "selected_count": len(selected),
        "requested": len(selected),
        "attempted": 0,
        "successful": 0,
        "not_found": 0,
        "no_profile": 0,
        "errors": 0,
        "rate_limited": 0,
        "remaining_targets": len(eligible),
        "rate_limit_limit": None,
        "rate_limit_remaining": None,
        "rate_limit_reset": None,
        "min_remaining": min_remaining,
        "stopped_for_rate_limit": False,
        "stopped_for_reserve": False,
        "snapshot_write_executed": False,
    }
    for item in selected:
        attempt_time = _now()
        diagnostics["attempted"] += 1
        status, data, rate = _request(item, key)
        diagnostics["rate_limit_limit"] = rate.get("rate_limit_limit")
        diagnostics["rate_limit_remaining"] = rate.get("rate_limit_remaining")
        diagnostics["rate_limit_reset"] = rate.get("rate_limit_reset")
        _record_attempt(state, item, status, attempt_time, rate)
        if status in {"ok", "no_profile", "not_found"}:
            profiles[item] = _profile_from_response(item, data, status, attempt_time)
            diagnostics["successful"] += status == "ok"
            diagnostics["not_found"] += status == "not_found"
            diagnostics["no_profile"] += status == "no_profile"
        elif status == "rate_limited":
            diagnostics["rate_limited"] += 1
            diagnostics["stopped_for_rate_limit"] = True
            diagnostics["remaining_targets"] = len(eligible) - diagnostics["attempted"]
            break
        else:
            diagnostics["errors"] += 1
            remaining = rate.get("rate_limit_remaining")
            if remaining is not None and remaining <= min_remaining:
                diagnostics["stopped_for_reserve"] = True
                diagnostics["remaining_targets"] = len(eligible) - diagnostics["attempted"]
                break
        diagnostics["remaining_targets"] = len(eligible) - diagnostics["attempted"]
        remaining = rate.get("rate_limit_remaining")
        if remaining is not None and remaining <= min_remaining:
            diagnostics["stopped_for_reserve"] = True
            break

    profile_data_changed = profiles != existing_profiles or fallback_names != existing_fallback_names
    if profile_data_changed:
        output = copy.deepcopy(existing)
        output.update({
            "schema_version": 1,
            "generated_at": _now().isoformat(),
            "source": "opensea",
            "profiles": profiles,
            "fallback_names": fallback_names,
        })
        _atomic_write_json(PROFILE_SNAPSHOT, output)
    diagnostics["snapshot_write_executed"] = profile_data_changed
    diagnostics["completed_at"] = _now().isoformat()
    state["last_run"] = copy.deepcopy(diagnostics)
    state["updated_at"] = diagnostics["completed_at"]
    _atomic_write_json(_sync_state_file(), state)
    return diagnostics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=DEFAULT_REQUEST_LIMIT)
    parser.add_argument("--wallet")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--stale-hours", type=float, default=168)
    parser.add_argument("--min-remaining", type=int, default=DEFAULT_MIN_REMAINING)
    args = parser.parse_args()
    print(json.dumps(refresh(args.limit, args.wallet, args.force, args.stale_hours, args.min_remaining), sort_keys=True))


if __name__ == "__main__":
    main()
