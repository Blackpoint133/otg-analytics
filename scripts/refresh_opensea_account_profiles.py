"""Refresh prepared OpenSea account profiles using the approved parser .env key."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "streamlit_opensea_sales"
TRADER_SNAPSHOT = APP / "data_opensea_sales" / "trader_analytics_snapshot.json"
PROFILE_SNAPSHOT = APP / "data_opensea_sales" / "opensea_account_profiles_snapshot.json"
ENV_FILE = Path(r"C:\VAMBAM\Projects\OTG\parsers\.env")
API = "https://api.opensea.io/api/v2/accounts/"


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
        return payload if isinstance(payload, dict) else default
    except (OSError, ValueError):
        return default


def _wallets() -> list[str]:
    payload = _load_json(TRADER_SNAPSHOT, {})
    return [str(row["wallet"]).strip().lower() for row in payload.get("wallets", []) if row.get("wallet")]


def _request(wallet: str, key: str) -> tuple[str, dict[str, Any]]:
    request = urllib.request.Request(API + wallet, headers={"X-API-KEY": key, "Accept": "application/json", "User-Agent": "OTG-Analytics-profile-refresh/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return ("ok" if data.get("address") else "no_profile"), data
    except urllib.error.HTTPError as exc:
        return ("not_found" if exc.code == 404 else "error"), {}
    except (OSError, ValueError):
        return "error", {}


def refresh(limit: int | None = None, wallet: str | None = None, force: bool = False, stale_hours: float = 168) -> dict[str, Any]:
    key = _load_key()
    existing = _load_json(PROFILE_SNAPSHOT, {"schema_version": 1, "source": "opensea", "profiles": {}})
    profiles = existing.get("profiles", {}) if isinstance(existing.get("profiles"), dict) else {}
    targets = [_wallets()[0]] if wallet else _wallets()
    if wallet:
        targets = [wallet.strip().lower()]
    cutoff = _now() - timedelta(hours=stale_hours)
    selected = []
    for item in targets:
        old = profiles.get(item, {})
        stale = True
        try: stale = datetime.fromisoformat(str(old.get("updated_at")).replace("Z", "+00:00")) < cutoff
        except (TypeError, ValueError): pass
        if force or not old or stale:
            selected.append(item)
    if limit is not None:
        selected = selected[:max(0, limit)]
    diagnostics = {"requested": len(selected), "successful": 0, "errors": 0}
    for item in selected:
        status, data = _request(item, key)
        if status == "error" and item in profiles:
            profiles[item]["status"] = "stale"
            profiles[item]["updated_at"] = _now().isoformat()
            diagnostics["errors"] += 1
            continue
        profiles[item] = {"wallet": item, "username": data.get("username"), "display_name": data.get("display_name"), "profile_image_url": data.get("profile_image_url"), "is_verified": bool(data.get("is_verified")), "ens_name": data.get("ens_name"), "bio": data.get("bio"), "website": data.get("website"), "status": status, "updated_at": _now().isoformat()}
        diagnostics["successful"] += status == "ok"
        diagnostics["errors"] += status == "error"
    output = {"schema_version": 1, "generated_at": _now().isoformat(), "source": "opensea", "profiles": profiles}
    PROFILE_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=PROFILE_SNAPSHOT.name + ".", dir=PROFILE_SNAPSHOT.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle: json.dump(output, handle, indent=2, sort_keys=True); handle.write("\n")
        os.replace(temporary, PROFILE_SNAPSHOT)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    return diagnostics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--wallet")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--stale-hours", type=float, default=168)
    args = parser.parse_args()
    print(json.dumps(refresh(args.limit, args.wallet, args.force, args.stale_hours), sort_keys=True))


if __name__ == "__main__": main()
