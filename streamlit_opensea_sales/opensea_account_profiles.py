"""Read-only access to prepared OpenSea account profile metadata."""

from __future__ import annotations

import base64
import json
import zlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from trader_analytics import normalize_wallet

SNAPSHOT_PATH = Path(__file__).parent / "data_opensea_sales" / "opensea_account_profiles_snapshot.json"
FALLBACK_AVATAR_PATH = Path(__file__).parent.parent / "img" / "profile_avatar" / "profile_avatar_1.png"


def fallback_name(wallet: str) -> str:
    canonical = normalize_wallet(wallet) or str(wallet).strip().lower()
    return f"NoName{zlib.crc32(canonical.encode('utf-8')) % 10000:04d}"


def profile_name(wallet: str, profile: dict[str, Any] | None) -> str:
    profile = profile or {}
    return str(profile.get("display_name") or profile.get("username") or fallback_name(wallet)).strip()


@lru_cache(maxsize=4)
def load_profile_snapshot(path: str | Path = SNAPSHOT_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1 or not isinstance(payload.get("profiles"), dict):
            return {"schema_version": 1, "profiles": {}}
        return payload
    except (OSError, ValueError, TypeError):
        return {"schema_version": 1, "profiles": {}}


def get_profile(wallet: str, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    canonical = normalize_wallet(wallet)
    profiles = (snapshot or load_profile_snapshot()).get("profiles", {})
    profile = profiles.get(canonical or str(wallet).strip().lower(), {})
    return profile if isinstance(profile, dict) else {}


@lru_cache(maxsize=1)
def fallback_avatar_data_uri() -> str:
    try:
        encoded = base64.b64encode(FALLBACK_AVATAR_PATH.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except OSError:
        return ""


def avatar_url(profile: dict[str, Any] | None) -> str:
    return str((profile or {}).get("profile_image_url") or fallback_avatar_data_uri())
