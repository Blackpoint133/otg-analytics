"""Small fail-closed configuration helpers for analytics writes."""

from __future__ import annotations

import os


TRUE_VALUES = {"1", "true", "yes", "on"}


def strict_env_bool(name: str) -> bool:
    """Return true only for explicitly recognized true values."""
    return os.getenv(name, "").strip().lower() in TRUE_VALUES


def analytics_writes_enabled() -> bool:
    """Global defense-in-depth switch; disabled unless explicitly enabled."""
    return strict_env_bool("OTG_ANALYTICS_WRITES_ENABLED")
