"""Non-blocking Telegram notifications for persisted feedback."""
import json
import logging
import os
import socket
import uuid
from urllib import request
from urllib.error import HTTPError, URLError

LOGGER = logging.getLogger("feedback.telegram")
ENABLED_VALUES = {"1", "true", "yes", "on"}


def telegram_notifications_enabled() -> bool:
    return os.getenv("OTG_FEEDBACK_TELEGRAM_ENABLED", "").strip().lower() in ENABLED_VALUES


def _display_type(value) -> str:
    return {"bug": "BUG", "suggestion": "SUGGESTION", "data_issue": "DATA ISSUE", "other": "OTHER"}.get(str(value).strip().lower(), "OTHER")


def _display_source(value) -> str:
    return {"item": "ITEM", "market": "MARKET", "top_items": "TOP ITEMS", "trader": "TOP TRADERS", "unknown": "UNKNOWN"}.get(str(value).strip().lower(), "UNKNOWN")


def _clean_message(message) -> str:
    return str(message or "").replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "").strip()


def build_feedback_notification(*, submission_id, feedback_type, message, source_mode, source_item_key=None) -> str:
    emoji = {"bug": "🐞", "suggestion": "💡", "data_issue": "📊", "other": "💬"}.get(str(feedback_type).strip().lower(), "💬")
    lines = [f"{emoji} NEW OTG ANALYTICS FEEDBACK", "", f"TYPE: {_display_type(feedback_type)}", f"SOURCE: {_display_source(source_mode)}"]
    if source_item_key:
        lines.append(f"ITEM: {str(source_item_key).strip()}")
    lines.extend(["", "MESSAGE:", _clean_message(message), "", f"SUBMISSION: {str(submission_id).replace('-', '')[:8]}"])
    text = "\n".join(lines)
    return text if len(text) <= 3500 else text[:3497].rstrip() + "..."


def _log_failure(reason: str, feedback_type, source_mode) -> None:
    LOGGER.warning("telegram feedback notification failed reason=%s source_mode=%s feedback_type=%s", reason, _display_source(source_mode).lower(), _display_type(feedback_type).lower())


def send_feedback_notification(*, submission_id: uuid.UUID, feedback_type, message, source_mode, source_item_key=None) -> str:
    if not telegram_notifications_enabled():
        return "disabled"
    token = os.getenv("OTG_FEEDBACK_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("OTG_FEEDBACK_TELEGRAM_CHAT_ID", "").strip()
    if not token:
        _log_failure("telegram_missing_bot_token", feedback_type, source_mode)
        return "failed"
    if not chat_id:
        _log_failure("telegram_missing_chat_id", feedback_type, source_mode)
        return "failed"
    payload = json.dumps({"chat_id": chat_id, "text": build_feedback_notification(submission_id=submission_id, feedback_type=feedback_type, message=message, source_mode=source_mode, source_item_key=source_item_key), "disable_web_page_preview": True}).encode("utf-8")
    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    req = request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=2) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("ok") is True:
            LOGGER.info("telegram feedback notification sent source_mode=%s feedback_type=%s", _display_source(source_mode).lower(), _display_type(feedback_type).lower())
            return "sent"
        _log_failure("telegram_api_rejected", feedback_type, source_mode)
    except HTTPError:
        _log_failure("telegram_http_error", feedback_type, source_mode)
    except (socket.timeout, TimeoutError):
        _log_failure("telegram_timeout", feedback_type, source_mode)
    except URLError:
        _log_failure("telegram_url_error", feedback_type, source_mode)
    except (ValueError, TypeError, AttributeError):
        _log_failure("telegram_invalid_response", feedback_type, source_mode)
    except Exception:
        _log_failure("telegram_unknown_error", feedback_type, source_mode)
    return "failed"
