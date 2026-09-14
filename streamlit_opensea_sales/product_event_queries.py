"""Read-only aggregate queries for categorical product events."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from visitor_dashboard_queries import _connect, _event_period_clause, period_bounds


OUTPUT_COLUMNS = ["surface", "event_type", "control_key", "value_key", "events", "unique_sessions", "unique_v2_visitors", "latest_event"]


def load_product_event_aggregates(range_key: str, now: datetime | None = None) -> pd.DataFrame:
    start, end = period_bounds(range_key, now)
    period, params = _event_period_clause(start, end)
    sql = f"""SELECT e.surface, e.event_type, e.control_key, e.value_key,
        count(*)::bigint AS events,
        count(DISTINCT e.parent_session_id)::bigint AS unique_sessions,
        count(DISTINCT s.browser_visitor_hash) FILTER (
            WHERE s.identity_version = 2 AND s.browser_visitor_hash IS NOT NULL
        )::bigint AS unique_v2_visitors,
        max(e.occurred_at_utc) AS latest_event
        FROM public.site_product_events e
        JOIN public.site_visit_sessions s ON s.session_id = e.parent_session_id
        WHERE NOT s.is_bot AND NOT s.is_internal AND {period}
        GROUP BY e.surface, e.event_type, e.control_key, e.value_key
        ORDER BY events DESC, e.surface, e.event_type, e.control_key NULLS FIRST, e.value_key NULLS FIRST"""
    conn = cur = None
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
