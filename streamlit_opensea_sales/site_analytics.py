"""First-party visitor analytics collector for OTG OpenSea Sales.

This module must never render public UI and must never let analytics failures
escape into the Streamlit app.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import logging
import os
import re
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

import psycopg2
from psycopg2 import Error as PsycopgError
import streamlit as st
from logging_compat import get_module_logger


SESSION_ID_KEY = "site_analytics_session_id"
ATTEMPTED_KEY = "site_analytics_session_attempted"
RECORDED_KEY = "site_analytics_session_recorded"
FAILED_KEY = "site_analytics_session_failed"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
LOG_PATH = PROJECT_ROOT / "logs" / "site_analytics.log"

VALID_MODES = {"item", "market", "top_items"}
ENABLED_VALUES = {"1", "true", "yes", "on"}
CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
WHITESPACE_RE = re.compile(r"\s+")
ITEM_KEY_RE = re.compile(r"^[A-Za-z0-9 _.,:'()/\-]+$")

BOT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("facebookexternalhit", "ua:social_preview"),
    ("twitterbot", "ua:social_preview"),
    ("discordbot", "ua:social_preview"),
    ("telegrambot", "ua:social_preview"),
    ("whatsapp", "ua:social_preview"),
    ("headlesschrome", "ua:headless"),
    ("uptimerobot", "ua:monitor"),
    ("pingdom", "ua:monitor"),
    ("statuscake", "ua:monitor"),
    ("curl/", "ua:automation"),
    ("python-requests", "ua:automation"),
    ("playwright", "ua:automation"),
    ("selenium", "ua:automation"),
    ("codex", "ua:automation"),
    ("copilot", "ua:automation"),
    ("crawler", "ua:crawler"),
    ("spider", "ua:crawler"),
    ("slurp", "ua:crawler"),
    ("preview", "ua:social_preview"),
    ("bot", "ua:bot"),
)

DB_COLUMNS = (
    "session_id",
    "visitor_hash",
    "started_at_utc",
    "last_seen_at_utc",
    "mode",
    "item_key",
    "path",
    "referrer_host",
    "traffic_source",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "device_type",
    "browser_family",
    "locale",
    "timezone",
    "is_bot",
    "bot_reason",
    "is_internal",
    "internal_reason",
)

INSERT_SQL = """
insert into public.site_visit_sessions (
    session_id,
    visitor_hash,
    started_at_utc,
    last_seen_at_utc,
    mode,
    item_key,
    path,
    referrer_host,
    traffic_source,
    utm_source,
    utm_medium,
    utm_campaign,
    utm_content,
    utm_term,
    device_type,
    browser_family,
    locale,
    timezone,
    is_bot,
    bot_reason,
    is_internal,
    internal_reason
)
values (
    %(session_id)s,
    %(visitor_hash)s,
    %(started_at_utc)s,
    %(last_seen_at_utc)s,
    %(mode)s,
    %(item_key)s,
    %(path)s,
    %(referrer_host)s,
    %(traffic_source)s,
    %(utm_source)s,
    %(utm_medium)s,
    %(utm_campaign)s,
    %(utm_content)s,
    %(utm_term)s,
    %(device_type)s,
    %(browser_family)s,
    %(locale)s,
    %(timezone)s,
    %(is_bot)s,
    %(bot_reason)s,
    %(is_internal)s,
    %(internal_reason)s
)
on conflict (session_id) do nothing
returning id;
"""


def _load_env_file() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ENV_PATH)
        return
    except Exception:
        pass

    try:
        with ENV_PATH.open("r", encoding="utf-8") as env_file:
            for line in env_file:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    except OSError:
        return


_load_env_file()


def _get_logger() -> logging.Logger:
    return get_module_logger("site_analytics", module_tag="site_analytics", level=logging.INFO)


LOGGER = _get_logger()


def record_current_session_once(mode: str, item_key: str | None = None) -> None:
    """Record one analytics row for the current Streamlit session."""
    if not _analytics_enabled():
        _log_status("disabled", session_id=None, duration_ms=0, mode=mode)
        return

    try:
        session_state = st.session_state
        if session_state.get(RECORDED_KEY) is True:
            return
        if session_state.get(ATTEMPTED_KEY) is True:
            return

        analytics_session_id = session_state.get(SESSION_ID_KEY)
        if not analytics_session_id:
            analytics_session_id = str(uuid.uuid4())
            session_state[SESSION_ID_KEY] = analytics_session_id

        session_state[ATTEMPTED_KEY] = True
        started = time.monotonic()
        secret = os.getenv("OTG_SITE_ANALYTICS_HMAC_SECRET", "")
        if not secret:
            session_state[FAILED_KEY] = True
            _log_status(
                "missing_secret",
                session_id=analytics_session_id,
                duration_ms=_elapsed_ms(started),
                mode=mode,
                reason="missing_secret",
            )
            return

        record = build_session_record(
            session_id=analytics_session_id,
            mode=mode,
            item_key=item_key,
            context=getattr(st, "context", None),
            query_params=getattr(st, "query_params", {}),
            secret=secret,
        )
        result = insert_session(record)
        session_state[RECORDED_KEY] = True
        session_state[FAILED_KEY] = False
        _log_status(
            "insert_ok" if result == "inserted" else "insert_duplicate",
            session_id=analytics_session_id,
            duration_ms=_elapsed_ms(started),
            mode=record["mode"],
            is_bot=bool(record["is_bot"]),
            is_internal=bool(record["is_internal"]),
        )
    except (PsycopgError, OSError, ValueError, TypeError, Exception) as exc:
        try:
            st.session_state[FAILED_KEY] = True
        except Exception:
            pass
        sanitized_reason = _sanitize_exception(exc)
        status = "missing_db_config" if sanitized_reason.startswith("missing_db_config") else "insert_failed"
        _log_status(
            status,
            session_id=_safe_session_id(),
            duration_ms=0,
            mode=mode,
            exc=exc,
            reason=sanitized_reason,
        )


def build_session_record(
    session_id: str,
    mode: str,
    item_key: str | None,
    context: Any,
    query_params: Mapping[str, Any],
    secret: str,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Build a privacy-safe session record from Streamlit context."""
    headers = _safe_headers(context)
    now = now_utc or datetime.now(timezone.utc)
    normalized_mode = mode if mode in VALID_MODES else "item"
    raw_user_agent = _header_get(headers, "User-Agent")
    user_agent = normalize_user_agent(raw_user_agent)
    client_ip = extract_client_ip(headers)
    normalized_ip = client_ip if client_ip else "ip:unknown"
    visitor_hash = calculate_visitor_hash(normalized_ip, user_agent, secret)
    is_bot, bot_reason = classify_bot(user_agent)
    is_internal, internal_reason = classify_internal(
        visitor_hash=visitor_hash,
        normalized_user_agent=user_agent,
        client_ip_available=client_ip is not None,
    )
    referrer_host, traffic_source = normalize_referrer(_header_get(headers, "Referer"))

    raw_item_key = item_key if normalized_mode == "item" else None
    if raw_item_key is None and normalized_mode == "item":
        raw_item_key = _query_get(query_params, "item")

    return {
        "session_id": session_id,
        "visitor_hash": visitor_hash,
        "started_at_utc": now,
        "last_seen_at_utc": now,
        "mode": normalized_mode,
        "item_key": sanitize_item_key(raw_item_key) if normalized_mode == "item" else None,
        "path": _extract_path(_safe_context_value(context, "url")),
        "referrer_host": referrer_host,
        "traffic_source": traffic_source,
        "utm_source": normalize_utm(_query_get(query_params, "utm_source"), True, 100),
        "utm_medium": normalize_utm(_query_get(query_params, "utm_medium"), True, 100),
        "utm_campaign": normalize_utm(_query_get(query_params, "utm_campaign"), False, 150),
        "utm_content": normalize_utm(_query_get(query_params, "utm_content"), False, 150),
        "utm_term": normalize_utm(_query_get(query_params, "utm_term"), False, 150),
        "device_type": classify_device(user_agent),
        "browser_family": classify_browser(user_agent, is_bot),
        "locale": _truncate(_clean_text(_safe_context_value(context, "locale")), 35),
        "timezone": _truncate(_clean_text(_safe_context_value(context, "timezone")), 64),
        "is_bot": is_bot,
        "bot_reason": bot_reason,
        "is_internal": is_internal,
        "internal_reason": internal_reason,
    }


def extract_client_ip(headers: Any) -> str | None:
    """Extract canonical client IP from Caddy-produced X-Forwarded-For."""
    values: list[str] = []
    get_all = getattr(headers, "get_all", None)
    if callable(get_all):
        try:
            values.extend(str(value) for value in get_all("X-Forwarded-For"))
        except Exception:
            values = []
    else:
        value = _header_get(headers, "X-Forwarded-For")
        if value:
            values.append(value)

    tokens = ",".join(values).split(",")
    valid: list[str] = []
    for token in tokens:
        candidate = token.strip()
        if not candidate or _looks_like_ip_with_port(candidate):
            continue
        try:
            parsed = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if parsed.is_loopback or str(parsed) in {"127.0.0.1", "::1"}:
            continue
        valid.append(str(parsed))
    return valid[-1] if valid else None


def normalize_user_agent(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return "ua:unknown"
    return text[:512]


def normalize_referrer(value: Any) -> tuple[str | None, str]:
    text = _clean_text(value)
    if not text:
        return None, "direct"

    try:
        parsed = urlparse(text)
        host = parsed.hostname
    except Exception:
        host = None
    if not host:
        return None, "direct"

    host = host.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    host = host[:255]
    return host, _traffic_source_for_host(host)


def normalize_utm(value: Any, lowercase: bool, max_len: int) -> str | None:
    text = _clean_text(value, normalize_unicode=True)
    if lowercase:
        text = text.lower()
    return _truncate(text, max_len)


def sanitize_item_key(value: Any) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    text = text[:180]
    if not ITEM_KEY_RE.fullmatch(text):
        return None
    return text


def classify_device(user_agent: str) -> str:
    ua = user_agent.lower()
    if ua == "ua:unknown":
        return "unknown"
    if "ipad" in ua or "tablet" in ua or ("android" in ua and "mobile" not in ua):
        return "tablet"
    if (
        "mobile" in ua
        or "iphone" in ua
        or "ipod" in ua
        or ("android" in ua and "mobile" in ua)
        or "windows phone" in ua
    ):
        return "mobile"
    if any(token in ua for token in ("windows nt", "macintosh", "x11", "linux x86_64", "cros")):
        return "desktop"
    return "unknown"


def classify_browser(user_agent: str, is_bot: bool) -> str:
    ua = user_agent.lower()
    if is_bot:
        return "bot"
    if "headlesschrome" in ua:
        return "headless_chrome"
    if "edg/" in ua:
        return "edge"
    if "firefox/" in ua or "fxios/" in ua:
        return "firefox"
    if ("chrome/" in ua or "crios/" in ua) and "edg/" not in ua:
        return "chrome"
    if "safari/" in ua and not any(token in ua for token in ("chrome/", "crios/", "chromium/", "edg/")):
        return "safari"
    return "unknown"


def classify_bot(user_agent: str) -> tuple[bool, str | None]:
    ua = user_agent.lower()
    if ua == "ua:unknown":
        return True, "ua:missing"
    for pattern, reason in BOT_PATTERNS:
        if pattern in ua:
            return True, reason
    return False, None


def classify_internal(
    visitor_hash: str,
    normalized_user_agent: str,
    client_ip_available: bool,
) -> tuple[bool, str | None]:
    excluded_hashes = _env_list("OTG_SITE_ANALYTICS_EXCLUDED_VISITOR_HASHES")
    if visitor_hash in excluded_hashes:
        return True, "hash_match"

    ua = normalized_user_agent.lower()
    for pattern in _env_list("OTG_SITE_ANALYTICS_INTERNAL_USER_AGENT_PATTERNS"):
        if pattern and pattern in ua:
            return True, "ua_pattern"

    if not client_ip_available:
        return True, "local_or_unknown_ip"
    return False, None


def calculate_visitor_hash(normalized_ip: str, normalized_user_agent: str, secret: str) -> str:
    message = normalized_ip + "\n" + normalized_user_agent
    return hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def insert_session(record: Mapping[str, Any]) -> str:
    params = _db_params()
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**params, connect_timeout=1)
        cur = conn.cursor()
        cur.execute("set local statement_timeout = '750ms';")
        cur.execute(INSERT_SQL, {column: record[column] for column in DB_COLUMNS})
        row = cur.fetchone()
        conn.commit()
        return "inserted" if row else "duplicate"
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def _analytics_enabled() -> bool:
    return os.getenv("OTG_SITE_ANALYTICS_ENABLED", "").strip().lower() in ENABLED_VALUES


def _db_params() -> dict[str, Any]:
    required = {
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT"),
        "dbname": os.getenv("POSTGRES_DB"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError("missing_db_config:" + ",".join(missing))
    params: dict[str, Any] = dict(required)
    if params["port"] is not None:
        params["port"] = int(params["port"])
    return params


def _safe_headers(context: Any) -> Any:
    if context is None:
        return {}
    try:
        return getattr(context, "headers", {}) or {}
    except Exception:
        return {}


def _safe_context_value(context: Any, name: str) -> Any:
    if context is None:
        return None
    try:
        return getattr(context, name, None)
    except Exception:
        return None


def _query_get(query_params: Mapping[str, Any], key: str) -> Any:
    try:
        value = query_params.get(key)
    except Exception:
        return None
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def _header_get(headers: Any, key: str) -> str | None:
    try:
        value = headers.get(key)
    except Exception:
        try:
            value = headers[key]
        except Exception:
            return None
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    return str(value) if value is not None else None


def _clean_text(value: Any, normalize_unicode: bool = False) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    text = str(value)
    if normalize_unicode:
        text = unicodedata.normalize("NFKC", text)
    text = CONTROL_CHARS_RE.sub("", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


def _truncate(value: str, max_len: int) -> str | None:
    if not value:
        return None
    return value[:max_len]


def _extract_path(url: Any) -> str:
    text = _clean_text(url)
    if not text:
        return "/"
    try:
        path = urlparse(text).path or "/"
    except Exception:
        path = "/"
    return path[:255]


def _traffic_source_for_host(host: str) -> str:
    if not host:
        return "direct"
    if host == "otgos.run.place":
        return "self"
    if host in {"x.com", "twitter.com", "t.co"}:
        return "x"
    if host in {"youtube.com", "youtu.be"} or host.endswith(".youtube.com"):
        return "youtube"
    if host == "tiktok.com" or host.endswith(".tiktok.com"):
        return "tiktok"
    if host == "instagram.com" or host.endswith(".instagram.com"):
        return "instagram"
    if host in {"discord.com", "discord.gg"} or host.endswith(".discord.com"):
        return "discord"
    if host in {"telegram.org", "t.me"} or host.endswith(".telegram.org"):
        return "telegram"
    if host == "google" or host.startswith("google.") or ".google." in host:
        return "google"
    return "other"


def _looks_like_ip_with_port(value: str) -> bool:
    if value.count(":") == 1 and "." in value:
        return True
    if value.startswith("[") and "]:" in value:
        return True
    return False


def _env_list(key: str) -> set[str]:
    raw = os.getenv(key, "")
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _safe_session_id() -> str | None:
    try:
        value = st.session_state.get(SESSION_ID_KEY)
    except Exception:
        return None
    return str(value) if value else None


def _sanitize_exception(exc: BaseException) -> str:
    text = _clean_text(str(exc))
    if not text:
        return exc.__class__.__name__
    blocked = (
        os.getenv("POSTGRES_PASSWORD", ""),
        os.getenv("OTG_SITE_ANALYTICS_HMAC_SECRET", ""),
    )
    for secret in blocked:
        if secret:
            text = text.replace(secret, "<redacted>")
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<ip>", text)
    if "mozilla/" in text.lower():
        text = "<redacted_user_agent>"
    return text[:160]


def _log_status(
    status: str,
    session_id: str | None,
    duration_ms: int,
    mode: str,
    is_bot: bool | None = None,
    is_internal: bool | None = None,
    exc: BaseException | None = None,
    reason: str | None = None,
) -> None:
    prefix = session_id[:8] if session_id else ""
    fields = [
        f"status={status}",
        f"session_prefix={prefix}",
        f"duration_ms={duration_ms}",
        f"mode={mode if mode in VALID_MODES else 'item'}",
    ]
    if is_bot is not None:
        fields.append(f"is_bot={is_bot}")
    if is_internal is not None:
        fields.append(f"is_internal={is_internal}")
    if exc is not None:
        fields.append(f"exception_class={exc.__class__.__name__}")
    if reason:
        fields.append(f"reason={reason}")
    message = " ".join(fields)
    if status in {"insert_failed", "missing_secret", "missing_db_config"}:
        LOGGER.warning(message)
    else:
        LOGGER.info(message)
