"""Read-only aggregate queries for the internal visitor dashboard."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd
import psycopg2
from dotenv import load_dotenv


MIGRATION_BOUNDARY = datetime(2026, 8, 25, 8, 38, 50, 932403, tzinfo=timezone.utc)
DISPLAY_TIMEZONE = "America/Los_Angeles"
RANGES = {"24H": timedelta(hours=24), "7D": timedelta(days=7), "30D": timedelta(days=30), "ALL": None}
BUCKETS = {"24H": "hour", "7D": "day", "30D": "day", "ALL": "day"}


def period_bounds(range_key: str, now: datetime | None = None) -> tuple[datetime | None, datetime]:
    """Return UTC-aware half-open period bounds for a whitelisted range."""
    if range_key not in RANGES:
        raise ValueError("Unsupported dashboard range")
    end = now or datetime.now(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    start = None if RANGES[range_key] is None else end - RANGES[range_key]
    return start, end


def _db_params() -> dict[str, Any]:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path)
    required = {"user": os.getenv("POSTGRES_USER"), "password": os.getenv("POSTGRES_PASSWORD"), "host": os.getenv("POSTGRES_HOST"), "port": os.getenv("POSTGRES_PORT"), "dbname": os.getenv("POSTGRES_DB")}
    if any(not value for value in required.values()):
        raise ValueError("Visitor analytics database configuration is unavailable")
    required["port"] = int(required["port"])
    return required


def _connect():
    return psycopg2.connect(
        **_db_params(),
        connect_timeout=3,
        options="-c default_transaction_read_only=on -c statement_timeout=4000",
    )


def _period_clause(start: datetime | None, end: datetime) -> tuple[str, dict[str, datetime]]:
    if start is None:
        return "started_at_utc < %(period_end)s", {"period_end": end}
    return "started_at_utc >= %(period_start)s AND started_at_utc < %(period_end)s", {"period_start": start, "period_end": end}


def _event_period_clause(start: datetime | None, end: datetime) -> tuple[str, dict[str, datetime]]:
    """Return a half-open period predicate for item-event timestamps."""
    if start is None:
        return "e.occurred_at_utc < %(period_end)s", {"period_end": end}
    return "e.occurred_at_utc >= %(period_start)s AND e.occurred_at_utc < %(period_end)s", {
        "period_start": start,
        "period_end": end,
    }


def _fetch_dataframe(cur, sql: str, params: dict[str, Any]) -> pd.DataFrame:
    cur.execute(sql, params)
    rows = cur.fetchall()
    columns = [description[0] for description in cur.description]
    return pd.DataFrame(rows, columns=columns)


def classify_all_profiles(session_counts: Mapping[Any, int]) -> dict[str, int]:
    """Return mutually exclusive ALL-range V2 profile categories."""
    counts = [int(value) for value in session_counts.values()]
    return {
        "stable_visitors": len(counts),
        "new_visitors": sum(value == 1 for value in counts),
        "returning_visitors": sum(value >= 2 for value in counts),
    }


def count_bounded_returning_profiles(
    selected_profiles: Iterable[Any],
    first_seen: Mapping[Any, datetime],
    period_start: datetime,
) -> int:
    """Count selected V2 profiles first observed before a bounded period."""
    return sum(1 for profile in selected_profiles if first_seen[profile] < period_start)


def count_all_post_returning_profiles(
    attributed_profiles: Iterable[Any],
    session_counts: Mapping[Any, int],
) -> int:
    """Count attributed V2 profiles returning across all eligible V2 history."""
    return len({profile for profile in attributed_profiles if session_counts.get(profile, 0) >= 2})


def _item_interest_queries(cur, period: str, params: dict[str, Any], start: datetime | None) -> tuple[pd.DataFrame, int]:
    """Load recorded-item aggregates and missing-context count from one read-only cursor."""
    if start is None:
        profile_cte = """WITH profile_counts AS (
                SELECT browser_visitor_hash, count(*) AS profile_sessions
                FROM public.site_visit_sessions
                WHERE identity_version = 2 AND browser_visitor_hash IS NOT NULL
                  AND NOT is_bot AND NOT is_internal
                GROUP BY browser_visitor_hash
            )"""
        join_sql = "LEFT JOIN profile_counts pc USING (browser_visitor_hash)"
        returning_expr = "pc.profile_sessions >= 2"
    else:
        profile_cte = """WITH first_seen AS (
                SELECT browser_visitor_hash, min(started_at_utc) AS first_seen
                FROM public.site_visit_sessions
                WHERE identity_version = 2 AND browser_visitor_hash IS NOT NULL
                  AND NOT is_bot AND NOT is_internal
                GROUP BY browser_visitor_hash
            )"""
        join_sql = "LEFT JOIN first_seen fs USING (browser_visitor_hash)"
        returning_expr = "fs.first_seen < %(period_start)s"
    sql = f"""{profile_cte}
        SELECT trim(s.item_key) AS item_key,
               count(*)::bigint AS sessions,
               count(DISTINCT s.browser_visitor_hash) FILTER (
                   WHERE s.identity_version = 2 AND s.browser_visitor_hash IS NOT NULL
               )::bigint AS unique_v2_visitors,
               count(DISTINCT s.browser_visitor_hash) FILTER (
                   WHERE s.identity_version = 2 AND s.browser_visitor_hash IS NOT NULL
                     AND {returning_expr}
               )::bigint AS returning_v2_visitors,
               max(s.started_at_utc) AS latest_visit
        FROM public.site_visit_sessions s
        {join_sql}
        WHERE s.mode = 'item' AND NOT s.is_bot AND NOT s.is_internal
          AND NULLIF(trim(s.item_key), '') IS NOT NULL AND {period}
        GROUP BY trim(s.item_key)
        ORDER BY sessions DESC, item_key"""
    items = _fetch_dataframe(cur, sql, params)
    cur.execute(f"""SELECT count(*)::bigint
        FROM public.site_visit_sessions
        WHERE mode = 'item' AND NOT is_bot AND NOT is_internal
          AND NULLIF(trim(item_key), '') IS NULL AND {period}""", params)
    return items, int(cur.fetchone()[0] or 0)


def load_item_interest(range_key: str, now: datetime | None = None) -> tuple[pd.DataFrame, int]:
    """Return recorded-item aggregates and missing-context count using SELECT-only SQL."""
    start, end = period_bounds(range_key, now)
    period, params = _period_clause(start, end)
    conn = cur = None
    try:
        conn = _connect()
        cur = conn.cursor()
        return _item_interest_queries(cur, period, params, start)
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def load_visitor_summaries(range_key: str, now: datetime | None = None) -> pd.DataFrame:
    """Return transient server-side V2 profile keys and aggregate summary fields."""
    start, end = period_bounds(range_key, now)
    period, params = _period_clause(start, end)
    conn = cur = None
    try:
        conn = _connect()
        cur = conn.cursor()
        sql = f"""SELECT browser_visitor_hash AS profile_key,
                count(*)::bigint AS sessions,
                count(DISTINCT NULLIF(trim(item_key), ''))::bigint AS recorded_items,
                min(started_at_utc) AS first_seen,
                max(started_at_utc) AS latest_visit,
                (array_agg(CASE
                    WHEN nullif(trim(utm_source), '') IS NOT NULL
                      OR nullif(trim(utm_medium), '') IS NOT NULL
                      OR nullif(trim(utm_campaign), '') IS NOT NULL
                      OR nullif(trim(utm_content), '') IS NOT NULL
                      OR nullif(trim(utm_term), '') IS NOT NULL THEN 'UTM'
                    WHEN nullif(trim(referrer_host), '') IS NOT NULL THEN 'Referral'
                    WHEN traffic_source = 'direct' THEN 'Direct'
                    ELSE 'Other' END ORDER BY started_at_utc DESC))[1] AS last_acquisition
            FROM public.site_visit_sessions
            WHERE identity_version = 2 AND browser_visitor_hash IS NOT NULL
              AND NOT is_bot AND NOT is_internal AND {period}
            GROUP BY browser_visitor_hash
            ORDER BY latest_visit DESC, sessions DESC"""
        return _fetch_dataframe(cur, sql, params)
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def load_visitor_timeline(profile_key: str) -> pd.DataFrame:
    """Return one V2 profile's safe recorded-session timeline; key is never UI-facing."""
    conn = cur = None
    try:
        conn = _connect()
        cur = conn.cursor()
        sql = """SELECT started_at_utc, mode,
                NULLIF(trim(item_key), '') AS recorded_item,
                CASE
                    WHEN nullif(trim(utm_source), '') IS NOT NULL
                      OR nullif(trim(utm_medium), '') IS NOT NULL
                      OR nullif(trim(utm_campaign), '') IS NOT NULL
                      OR nullif(trim(utm_content), '') IS NOT NULL
                      OR nullif(trim(utm_term), '') IS NOT NULL THEN 'UTM'
                    WHEN nullif(trim(referrer_host), '') IS NOT NULL THEN 'Referral'
                    WHEN traffic_source = 'direct' THEN 'Direct'
                    ELSE 'Other' END AS acquisition,
                NULLIF(trim(utm_campaign), '') AS campaign,
                NULLIF(trim(utm_content), '') AS post
            FROM public.site_visit_sessions
            WHERE identity_version = 2 AND browser_visitor_hash = %(profile_key)s
              AND NOT is_bot AND NOT is_internal
            ORDER BY started_at_utc DESC"""
        return _fetch_dataframe(cur, sql, {"profile_key": profile_key})
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def _item_activity_queries(cur, period: str, params: dict[str, Any]) -> tuple[pd.DataFrame, int, datetime | None]:
    """Load explicit item activity aggregates and initial-default diagnostics."""
    sql = f"""SELECT trim(e.item_key) AS item_key,
            count(*)::bigint AS selections,
            count(DISTINCT e.parent_session_id)::bigint AS unique_sessions,
            count(DISTINCT e.browser_visitor_hash) FILTER (
                WHERE e.identity_version = 2 AND e.browser_visitor_hash IS NOT NULL
            )::bigint AS unique_v2_visitors,
            max(e.occurred_at_utc) AS latest_selection
        FROM public.site_item_events e
        JOIN public.site_visit_sessions s ON s.session_id = e.parent_session_id
        WHERE e.event_type IN ('initial_explicit', 'item_select')
          AND s.mode = 'item' AND NOT s.is_bot AND NOT s.is_internal
          AND {period}
        GROUP BY trim(e.item_key)
        ORDER BY selections DESC, item_key"""
    activity = _fetch_dataframe(cur, sql, params)
    cur.execute(f"""SELECT count(*)::bigint, min(e.occurred_at_utc)
        FROM public.site_item_events e
        JOIN public.site_visit_sessions s ON s.session_id = e.parent_session_id
        WHERE e.event_type = 'initial_default'
          AND s.mode = 'item' AND NOT s.is_bot AND NOT s.is_internal
          AND {period}""", params)
    count, first = cur.fetchone()
    return activity, int(count or 0), first


def load_item_activity(range_key: str, now: datetime | None = None) -> tuple[pd.DataFrame, int, datetime | None]:
    """Return explicit item-event aggregates using the same read-only connection model."""
    start, end = period_bounds(range_key, now)
    period, params = _event_period_clause(start, end)
    conn = cur = None
    try:
        conn = _connect()
        cur = conn.cursor()
        return _item_activity_queries(cur, period, params)
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def load_visitor_item_activity(profile_key: str) -> pd.DataFrame:
    """Return safe item-event fields for one transiently selected V2 profile."""
    conn = cur = None
    try:
        conn = _connect()
        cur = conn.cursor()
        sql = """SELECT e.occurred_at_utc, e.event_type, e.item_key,
                e.sequence_no,
                NULLIF(trim(s.utm_campaign), '') AS campaign,
                NULLIF(trim(s.utm_content), '') AS post
            FROM public.site_item_events e
            JOIN public.site_visit_sessions s ON s.session_id = e.parent_session_id
            WHERE e.identity_version = 2
              AND e.browser_visitor_hash = %(profile_key)s
              AND NOT s.is_bot AND NOT s.is_internal
            ORDER BY e.occurred_at_utc DESC, e.sequence_no DESC"""
        return _fetch_dataframe(cur, sql, {"profile_key": profile_key})
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def load_dashboard_data(range_key: str, now: datetime | None = None) -> dict[str, Any]:
    """Load only aggregate dashboard data; no row-level identifiers leave PostgreSQL."""
    start, end = period_bounds(range_key, now)
    period, params = _period_clause(start, end)
    params["migration_boundary"] = MIGRATION_BOUNDARY
    bucket = BUCKETS[range_key]
    conn = None
    cur = None
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute("SELECT now()")
        db_now = cur.fetchone()[0]
        params["db_now"] = db_now

        cur.execute(f"""SELECT count(*)::bigint AS sessions, max(started_at_utc) AS latest_visit
            FROM public.site_visit_sessions
            WHERE NOT is_bot AND NOT is_internal AND {period}""", params)
        kpis = cur.fetchone()

        trend = _fetch_dataframe(cur, f"""SELECT date_trunc('{bucket}', timezone(%(display_timezone)s, started_at_utc)) AS bucket,
                count(*)::bigint AS sessions,
                count(DISTINCT browser_visitor_hash) FILTER (WHERE identity_version = 2 AND browser_visitor_hash IS NOT NULL)::bigint AS stable_visitors
            FROM public.site_visit_sessions
            WHERE NOT is_bot AND NOT is_internal AND {period}
            GROUP BY 1 ORDER BY 1""", {**params, "display_timezone": DISPLAY_TIMEZONE})

        if start is None:
            first_seen_sql = """WITH profile_counts AS (
                    SELECT browser_visitor_hash, count(*) AS sessions
                    FROM public.site_visit_sessions
                    WHERE identity_version = 2 AND browser_visitor_hash IS NOT NULL
                      AND NOT is_bot AND NOT is_internal
                    GROUP BY browser_visitor_hash
                )
                SELECT count(*)::bigint AS stable_visitors,
                       count(*) FILTER (WHERE sessions = 1)::bigint AS new_visitors,
                       count(*) FILTER (WHERE sessions >= 2)::bigint AS returning_visitors
                FROM profile_counts"""
        else:
            first_seen_sql = f"""WITH first_seen AS (
                SELECT browser_visitor_hash, min(started_at_utc) AS first_seen
                FROM public.site_visit_sessions
                WHERE identity_version = 2 AND browser_visitor_hash IS NOT NULL
                  AND NOT is_bot AND NOT is_internal
                GROUP BY browser_visitor_hash
            ), selected AS (
                SELECT s.browser_visitor_hash, f.first_seen
                FROM public.site_visit_sessions s
                JOIN first_seen f USING (browser_visitor_hash)
                WHERE s.identity_version = 2 AND s.browser_visitor_hash IS NOT NULL
                  AND NOT s.is_bot AND NOT s.is_internal AND {period}
            )
            SELECT count(DISTINCT browser_visitor_hash)::bigint AS stable_visitors,
                   count(DISTINCT browser_visitor_hash) FILTER (WHERE first_seen >= %(period_start)s)::bigint AS new_visitors,
                   count(DISTINCT browser_visitor_hash) FILTER (WHERE first_seen < %(period_start)s)::bigint AS returning_visitors
            FROM selected"""
        v2 = _fetch_dataframe(cur, first_seen_sql, params)

        modes = _fetch_dataframe(cur, f"""SELECT mode, count(*)::bigint AS sessions
            FROM public.site_visit_sessions
            WHERE NOT is_bot AND NOT is_internal AND {period}
            GROUP BY mode ORDER BY mode""", params)

        acquisition = _fetch_dataframe(cur, f"""SELECT CASE
                WHEN nullif(trim(utm_source), '') IS NOT NULL
                  OR nullif(trim(utm_medium), '') IS NOT NULL
                  OR nullif(trim(utm_campaign), '') IS NOT NULL
                  OR nullif(trim(utm_content), '') IS NOT NULL
                  OR nullif(trim(utm_term), '') IS NOT NULL THEN 'UTM'
                WHEN nullif(trim(referrer_host), '') IS NOT NULL THEN 'Referral'
                WHEN traffic_source = 'direct' THEN 'Direct'
                ELSE 'Other' END AS source,
                count(*)::bigint AS sessions
            FROM public.site_visit_sessions
            WHERE NOT is_bot AND NOT is_internal AND {period}
            GROUP BY 1 ORDER BY sessions DESC, source""", params)

        if start is None:
            posts_sql = f"""WITH profile_counts AS (
                SELECT browser_visitor_hash, count(*) AS total_sessions
                FROM public.site_visit_sessions
                WHERE identity_version = 2 AND browser_visitor_hash IS NOT NULL
                  AND NOT is_bot AND NOT is_internal
                GROUP BY browser_visitor_hash
            )
            SELECT trim(s.utm_content) AS post, count(*)::bigint AS sessions,
                   count(DISTINCT s.browser_visitor_hash) FILTER (WHERE s.identity_version = 2 AND s.browser_visitor_hash IS NOT NULL)::bigint AS stable_visitors,
                   count(DISTINCT s.browser_visitor_hash) FILTER (WHERE s.identity_version = 2 AND s.browser_visitor_hash IS NOT NULL AND pc.total_sessions >= 2)::bigint AS returning,
                   count(*) FILTER (WHERE s.mode = 'item')::bigint AS item,
                   count(*) FILTER (WHERE s.mode = 'market')::bigint AS market,
                   count(*) FILTER (WHERE s.mode = 'top_items')::bigint AS top_items,
                   max(s.started_at_utc) AS latest_visit
            FROM public.site_visit_sessions s
            LEFT JOIN profile_counts pc USING (browser_visitor_hash)
            WHERE NOT s.is_bot AND NOT s.is_internal
              AND nullif(trim(s.utm_content), '') IS NOT NULL
            GROUP BY trim(s.utm_content) ORDER BY sessions DESC, post"""
            post_params = params
        else:
            posts_sql = f"""WITH first_seen AS (
                SELECT browser_visitor_hash, min(started_at_utc) AS first_seen
                FROM public.site_visit_sessions
                WHERE identity_version = 2 AND browser_visitor_hash IS NOT NULL
                  AND NOT is_bot AND NOT is_internal GROUP BY browser_visitor_hash
            )
            SELECT trim(s.utm_content) AS post, count(*)::bigint AS sessions,
                   count(DISTINCT s.browser_visitor_hash) FILTER (WHERE s.identity_version = 2 AND s.browser_visitor_hash IS NOT NULL)::bigint AS stable_visitors,
                   count(DISTINCT s.browser_visitor_hash) FILTER (WHERE s.identity_version = 2 AND s.browser_visitor_hash IS NOT NULL AND f.first_seen < %(period_start)s)::bigint AS returning,
                   count(*) FILTER (WHERE s.mode = 'item')::bigint AS item,
                   count(*) FILTER (WHERE s.mode = 'market')::bigint AS market,
                   count(*) FILTER (WHERE s.mode = 'top_items')::bigint AS top_items,
                   max(s.started_at_utc) AS latest_visit
            FROM public.site_visit_sessions s
            LEFT JOIN first_seen f USING (browser_visitor_hash)
            WHERE NOT s.is_bot AND NOT s.is_internal AND {period}
              AND nullif(trim(s.utm_content), '') IS NOT NULL
            GROUP BY trim(s.utm_content) ORDER BY sessions DESC, post"""
            post_params = {**params, "period_start": start}
        posts = _fetch_dataframe(cur, posts_sql, post_params)
        item_interest, item_missing = _item_interest_queries(cur, period, params, start)
        event_period, event_params = _event_period_clause(start, end)
        item_activity, initial_default_events, activity_started_at = _item_activity_queries(cur, event_period, event_params)

        return {"range_key": range_key, "start": start, "end": end, "db_now": db_now, "kpis": {"sessions": int(kpis[0] or 0), "latest_visit": kpis[1]}, "trend": trend, "v2": v2.iloc[0].to_dict() if not v2.empty else {"stable_visitors": 0, "new_visitors": 0, "returning_visitors": 0}, "modes": modes, "acquisition": acquisition, "posts": posts, "item_interest": item_interest, "item_missing": item_missing, "item_activity": item_activity, "initial_default_events": initial_default_events, "activity_started_at": activity_started_at}
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
