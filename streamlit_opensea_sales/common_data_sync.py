"""Pure helpers for bounded item-level common_data reconciliation."""

from __future__ import annotations

import unicodedata
from typing import Any, Iterable


MAX_METADATA_FETCHES_PER_RUN = 100


def normalize_item_name(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).strip().split())


def normalization_collisions(names: Iterable[str]) -> dict[str, list[str]]:
    grouped: dict[str, set[str]] = {}
    for name in names:
        grouped.setdefault(normalize_item_name(name), set()).add(str(name))
    return {key: sorted(values) for key, values in grouped.items() if len(values) > 1}


def merge_nonblank_metadata(existing: dict[str, Any] | None, incoming: dict[str, Any]) -> dict[str, Any]:
    result = dict(existing or {})
    for field in ("image", "class", "type"):
        value = incoming.get(field)
        if value is not None and str(value).strip():
            result[field] = str(value).strip()
    result["name"] = incoming.get("name", result.get("name", ""))
    return result


def select_reconciliation_targets(
    current_names: Iterable[str],
    existing_names: Iterable[str],
    state: dict[str, dict[str, Any]] | None = None,
    limit: int = MAX_METADATA_FETCHES_PER_RUN,
) -> list[str]:
    current = sorted({normalize_item_name(name) for name in current_names if normalize_item_name(name)})
    existing = {normalize_item_name(name) for name in existing_names}
    state = state or {}
    missing = [name for name in current if name not in existing]
    known = [name for name in current if name in existing]
    known.sort(key=lambda name: str(state.get(name, {}).get("last_success_at", "")))
    return (missing + known)[: max(0, int(limit))]

