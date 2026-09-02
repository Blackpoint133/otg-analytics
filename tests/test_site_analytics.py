import io
import logging
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "streamlit_opensea_sales"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import site_analytics as analytics  # noqa: E402


class FakeHeaders:
    def __init__(self, values=None):
        self.values = values or {}

    def get_all(self, key):
        value = self.values.get(key, [])
        return value if isinstance(value, list) else [value]

    def get(self, key, default=None):
        value = self.values.get(key, default)
        if isinstance(value, list):
            return value[0] if value else default
        return value


class FakeContext:
    def __init__(self, headers=None, url="https://otgos.run.place/", locale="en-US", timezone_value="America/Los_Angeles"):
        self.headers = headers or FakeHeaders()
        self.url = url
        self.locale = locale
        self.timezone = timezone_value


class FakeCursor:
    def __init__(self, row=(1,), fail_on_execute=None):
        self.row = row
        self.fail_on_execute = fail_on_execute
        self.params = None
        self.closed = False

    def execute(self, sql, params=None):
        self.params = params
        if self.fail_on_execute and "insert into" in sql.lower():
            raise self.fail_on_execute

    def fetchone(self):
        return self.row

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_obj = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class SiteAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.env_patcher = patch.dict(
            os.environ,
            {
                "OTG_SITE_ANALYTICS_ENABLED": "true",
                "OTG_ANALYTICS_WRITES_ENABLED": "true",
                "OTG_SITE_ANALYTICS_HMAC_SECRET": "test-secret-value-that-is-long-enough",
                "OTG_SITE_ANALYTICS_EXCLUDED_VISITOR_HASHES": "",
                "OTG_SITE_ANALYTICS_INTERNAL_USER_AGENT_PATTERNS": "codex,copilot,playwright,selenium,headlesschrome",
                "POSTGRES_USER": "user",
                "POSTGRES_PASSWORD": "password",
                "POSTGRES_HOST": "localhost",
                "POSTGRES_PORT": "5432",
                "POSTGRES_DB": "server_otg",
            },
            clear=False,
        )
        self.env_patcher.start()
        self.original_logger = analytics.LOGGER
        self.test_log_stream = io.StringIO()
        self.test_logger = logging.getLogger("site_analytics_unit_test")
        self.test_logger.handlers = []
        self.test_logger.propagate = False
        self.test_logger.setLevel(logging.INFO)
        self.test_logger.addHandler(logging.StreamHandler(self.test_log_stream))
        analytics.LOGGER = self.test_logger
        analytics.st.session_state = {}
        analytics.st.context = FakeContext(
            headers=FakeHeaders(
                {
                    "X-Forwarded-For": ["198.51.100.10"],
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
                    "Referer": "https://x.com/path?private=yes",
                }
            )
        )
        analytics.st.query_params = {
            "item": "Ampu-Tee Epic",
            "utm_source": " Manual_Test ",
            "utm_medium": " QA ",
            "utm_campaign": "Launch Campaign",
        }

    def tearDown(self):
        analytics.LOGGER = self.original_logger
        self.env_patcher.stop()

    def build_record(self, **overrides):
        kwargs = {
            "session_id": "11111111-1111-4111-8111-111111111111",
            "mode": "item",
            "item_key": "Ampu-Tee Epic",
            "context": analytics.st.context,
            "query_params": analytics.st.query_params,
            "secret": os.environ["OTG_SITE_ANALYTICS_HMAC_SECRET"],
            "now_utc": datetime(2026, 8, 3, tzinfo=timezone.utc),
        }
        kwargs.update(overrides)
        return analytics.build_session_record(**kwargs)

    def test_one_new_session_performs_one_insert(self):
        calls = []

        def fake_insert(record):
            calls.append(record)
            return "inserted"

        with patch.object(analytics, "insert_session", side_effect=fake_insert):
            analytics.record_current_session_once("item", "Ampu-Tee Epic")

        self.assertEqual(len(calls), 1)
        self.assertTrue(analytics.st.session_state[analytics.RECORDED_KEY])

    def test_rerun_after_success_performs_no_second_insert(self):
        with patch.object(analytics, "insert_session", return_value="inserted") as insert:
            analytics.record_current_session_once("item", "Ampu-Tee Epic")
            analytics.record_current_session_once("item", "Ampu-Tee Epic")

        self.assertEqual(insert.call_count, 1)

    def test_attempted_failure_does_not_retry_on_rerun(self):
        with patch.object(analytics, "insert_session", side_effect=OSError("db down")) as insert:
            analytics.record_current_session_once("item", "Ampu-Tee Epic")
            analytics.record_current_session_once("item", "Ampu-Tee Epic")

        self.assertEqual(insert.call_count, 1)
        self.assertTrue(analytics.st.session_state[analytics.FAILED_KEY])

    def test_new_session_state_produces_new_uuid(self):
        with patch.object(analytics, "insert_session", return_value="inserted"):
            analytics.record_current_session_once("item", None)
            first = analytics.st.session_state[analytics.SESSION_ID_KEY]
            analytics.st.session_state = {}
            analytics.record_current_session_once("item", None)
            second = analytics.st.session_state[analytics.SESSION_ID_KEY]

        self.assertNotEqual(first, second)

    def test_duplicate_insert_is_treated_as_recorded(self):
        with patch.object(analytics, "insert_session", return_value="duplicate"):
            analytics.record_current_session_once("item", None)

        self.assertTrue(analytics.st.session_state[analytics.RECORDED_KEY])
        self.assertFalse(analytics.st.session_state[analytics.FAILED_KEY])

    def test_missing_hmac_secret_performs_no_insert(self):
        os.environ["OTG_SITE_ANALYTICS_HMAC_SECRET"] = ""
        with patch.object(analytics, "insert_session") as insert:
            analytics.record_current_session_once("item", None)

        insert.assert_not_called()
        self.assertTrue(analytics.st.session_state[analytics.FAILED_KEY])

    def test_global_write_guard_blocks_session_connection(self):
        os.environ["OTG_ANALYTICS_WRITES_ENABLED"] = "false"
        with patch.object(analytics, "insert_session") as insert:
            analytics.record_current_session_once("item", None)

        insert.assert_not_called()

    def test_global_write_guard_allows_existing_enabled_session_writer(self):
        os.environ["OTG_ANALYTICS_WRITES_ENABLED"] = "true"
        with patch.object(analytics, "insert_session", return_value="inserted") as insert:
            analytics.record_current_session_once("item", "Ampu-Tee Epic")

        insert.assert_called_once()

    def test_missing_ip_uses_unknown_identity(self):
        record = self.build_record(context=FakeContext(headers=FakeHeaders({"User-Agent": "Mozilla/5.0"})))
        expected = analytics.calculate_visitor_hash("ip:unknown", "Mozilla/5.0", os.environ["OTG_SITE_ANALYTICS_HMAC_SECRET"])
        self.assertEqual(record["visitor_hash"], expected)

    def test_v2_browser_identity_is_domain_separated_and_stable(self):
        browser_id = "22222222-2222-4222-8222-222222222222"
        first = analytics.browser_visitor_hash(browser_id, "test-secret-value-that-is-long-enough")
        second = analytics.browser_visitor_hash(browser_id, "test-secret-value-that-is-long-enough")
        legacy = analytics.calculate_visitor_hash(browser_id, "Mozilla/5.0", "test-secret-value-that-is-long-enough")
        self.assertEqual(first, second)
        self.assertNotEqual(first, legacy)
        self.assertRegex(first, r"^[0-9a-f]{64}$")

    def test_different_browser_ids_produce_different_v2_digests(self):
        secret = "test-secret-value-that-is-long-enough"
        first = analytics.browser_visitor_hash("11111111-1111-4111-8111-111111111111", secret)
        second = analytics.browser_visitor_hash("22222222-2222-4222-8222-222222222222", secret)
        self.assertNotEqual(first, second)

    def test_malformed_and_oversized_browser_ids_are_rejected(self):
        secret = "test-secret-value-that-is-long-enough"
        self.assertIsNone(analytics.browser_visitor_hash("not-a-uuid", secret))
        self.assertIsNone(analytics.browser_visitor_hash("x" * 10000, secret))

    def test_missing_browser_identity_is_legacy_only(self):
        record = self.build_record(browser_identity={"status": "unavailable"})
        self.assertEqual(record["identity_version"], 1)
        self.assertIsNone(record["browser_visitor_hash"])

    def test_valid_browser_identity_is_v2_and_raw_id_is_not_persisted(self):
        browser_id = "33333333-3333-4333-8333-333333333333"
        record = self.build_record(browser_identity={"status": "ok", "id": browser_id})
        self.assertEqual(record["identity_version"], 2)
        self.assertRegex(record["browser_visitor_hash"], r"^[0-9a-f]{64}$")
        self.assertNotIn(browser_id, " ".join(str(value) for value in record.values()))

    def test_missing_user_agent_uses_unknown(self):
        self.assertEqual(analytics.normalize_user_agent(None), "ua:unknown")
        is_bot, reason = analytics.classify_bot("ua:unknown")
        self.assertTrue(is_bot)
        self.assertEqual(reason, "ua:missing")

    def test_malformed_x_forwarded_for_is_ignored_safely(self):
        headers = FakeHeaders({"X-Forwarded-For": ["bad, 127.0.0.1, [::1]:1234"]})
        self.assertIsNone(analytics.extract_client_ip(headers))

    def test_right_most_valid_x_forwarded_for_token_is_selected(self):
        headers = FakeHeaders({"X-Forwarded-For": ["198.51.100.1, 203.0.113.9"]})
        self.assertEqual(analytics.extract_client_ip(headers), "203.0.113.9")

    def test_raw_ip_absent_from_database_record(self):
        record = self.build_record()
        joined = " ".join(str(value) for value in record.values())
        self.assertNotIn("198.51.100.10", joined)
        self.assertNotIn("X-Forwarded-For", joined)

    def test_bot_user_agent_is_classified(self):
        is_bot, reason = analytics.classify_bot("Googlebot crawler")
        self.assertTrue(is_bot)
        self.assertIn(reason, {"ua:bot", "ua:crawler"})

    def test_internal_hash_is_classified(self):
        os.environ["OTG_SITE_ANALYTICS_EXCLUDED_VISITOR_HASHES"] = "abc123"
        is_internal, reason = analytics.classify_internal("abc123", "Mozilla/5.0", True)
        self.assertTrue(is_internal)
        self.assertEqual(reason, "hash_match")

    def test_internal_user_agent_pattern_is_classified(self):
        is_internal, reason = analytics.classify_internal("hash", "Playwright Chrome", True)
        self.assertTrue(is_internal)
        self.assertEqual(reason, "ua_pattern")

    def test_utm_normalization_and_length_limits_work(self):
        self.assertEqual(analytics.normalize_utm("  QA TEST  ", True, 100), "qa test")
        self.assertEqual(len(analytics.normalize_utm("x" * 200, False, 150)), 150)
        self.assertIsNone(analytics.normalize_utm(" \x00 ", True, 100))

    def test_referrer_stores_hostname_only(self):
        host, source = analytics.normalize_referrer("https://www.youtube.com/watch?v=secret")
        self.assertEqual(host, "youtube.com")
        self.assertEqual(source, "youtube")

    def test_direct_traffic_classification_works(self):
        self.assertEqual(analytics.normalize_referrer(None), (None, "direct"))

    def test_device_classification_works(self):
        self.assertEqual(analytics.classify_device("Mozilla iPhone Mobile"), "mobile")
        self.assertEqual(analytics.classify_device("Mozilla iPad"), "tablet")
        self.assertEqual(analytics.classify_device("Mozilla Windows NT 10.0"), "desktop")

    def test_browser_classification_works(self):
        self.assertEqual(analytics.classify_browser("Mozilla Edg/120 Chrome/120", False), "edge")
        self.assertEqual(analytics.classify_browser("Mozilla Chrome/120 Safari/537", False), "chrome")
        self.assertEqual(analytics.classify_browser("Mozilla Safari/605", False), "safari")
        self.assertEqual(analytics.classify_browser("Mozilla Firefox/120", False), "firefox")

    def test_postgresql_connection_failure_is_swallowed(self):
        with patch.object(analytics, "insert_session", side_effect=OSError("connection failed")):
            analytics.record_current_session_once("item", None)

        self.assertTrue(analytics.st.session_state[analytics.FAILED_KEY])

    def test_statement_timeout_failure_is_swallowed(self):
        with patch.object(analytics, "insert_session", side_effect=TimeoutError("statement timeout")):
            analytics.record_current_session_once("item", None)

        self.assertTrue(analytics.st.session_state[analytics.FAILED_KEY])

    def test_logs_never_contain_raw_ip_full_ua_or_secret(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        analytics.LOGGER.addHandler(handler)
        try:
            secret = os.environ["OTG_SITE_ANALYTICS_HMAC_SECRET"]
            exc = ValueError("failed for 198.51.100.10 Mozilla/5.0 Secret " + secret)
            analytics._log_status(
                "insert_failed",
                session_id="11111111-1111-4111-8111-111111111111",
                duration_ms=1,
                mode="item",
                exc=exc,
                reason=analytics._sanitize_exception(exc),
            )
        finally:
            analytics.LOGGER.removeHandler(handler)

        logged = stream.getvalue()
        self.assertNotIn("198.51.100.10", logged)
        self.assertNotIn("Mozilla/5.0", logged)
        self.assertNotIn(os.environ["OTG_SITE_ANALYTICS_HMAC_SECRET"], logged)
        self.assertNotIn("11111111-1111-4111-8111-111111111111", logged)

    def test_mode_values_are_whitelisted(self):
        record = self.build_record(mode="bad")
        self.assertEqual(record["mode"], "item")

    def test_invalid_item_key_becomes_null(self):
        self.assertIsNone(analytics.sanitize_item_key("bad<>item"))

    def test_insert_session_interprets_inserted_and_duplicate(self):
        fake_insert_conn = FakeConnection(FakeCursor(row=(7,)))
        with patch.object(analytics.psycopg2, "connect", return_value=fake_insert_conn):
            self.assertEqual(analytics.insert_session(self.build_record()), "inserted")
        self.assertTrue(fake_insert_conn.committed)
        self.assertTrue(fake_insert_conn.closed)

        fake_duplicate_conn = FakeConnection(FakeCursor(row=None))
        with patch.object(analytics.psycopg2, "connect", return_value=fake_duplicate_conn):
            self.assertEqual(analytics.insert_session(self.build_record()), "duplicate")

    def test_raw_browser_id_is_not_passed_to_sql_parameters(self):
        browser_id = "33333333-3333-4333-8333-333333333333"
        record = self.build_record(browser_identity={"status": "ok", "id": browser_id})
        cursor = FakeCursor(row=(7,))
        connection = FakeConnection(cursor)
        with patch.object(analytics.psycopg2, "connect", return_value=connection):
            analytics.insert_session(record)
        self.assertNotIn(browser_id, " ".join(str(value) for value in cursor.params.values()))

    def test_insert_session_rolls_back_and_closes_on_error(self):
        fake_conn = FakeConnection(FakeCursor(fail_on_execute=RuntimeError("timeout")))
        with patch.object(analytics.psycopg2, "connect", return_value=fake_conn):
            with self.assertRaises(RuntimeError):
                analytics.insert_session(self.build_record())
        self.assertTrue(fake_conn.rolled_back)
        self.assertTrue(fake_conn.closed)


if __name__ == "__main__":
    unittest.main()
