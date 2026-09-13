import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "streamlit_opensea_sales"))

import feedback_notifications as notifications


def test_telegram_enable_gate(monkeypatch):
    monkeypatch.delenv("OTG_FEEDBACK_TELEGRAM_ENABLED", raising=False)
    assert notifications.telegram_notifications_enabled() is False
    for value in ("false", "0"):
        monkeypatch.setenv("OTG_FEEDBACK_TELEGRAM_ENABLED", value)
        assert notifications.telegram_notifications_enabled() is False
    for value in ("true", "yes", "on", "1"):
        monkeypatch.setenv("OTG_FEEDBACK_TELEGRAM_ENABLED", value)
        assert notifications.telegram_notifications_enabled() is True


def test_notification_text_mappings_and_safe_truncation():
    sid = uuid.UUID("12345678-abcd-0000-0000-000000000000")
    text = notifications.build_feedback_notification(submission_id=sid, feedback_type="data_issue", message="one\r\ntwo", source_mode="trader", source_item_key="Tacoma Pioneer")
    assert "TYPE: DATA ISSUE" in text and "SOURCE: TOP TRADERS" in text
    assert "ITEM: Tacoma Pioneer" in text and "SUBMISSION: 12345678" in text
    assert "one\ntwo" in text and "\r" not in text
    assert "ITEM: None" not in text
    for feedback_type, label in (("bug", "BUG"), ("suggestion", "SUGGESTION"), ("other", "OTHER"), ("bad", "OTHER")):
        assert f"TYPE: {label}" in notifications.build_feedback_notification(submission_id=sid, feedback_type=feedback_type, message="valid message", source_mode="unknown")
    for mode, label in (("item", "ITEM"), ("market", "MARKET"), ("top_items", "TOP ITEMS"), ("trader", "TOP TRADERS"), ("bad", "UNKNOWN")):
        assert f"SOURCE: {label}" in notifications.build_feedback_notification(submission_id=sid, feedback_type="bug", message="valid message", source_mode=mode)
    assert len(notifications.build_feedback_notification(submission_id=sid, feedback_type="bug", message="x" * 4000, source_mode="item")) <= 3500


class _Response:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return json.dumps(self.body).encode()


def test_http_contract_and_statuses(monkeypatch):
    monkeypatch.setenv("OTG_FEEDBACK_TELEGRAM_ENABLED", "true")
    monkeypatch.setenv("OTG_FEEDBACK_TELEGRAM_BOT_TOKEN", "TEST_BOT_TOKEN")
    monkeypatch.setenv("OTG_FEEDBACK_TELEGRAM_CHAT_ID", "123456789")
    calls = []
    monkeypatch.setattr(notifications.request, "urlopen", lambda req, timeout: (calls.append((req, timeout)) or _Response({"ok": True})))
    assert notifications.send_feedback_notification(submission_id=uuid.uuid4(), feedback_type="bug", message="valid message", source_mode="market") == "sent"
    req, timeout = calls[0]
    assert timeout == 2 and req.method == "POST" and "/botTEST_BOT_TOKEN/sendMessage" in req.full_url
    body = json.loads(req.data.decode())
    assert body["chat_id"] == "123456789" and "text" in body and body["disable_web_page_preview"] is True
    monkeypatch.setattr(notifications.request, "urlopen", lambda req, timeout: _Response({"ok": False}))
    assert notifications.send_feedback_notification(submission_id=uuid.uuid4(), feedback_type="bug", message="valid message", source_mode="market") == "failed"


def test_disabled_and_network_failure_do_not_call_or_raise(monkeypatch):
    monkeypatch.setenv("OTG_FEEDBACK_TELEGRAM_ENABLED", "false")
    called = []
    monkeypatch.setattr(notifications.request, "urlopen", lambda *args, **kwargs: called.append(True))
    assert notifications.send_feedback_notification(submission_id=uuid.uuid4(), feedback_type="bug", message="valid message", source_mode="item") == "disabled"
    assert not called
    monkeypatch.setenv("OTG_FEEDBACK_TELEGRAM_ENABLED", "true")
    monkeypatch.setenv("OTG_FEEDBACK_TELEGRAM_BOT_TOKEN", "TEST_BOT_TOKEN")
    monkeypatch.setenv("OTG_FEEDBACK_TELEGRAM_CHAT_ID", "123456789")
    def fail(*args, **kwargs): raise OSError("network")
    monkeypatch.setattr(notifications.request, "urlopen", fail)
    assert notifications.send_feedback_notification(submission_id=uuid.uuid4(), feedback_type="bug", message="valid message", source_mode="item") == "failed"


def test_feedback_notifies_only_new_database_inserts():
    source = (ROOT / "streamlit_opensea_sales" / "ui" / "feedback.py").read_text(encoding="utf-8")
    assert 'if result == "inserted":' in source
    assert "send_feedback_notification(" in source
    assert source.index('if result == "inserted":') < source.index("send_feedback_notification(")
    assert "feedback_store.py" not in source
