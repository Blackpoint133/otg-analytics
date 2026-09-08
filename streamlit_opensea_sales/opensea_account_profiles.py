"""Read-only access to prepared OpenSea account profile metadata."""

from __future__ import annotations

import base64
import hashlib
import json
import zlib
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import json as _json

from trader_analytics import normalize_wallet

SNAPSHOT_PATH = Path(__file__).parent / "data_opensea_sales" / "opensea_account_profiles_snapshot.json"
FALLBACK_AVATAR_DIR = Path(__file__).parent.parent / "img" / "profile_avatar"
FALLBACK_AVATAR_COUNT = 94


def fallback_name(wallet: str) -> str:
    canonical = normalize_wallet(wallet) or str(wallet).strip().lower()
    return f"NoName{zlib.crc32(canonical.encode('utf-8')) % 10000:04d}"


def valid_fallback_name(value: Any) -> bool:
    value = str(value or "")
    return len(value) == 10 and value.startswith("NoName") and value[6:].isdigit()


def allocate_fallback_names(wallets: list[str], existing: dict[str, Any] | None = None) -> dict[str, str]:
    canonical_wallets = sorted({normalize_wallet(wallet) or str(wallet).strip().lower() for wallet in wallets if str(wallet).strip()})
    result: dict[str, str] = {}
    used: set[int] = set()
    for wallet, alias in (existing or {}).items():
        canonical = normalize_wallet(wallet) or str(wallet).strip().lower()
        suffix = str(alias)[6:] if valid_fallback_name(alias) else ""
        if canonical in canonical_wallets and suffix and int(suffix) not in used:
            result[canonical] = str(alias)
            used.add(int(suffix))
    if len(canonical_wallets) > 10000:
        raise ValueError("NoName#### namespace exhausted")
    for wallet in canonical_wallets:
        if wallet in result:
            continue
        start = zlib.crc32(wallet.encode("utf-8")) % 10000
        for offset in range(10000):
            suffix = (start + offset) % 10000
            if suffix not in used:
                result[wallet] = f"NoName{suffix:04d}"
                used.add(suffix)
                break
        else:
            raise ValueError("NoName#### namespace exhausted")
    return result


def profile_name(wallet: str, profile: dict[str, Any] | None, fallback_names: dict[str, str] | None = None) -> str:
    profile = profile or {}
    display = str(profile.get("display_name") or "").strip()
    username = str(profile.get("username") or "").strip()
    canonical = normalize_wallet(wallet) or str(wallet).strip().lower()
    persisted = (fallback_names or {}).get(canonical)
    return display or username or (persisted if valid_fallback_name(persisted) else fallback_name(wallet))


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


def fallback_avatar_filename(wallet: str) -> str:
    wallet_key = str(wallet or "").strip().lower()
    if not wallet_key:
        index = 1
    else:
        digest = hashlib.sha256(wallet_key.encode("utf-8")).digest()
        index = int.from_bytes(digest[:8], "big") % FALLBACK_AVATAR_COUNT + 1
    return f"avatar_{index:03d}.png"


@lru_cache(maxsize=FALLBACK_AVATAR_COUNT + 1)
def fallback_avatar_data_uri(wallet: str = "") -> str:
    try:
        encoded = base64.b64encode((FALLBACK_AVATAR_DIR / fallback_avatar_filename(wallet)).read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except OSError:
        return ""


def avatar_url(profile: dict[str, Any] | None) -> str:
    value = str((profile or {}).get("profile_image_url") or "").strip()
    parsed = urlparse(value)
    return value if parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc) else ""


def safe_avatar_css(profile: dict[str, Any] | None) -> str:
    """Return a quoted CSS url() only for a valid HTTP(S) remote avatar."""
    value = avatar_url(profile)
    if not value:
        return ""
    escaped = _json.dumps(value, ensure_ascii=True)[1:-1]
    return f'url("{escaped}")'
