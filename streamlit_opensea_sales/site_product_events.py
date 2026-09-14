"""Best-effort, privacy-safe categorical product usage events."""

from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
import streamlit as st
from dotenv import load_dotenv

from analytics_config import analytics_writes_enabled, strict_env_bool
from site_analytics import RECORDED_KEY, SESSION_ID_KEY

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
LOGGER = logging.getLogger("site_product_events")
PRODUCT_SEQUENCE_KEY = "site_product_event_sequence"
PRODUCT_LAST_SURFACE_KEY = "site_product_event_last_surface"
PRODUCT_CONTROL_STATES_KEY = "site_product_event_control_states"
VALID_SURFACES = {"item", "market", "top_items", "trader"}
VALID_EVENT_TYPES = {"surface_open", "filter_apply", "filter_clear", "sort_change", "period_change", "view_change", "toggle_change"}

_SHAPES = {
    ("item", "filter_apply", "wallet_filter"): {None},
    ("item", "filter_clear", "wallet_filter"): {None},
    ("top_items", "filter_apply", "item_class_filter"): {None},
    ("top_items", "filter_clear", "item_class_filter"): {None},
    ("trader", "filter_apply", "trader_filter"): {None},
    ("trader", "filter_clear", "trader_filter"): {None},
    ("top_items", "sort_change", "sort"): {"market_strength", "volume", "liquidity", "total_supply"},
    ("trader", "sort_change", "sort"): {"earned", "invested", "sold", "trades"},
    ("market", "period_change", "period"): {"all", "12m", "6m", "3m"},
    ("top_items", "period_change", "period"): {"all", "30d", "7d", "1d"},
    ("item", "view_change", "view"): {"chart", "table"},
    ("item", "toggle_change", "usd_price"): {"on", "off"},
    ("item", "toggle_change", "trend_line"): {"on", "off"},
    ("market", "toggle_change", "usd_price"): {"on", "off"},
    ("market", "toggle_change", "token_price"): {"on", "off"},
    ("market", "toggle_change", "unique_wallets"): {"on", "off"},
    ("top_items", "toggle_change", "usd_price"): {"on", "off"},
}
_SQL = """INSERT INTO public.site_product_events
 (occurred_at_utc, parent_session_id, surface, event_type, control_key, value_key, sequence_no)
 VALUES (%(occurred_at_utc)s, %(parent_session_id)s, %(surface)s, %(event_type)s, %(control_key)s, %(value_key)s, %(sequence_no)s)
 ON CONFLICT (parent_session_id, sequence_no) DO NOTHING
 RETURNING event_id"""


def _log(marker: str, **fields: Any) -> None:
    LOGGER.info("%s%s", marker, "".join(f" {k}={v}" for k, v in fields.items()))


def _sqlstate(exc: BaseException) -> str:
    value = getattr(exc, "pgcode", None)
    return value if isinstance(value, str) and re.fullmatch(r"[0-9A-Z]{5}", value) else "NONE"


def _normalize(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


def _safe_product_sequence() -> int:
    """Read a non-negative sequence without trusting malformed session state."""
    try:
        value = st.session_state.get(PRODUCT_SEQUENCE_KEY, 0)
        parsed = int(value)
        return parsed if parsed >= 0 else 0
    except Exception:
        return 0


def _safe_control_states() -> dict[str, tuple[str, str | None]]:
    """Copy only structurally valid categorical control states."""
    try:
        raw = st.session_state.get(PRODUCT_CONTROL_STATES_KEY, {})
        if not isinstance(raw, dict):
            return {}
        result: dict[str, tuple[str, str | None]] = {}
        for key, value in raw.items():
            if not isinstance(key, str) or not isinstance(value, (tuple, list)) or len(value) != 2:
                continue
            event_type, value_key = value
            if not isinstance(event_type, str) or event_type not in VALID_EVENT_TYPES:
                continue
            if value_key is not None and not isinstance(value_key, str):
                continue
            result[key] = (event_type, value_key)
        return result
    except (AttributeError, TypeError, ValueError):
        return {}


def _shape(surface: Any, event_type: Any, control_key: Any, value_key: Any) -> tuple[str, str, str | None, str | None] | None:
    s, e, c, v = _normalize(surface), _normalize(event_type), _normalize(control_key), _normalize(value_key)
    if s not in VALID_SURFACES:
        return None
    if e not in VALID_EVENT_TYPES:
        return None
    if e == "surface_open":
        return (s, e, None, None) if c is None and v is None else None
    allowed = _SHAPES.get((s, e, c))
    if allowed is None or v not in allowed:
        return None
    return s, e, c, v


def _db_params() -> dict[str, Any]:
    load_dotenv(ENV_PATH)
    values = {k: os.getenv(k) for k in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB")}
    if any(not v for v in values.values()):
        raise ValueError("Product event database configuration is unavailable")
    values["port"] = int(values["POSTGRES_PORT"])
    values.pop("POSTGRES_PORT")
    return {"user": values["POSTGRES_USER"], "password": values["POSTGRES_PASSWORD"], "host": values["POSTGRES_HOST"], "port": values["port"], "dbname": values["POSTGRES_DB"]}


def _connect():
    return psycopg2.connect(**_db_params(), connect_timeout=1, options="-c statement_timeout=750")


def _parent_session_id() -> str | None:
    if st.session_state.get(RECORDED_KEY) is not True:
        return None
    value = st.session_state.get(SESSION_ID_KEY)
    try:
        return str(uuid.UUID(str(value))) if value else None
    except (ValueError, TypeError, AttributeError):
        return None


def _advance(sequence: int, surface: str, event_type: str, control_key: str | None, value_key: str | None) -> None:
    st.session_state[PRODUCT_SEQUENCE_KEY] = sequence
    if event_type == "surface_open":
        st.session_state[PRODUCT_LAST_SURFACE_KEY] = surface
    else:
        states = _safe_control_states()
        states[f"{surface}:{control_key}"] = (event_type, value_key)
        st.session_state[PRODUCT_CONTROL_STATES_KEY] = states


def record_product_event(surface: str, event_type: str, *, control_key: str | None = None, value_key: str | None = None, occurred_at_utc: datetime | None = None) -> bool:
    normalized = _shape(surface, event_type, control_key, value_key)
    if normalized is None:
        _log("PRODUCT_EVENT_REJECTED", reason="invalid_event_shape")
        return False
    s, e, c, v = normalized
    if not analytics_writes_enabled() or not strict_env_bool("OTG_PRODUCT_EVENTS_ENABLED"):
        _log("PRODUCT_EVENT_WRITE_DISABLED")
        return False
    parent = _parent_session_id()
    if parent is None:
        _log("PRODUCT_EVENT_REJECTED", reason="missing_parent_session")
        return False
    if e == "surface_open" and st.session_state.get(PRODUCT_LAST_SURFACE_KEY) == s:
        return False
    if e != "surface_open" and _safe_control_states().get(f"{s}:{c}") == (e, v):
        return False
    sequence = _safe_product_sequence() + 1
    conn = cur = None
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute(_SQL, {"occurred_at_utc": occurred_at_utc or datetime.now(timezone.utc), "parent_session_id": parent, "surface": s, "event_type": e, "control_key": c, "value_key": v, "sequence_no": sequence})
        cur.fetchone()  # None is the expected duplicate outcome.
        conn.commit()
        _advance(sequence, s, e, c, v)
        return True
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        _log("PRODUCT_EVENT_WRITE_FAILED", surface=s, event_type=e, control_key=c, value_key=v, sequence=sequence, stage="db", exception_class=exc.__class__.__name__, sqlstate=_sqlstate(exc))
        return False
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
