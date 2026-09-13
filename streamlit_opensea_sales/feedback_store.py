"""Safe, opt-in PostgreSQL persistence for user feedback."""
import logging
import os
import uuid
from typing import Any, Mapping, Optional

import psycopg2

LOGGER = logging.getLogger("feedback")
ENABLED_VALUES = {"1", "true", "yes", "on"}
FEEDBACK_TYPES = {"bug", "suggestion", "data_issue", "other"}
SOURCE_MODES = {"item", "market", "top_items", "trader", "unknown"}


def feedback_writes_enabled() -> bool:
    return os.getenv("OTG_FEEDBACK_WRITES_ENABLED", "").strip().lower() in ENABLED_VALUES


def normalize_feedback_type(value: Any) -> str:
    value = str(value or "").strip().lower()
    return value if value in FEEDBACK_TYPES else "other"


def normalize_source_mode(value: Any) -> str:
    value = str(value or "").strip().lower()
    return value if value in SOURCE_MODES else "unknown"


def sanitize_source_item(value: Any) -> Optional[str]:
    if value is None:
        return None
    value = " ".join(str(value).split())
    return value[:180] or None


def insert_feedback(*, submission_id: uuid.UUID, feedback_type: str, message: str,
                    source_mode: str, source_item_key: Optional[str], source_context: Mapping[str, Any]) -> str:
    if not feedback_writes_enabled():
        return "disabled"
    message = str(message).strip()
    if not 10 <= len(message) <= 2000:
        raise ValueError("invalid_message_length")
    params = {key: os.getenv(key) for key in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB")}
    missing = [key for key, value in params.items() if not value]
    if missing:
        raise ValueError("missing_db_config")
    params["port"] = int(params.pop("POSTGRES_PORT"))
    params = {"user": params["POSTGRES_USER"], "password": params["POSTGRES_PASSWORD"], "host": params["POSTGRES_HOST"], "port": params["port"], "dbname": params["POSTGRES_DB"]}
    conn = cur = None
    try:
        conn = psycopg2.connect(**params, connect_timeout=1)
        cur = conn.cursor()
        cur.execute("SET LOCAL statement_timeout = '1500ms';")
        cur.execute("""INSERT INTO public.user_feedback
            (submission_id, feedback_type, message, source_mode, source_item_key, source_context)
            VALUES (%(submission_id)s, %(feedback_type)s, %(message)s, %(source_mode)s, %(source_item_key)s, %(source_context)s::jsonb)
            ON CONFLICT (submission_id) DO NOTHING""", {
                "submission_id": str(submission_id), "feedback_type": normalize_feedback_type(feedback_type),
                "message": message, "source_mode": normalize_source_mode(source_mode),
                "source_item_key": sanitize_source_item(source_item_key), "source_context": __import__("json").dumps(dict(source_context)),
            })
        inserted = cur.rowcount > 0
        conn.commit()
        LOGGER.info("feedback %s source_mode=%s feedback_type=%s", "inserted" if inserted else "duplicate", normalize_source_mode(source_mode), normalize_feedback_type(feedback_type))
        return "inserted" if inserted else "duplicate"
    except Exception:
        if conn is not None:
            conn.rollback()
        LOGGER.exception("feedback persistence failed source_mode=%s feedback_type=%s", normalize_source_mode(source_mode), normalize_feedback_type(feedback_type))
        raise
    finally:
        if cur is not None: cur.close()
        if conn is not None: conn.close()
