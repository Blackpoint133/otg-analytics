"""Small first-party browser identity component for visitor analytics."""

from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from pathlib import Path
from typing import Any

import streamlit.components.v1 as components


VISITOR_IDENTITY_VERSION = 2
LOCAL_STORAGE_KEY = "otg_analytics_visitor_id_v2"
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

_COMPONENT = components.declare_component(
    "otg_visitor_identity_v2",
    path=str(Path(__file__).parent / "ui" / "visitor_identity_component"),
)


def validate_browser_id(value: Any) -> str | None:
    """Accept only a canonical, version-4 UUID string with a bounded length."""
    if not isinstance(value, str) or len(value) != 36:
        return None
    normalized = value.lower()
    if not _UUID_RE.fullmatch(normalized):
        return None
    try:
        parsed = uuid.UUID(normalized)
    except (ValueError, AttributeError):
        return None
    if parsed.version != 4 or str(parsed) != normalized:
        return None
    return normalized


def browser_visitor_hash(browser_id: Any, secret: str) -> str | None:
    """Return the domain-separated V2 digest, never the raw browser ID."""
    normalized = validate_browser_id(browser_id)
    if not normalized or not isinstance(secret, str) or not secret:
        return None
    message = "browser-v2:" + normalized
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def get_browser_identity(key: str = "otg_visitor_identity_v2") -> dict[str, Any] | None:
    """Return the component response, or None during its first render."""
    value = _COMPONENT(default=None, key=key)
    return value if isinstance(value, dict) else None
