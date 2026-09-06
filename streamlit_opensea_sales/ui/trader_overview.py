"""Public Trader Analytics page backed only by the prepared snapshot."""

from __future__ import annotations

import math
from typing import Any, Iterable, Optional

import pandas as pd
import streamlit as st

from trader_analytics import load_current_snapshot, normalize_wallet


PANDL_MIN_MATCHED_SALES = 3
PANDL_MIN_COVERAGE_PCT = 50.0
TRADER_PAGE_SIZE = 25
EARNED_COLOR = "#67C77A"
INVESTED_COLOR = "#D8C3A5"
SOLD_COLOR = "#FFD400"


def short_wallet(wallet: str) -> str:
    value = str(wallet)
    return value if len(value) <= 12 else f"{value[:6]}…{value[-4:]}"


def trader_is_pnl_eligible(row: dict[str, Any]) -> bool:
    return bool(
        row.get("pnl_supported", False)
        and (row.get("matched_realized_sales") or 0) >= PANDL_MIN_MATCHED_SALES
        and (row.get("pnl_coverage_sell_pct") or 0) >= PANDL_MIN_COVERAGE_PCT
    )


def resolve_wallet_search(rows: Iterable[dict[str, Any]], query: Optional[str]) -> Optional[dict[str, Any]]:
    wallet = normalize_wallet(query)
    if not wallet:
        return None
    return next((row for row in rows if normalize_wallet(row.get("wallet")) == wallet), None)


def leaderboard_rows(rows: Iterable[dict[str, Any]], metric: str = "EARNED", currency: str = "USD") -> list[dict[str, Any]]:
    field_map = {
        "EARNED": "realized_pnl_usd" if currency == "USD" else "realized_pnl_gun",
        "ROI": "roi",
        "WIN RATE": "win_rate",
        "INVESTED": "buy_volume_usd" if currency == "USD" else "buy_volume_gun",
        "SOLD": "sell_volume_usd" if currency == "USD" else "sell_volume_gun",
        "TRADES": "trade_count",
    }
    if metric not in field_map:
        raise ValueError(f"unsupported trader metric: {metric}")
    result = list(rows)
    if metric in {"EARNED", "ROI", "WIN RATE"}:
        result = [row for row in result if trader_is_pnl_eligible(row) and row.get(field_map[metric]) is not None]
    result.sort(key=lambda row: (-(float(row.get(field_map[metric]) or 0)), -(int(row.get("trade_count") or 0)), str(row.get("wallet", ""))))
    for rank, row in enumerate(result, 1):
        row = row.copy()
        row["rank"] = rank
        row["metric_value"] = row.get(field_map[metric])
        result[rank - 1] = row
    return result


def paginate_traders(rows: list[dict[str, Any]], page: int = 1, page_size: int = TRADER_PAGE_SIZE) -> tuple[list[dict[str, Any]], int, int]:
    page_size = max(1, int(page_size))
    pages = max(1, math.ceil(len(rows) / page_size))
    page = min(max(1, int(page)), pages)
    start = (page - 1) * page_size
    return rows[start:start + page_size], page, pages


def metric_color(metric: str) -> str:
    return {"EARNED": EARNED_COLOR, "INVESTED": INVESTED_COLOR, "SOLD": SOLD_COLOR}.get(metric, "#FFFFFF")


def _format_metric(value: Any, metric: str, currency: str) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    if metric == "ROI":
        return f"{float(value) * 100:+.2f}%"
    if metric == "Win Rate":
        return f"{float(value) * 100:.1f}%"
    if metric == "TRADES":
        return f"{int(value):,}"
    suffix = " USD" if currency == "USD" else " GUN"
    return f"{float(value):+,.2f}{suffix}" if metric == "EARNED" else f"{float(value):,.2f}{suffix}"


def _render_detail(row: dict[str, Any], currency: str) -> None:
    st.subheader(f"TRADER · {short_wallet(row['wallet'])}")
    st.caption(f"Wallet: `{row['wallet']}`")
    cols = st.columns(4)
    pnl = row.get("realized_pnl_usd" if currency == "USD" else "realized_pnl_gun")
    cols[0].metric("EARNED", _format_metric(pnl, "EARNED", currency))
    cols[1].metric("ROI", _format_metric(row.get("roi"), "ROI", currency))
    cols[2].metric("Win Rate", _format_metric(row.get("win_rate"), "Win Rate", currency))
    cols[3].metric("P&L Coverage", f"{float(row.get('pnl_coverage_sell_pct') or 0):.1f}%")
    if not trader_is_pnl_eligible(row):
        st.info("Insufficient coverage for leaderboard. Observed P&L excludes unknown-cost sales.")
    details = {
        "EARNED": _format_metric(pnl, "EARNED", currency),
        "INVESTED": _format_metric(row.get("buy_volume_usd" if currency == "USD" else "buy_volume_gun"), "INVESTED", currency),
        "SOLD": _format_metric(row.get("sell_volume_usd" if currency == "USD" else "sell_volume_gun"), "SOLD", currency),
        "Matched Sales": row.get("matched_realized_sales", 0), "Unmatched Sales": row.get("unmatched_sales", 0),
        "Trades": row.get("trade_count", 0), "Buy Volume": _format_metric(row.get("buy_volume_usd" if currency == "USD" else "buy_volume_gun"), "Volume", currency),
        "Sell Volume": _format_metric(row.get("sell_volume_usd" if currency == "USD" else "sell_volume_gun"), "Volume", currency),
        "Total Volume": _format_metric(row.get("total_volume_usd" if currency == "USD" else "total_volume_gun"), "Volume", currency),
        "Unique Items / Assets": f"{row.get('unique_items_traded', 0)} / {row.get('unique_assets_traded', 0)}",
        "Counterparties": row.get("unique_counterparties", 0), "Active Days": row.get("active_days", 0),
        "First Trade": row.get("first_trade_at") or "N/A", "Last Trade": row.get("last_trade_at") or "N/A",
    }
    st.dataframe(pd.DataFrame([details]), use_container_width=True, hide_index=True)


def render_trader_overview(metric: str = "EARNED", currency: str = "USD", highlight_wallet: Optional[str] = None) -> None:
    payload = load_current_snapshot()
    st.title("TRADER ANALYTICS")
    if not payload:
        st.warning("Trader Analytics data is temporarily unavailable.")
        return
    rows = payload.get("wallets", [])
    eligible_count = sum(trader_is_pnl_eligible(row) for row in rows)
    st.caption("Public OpenSea activity analytics. EARNED is observed realized P&L from matched exact-NFT buy/sell cycles; unknown-cost sales are excluded.")
    st.caption(f"Tracked Traders: {payload.get('wallet_count', len(rows)):,} · Observed Trades: {payload.get('event_count', 0):,} · P&L Eligible: {eligible_count:,} · Data since {str(payload.get('date_min') or 'N/A')[:10]}")
    ranked = leaderboard_rows(rows, metric, currency)
    selection_signature = (metric, currency)
    if st.session_state.get("trader_previous_selection") != selection_signature:
        st.session_state.trader_previous_selection = selection_signature
        st.session_state.trader_page = 1
    page = st.session_state.get("trader_page", 1)
    visible, page, pages = paginate_traders(ranked, page)
    st.session_state.trader_page = page
    if metric in {"EARNED", "ROI", "WIN RATE"}:
        st.caption(f"Eligibility: at least {PANDL_MIN_MATCHED_SALES} matched sales and {PANDL_MIN_COVERAGE_PCT:.0f}% P&L coverage.")
    if not ranked:
        st.info("No traders meet the selected metric's eligibility requirements.")
    else:
        columns = [{"Rank": r["rank"], "Wallet": short_wallet(r["wallet"]), metric: _format_metric(r["metric_value"], metric, currency)} for r in visible]
        if metric in {"EARNED", "ROI", "WIN RATE"}:
            columns = [{**r, "Matched Sales": source.get("matched_realized_sales", 0), "Coverage": f"{float(source.get('pnl_coverage_sell_pct') or 0):.0f}%"} for r, source in zip(columns, visible)]
        elif metric == "INVESTED":
            columns = [{**r, "Purchases": source.get("buy_count", 0)} for r, source in zip(columns, visible)]
        elif metric == "SOLD":
            columns = [{**r, "Sales": source.get("sell_count", 0)} for r, source in zip(columns, visible)]
        elif metric == "TRADES":
            columns = [{**r, "Buys": source.get("buy_count", 0), "Sales": source.get("sell_count", 0)} for r, source in zip(columns, visible)]
        table = columns
        leaderboard = pd.DataFrame(table)
        st.dataframe(leaderboard.style.map(lambda _: f"color: {metric_color(metric)}", subset=[metric]), use_container_width=True, hide_index=True)
        nav = st.columns([1, 2, 1])
        if nav[0].button("Previous", disabled=page <= 1, key="trader_prev"):
            st.session_state.trader_page = page - 1; st.rerun()
        nav[1].markdown(f"<div style='text-align:center;padding:8px'>Page {page} of {pages}</div>", unsafe_allow_html=True)
        if nav[2].button("Next", disabled=page >= pages, key="trader_next"):
            st.session_state.trader_page = page + 1; st.rerun()

    selected = resolve_wallet_search(rows, highlight_wallet) if highlight_wallet else None
    if selected:
        _render_detail(selected, currency)
