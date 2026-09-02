"""Best-effort append-only item activity events for the public Item flow."""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import psycopg2
from dotenv import load_dotenv
import streamlit as st

from logging_compat import get_module_logger
from site_analytics import sanitize_item_key
from visitor_identity import browser_visitor_hash


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
LOG_PATH = PROJECT_ROOT / "logs" / "site_analytics.log"
LOGGER = get_module_logger("site_item_events", log_file=LOG_PATH, module_tag="site_item_events")
EVENT_INITIALIZED_KEY = "site_item_event_initialized"
LAST_ITEM_KEY = "site_item_event_last_item"
SEQUENCE_KEY = "site_item_event_sequence"
VALID_EVENT_TYPES = {"initial_default", "initial_explicit", "item_select"}
ITEM_EVENT_INSERT_SQL = """INSERT INTO public.site_item_events
                (occurred_at_utc, parent_session_id, browser_visitor_hash,
                 identity_version, item_key, event_type, mode, sequence_no)
                VALUES (%(occurred_at_utc)s, %(parent_session_id)s, %(browser_visitor_hash)s,
                        %(identity_version)s, %(item_key)s, %(event_type)s, 'item', %(sequence_no)s)"""


def _sqlstate(exc: BaseException) -> str:
    value = getattr(exc, "pgcode", None)
    return value if isinstance(value, str) and re.fullmatch(r"[0-9A-Z]{5}", value) else "NONE"


def _log_event(marker: str, **fields: Any) -> None:
    payload = " ".join(f"{key}={value}" for key, value in fields.items())
    LOGGER.info(f"{marker}{(' ' + payload) if payload else ''}")


def _db_params() -> dict[str, Any]:
    load_dotenv(ENV_PATH)
    required = {
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT"),
        "dbname": os.getenv("POSTGRES_DB"),
    }
    if any(not value for value in required.values()):
        raise ValueError("Item event database configuration is unavailable")
    required["port"] = int(required["port"])
    return required


def _connect():
    return psycopg2.connect(**_db_params(), connect_timeout=1, options="-c statement_timeout=750")


def _parent_session_id() -> str | None:
    value = st.session_state.get("site_analytics_session_id")
    try:
        parsed = uuid.UUID(str(value)) if value else None
        return str(parsed) if parsed is not None else None
    except (ValueError, TypeError, AttributeError):
        return None


def _identity_fields(browser_identity: Mapping[str, Any] | None) -> tuple[str | None, int]:
    secret = os.getenv("OTG_SITE_ANALYTICS_HMAC_SECRET", "")
    if isinstance(browser_identity, Mapping) and browser_identity.get("status") == "ok":
        digest = browser_visitor_hash(browser_identity.get("id"), secret)
        if digest:
            return digest, 2
    return None, 1


def record_item_event(
    item_key: Any,
    event_type: str,
    browser_identity: Mapping[str, Any] | None,
    *,
    occurred_at_utc: datetime | None = None,
) -> bool:
    """Insert one event without ever breaking the public Item page."""
    normalized_item = sanitize_item_key(item_key)
    if not normalized_item:
        _log_event("ITEM_EVENT_REJECTED", reason="invalid_item_key")
        return False
    if event_type not in VALID_EVENT_TYPES:
        _log_event("ITEM_EVENT_REJECTED", reason="invalid_event_type")
        return False
    if st.session_state.get(EVENT_INITIALIZED_KEY) is not True:
        st.session_state[EVENT_INITIALIZED_KEY] = True
    sequence = int(st.session_state.get(SEQUENCE_KEY, 0)) + 1
    profile_key, identity_version = _identity_fields(browser_identity)
    _log_event(
        "ITEM_EVENT_ATTEMPT",
        event_type=event_type,
        identity_version=identity_version,
        parent_session_present=_parent_session_id() is not None,
        browser_identity_present=isinstance(browser_identity, Mapping) and browser_identity.get("status") == "ok",
        sequence_no=sequence,
    )
    conn = cur = None
    stage = "connect"
    try:
        conn = _connect()
        _log_event("ITEM_EVENT_DB_CONNECT_OK")
        cur = conn.cursor()
        stage = "insert"
        cur.execute(
            ITEM_EVENT_INSERT_SQL,
            {
                "occurred_at_utc": occurred_at_utc or datetime.now(timezone.utc),
                "parent_session_id": _parent_session_id(),
                "browser_visitor_hash": profile_key,
                "identity_version": identity_version,
                "item_key": normalized_item,
                "event_type": event_type,
                "sequence_no": sequence,
            },
        )
        _log_event("ITEM_EVENT_INSERT_OK")
        stage = "commit"
        conn.commit()
        _log_event("ITEM_EVENT_COMMIT_OK")
        st.session_state[SEQUENCE_KEY] = sequence
        st.session_state[LAST_ITEM_KEY] = normalized_item
        return True
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        _log_event(
            "ITEM_EVENT_WRITE_FAILED",
            stage=stage,
            exception_class=exc.__class__.__name__,
            sqlstate=_sqlstate(exc),
        )
        return False
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def record_initial_item_context(item_key: Any, event_type: str, browser_identity: Mapping[str, Any] | None) -> bool:
    """Record the initial context exactly once per Streamlit session."""
    if st.session_state.get(EVENT_INITIALIZED_KEY) is True:
        return False
    if event_type not in {"initial_default", "initial_explicit"}:
        return False
    return record_item_event(item_key, event_type, browser_identity)


def record_explicit_item_selection(item_key: Any, browser_identity: Mapping[str, Any] | None) -> bool:
    """Record a changed user selection, suppressing unrelated reruns."""
    normalized_item = sanitize_item_key(item_key)
    if not normalized_item or normalized_item == st.session_state.get(LAST_ITEM_KEY):
        return False
    return record_item_event(normalized_item, "item_select", browser_identity)
