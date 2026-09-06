"""Public Trader Analytics presentation backed by the prepared snapshot."""

from __future__ import annotations

import html
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
PERFORMANCE_SORTS = {"EARNED", "ROI", "WIN RATE"}
SORT_OPTIONS = ["EARNED", "INVESTED", "SOLD", "TRADES", "ROI", "WIN RATE"]


def short_wallet(wallet: str) -> str:
    value = str(wallet)
    return value if len(value) <= 12 else f"{value[:6]}…{value[-4:]}"


def trader_is_pnl_eligible(row: dict[str, Any]) -> bool:
    return bool(row.get("pnl_supported", False) and (row.get("matched_realized_sales") or 0) >= PANDL_MIN_MATCHED_SALES and (row.get("pnl_coverage_sell_pct") or 0) >= PANDL_MIN_COVERAGE_PCT)


def resolve_wallet_search(rows: Iterable[dict[str, Any]], query: Optional[str]) -> Optional[dict[str, Any]]:
    wallet = normalize_wallet(query)
    if not wallet:
        return None
    return next((row for row in rows if normalize_wallet(row.get("wallet")) == wallet), None)


def _sort_field(sort_by: str, show_usd: bool) -> str:
    fields = {"EARNED": "realized_pnl_usd" if show_usd else "realized_pnl_gun", "INVESTED": "buy_volume_usd" if show_usd else "buy_volume_gun", "SOLD": "sell_volume_usd" if show_usd else "sell_volume_gun", "TRADES": "trade_count", "ROI": "roi", "WIN RATE": "win_rate"}
    if sort_by not in fields:
        raise ValueError(f"unsupported trader sort: {sort_by}")
    return fields[sort_by]


def sorted_trader_rows(rows: Iterable[dict[str, Any]], sort_by: str = "EARNED", show_usd: bool = True) -> list[dict[str, Any]]:
    field = _sort_field(sort_by, show_usd)
    result = [row.copy() for row in rows]
    def value(row):
        raw = row.get(field)
        return float(raw) if raw is not None and not pd.isna(raw) else float("-inf")
    if sort_by in PERFORMANCE_SORTS:
        result.sort(key=lambda row: (not trader_is_pnl_eligible(row), -value(row), -(int(row.get("trade_count") or 0)), str(row.get("wallet", ""))))
    else:
        result.sort(key=lambda row: (-value(row) if value(row) != float("-inf") else 0.0, -(int(row.get("trade_count") or 0)), str(row.get("wallet", ""))))
    eligible_count = sum(trader_is_pnl_eligible(row) for row in result) if sort_by in PERFORMANCE_SORTS else len(result)
    for index, row in enumerate(result):
        row["eligible"] = trader_is_pnl_eligible(row)
        row["rank"] = index + 1 if index < eligible_count else None
    return result


def leaderboard_rows(rows: Iterable[dict[str, Any]], metric: str = "EARNED", currency: str = "USD") -> list[dict[str, Any]]:
    aliases = {"Observed P&L": "EARNED", "Volume": "SOLD", "Trades": "TRADES", "Win Rate": "WIN RATE"}
    return sorted_trader_rows(rows, aliases.get(metric, metric), currency == "USD")


def paginate_traders(rows: list[dict[str, Any]], page: int = 1, page_size: int = TRADER_PAGE_SIZE) -> tuple[list[dict[str, Any]], int, int]:
    pages = max(1, math.ceil(len(rows) / max(1, int(page_size))))
    page = min(max(1, int(page)), pages)
    start = (page - 1) * page_size
    return rows[start:start + page_size], page, pages


def metric_color(metric: str) -> str:
    return {"EARNED": EARNED_COLOR, "INVESTED": INVESTED_COLOR, "SOLD": SOLD_COLOR}.get(metric, "#FFFFFF")


def _format_money(value: Any, show_usd: bool, signed: bool = False) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    suffix = " USD" if show_usd else " GUN"
    return f"{float(value):+,.2f}{suffix}" if signed else f"{float(value):,.2f}{suffix}"


def _format_percent(value: Any) -> str:
    return "N/A" if value is None or pd.isna(value) else f"{float(value) * 100:.1f}%"


def consolidated_table_rows(rows: Iterable[dict[str, Any]], show_usd: bool = True) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        result.append({"Rank": row.get("rank") or "", "Wallet": short_wallet(row.get("wallet", "")), "Earned": _format_money(row.get("realized_pnl_usd" if show_usd else "realized_pnl_gun"), show_usd, True), "Invested": _format_money(row.get("buy_volume_usd" if show_usd else "buy_volume_gun"), show_usd), "Sold": _format_money(row.get("sell_volume_usd" if show_usd else "sell_volume_gun"), show_usd), "Trades": int(row.get("trade_count") or 0), "Purchases": int(row.get("buy_count") or 0), "Sales": int(row.get("sell_count") or 0), "ROI": _format_percent(row.get("roi")), "Win Rate": _format_percent(row.get("win_rate")), "Coverage": _format_percent((row.get("pnl_coverage_sell_pct") or 0) / 100), "Matched Sales": int(row.get("matched_realized_sales") or 0), "_wallet": row.get("wallet", ""), "_eligible": row.get("eligible", False)})
    return result


def render_trader_table(rows: list[dict[str, Any]]) -> None:
    columns = ["Rank", "Wallet", "Earned", "Invested", "Sold", "Trades", "Purchases", "Sales", "ROI", "Win Rate", "Coverage", "Matched Sales"]
    body = []
    for row in rows:
        cells = []
        for column in columns:
            value = html.escape(str(row[column]))
            cls = column.lower().replace(" ", "-")
            if column == "Earned": cls += " earned-value"
            if column == "Invested": cls += " invested-value"
            if column == "Sold": cls += " sold-value"
            if column == "Wallet": value = f'<span title="{html.escape(row["_wallet"], quote=True)}">{value}</span>'
            cells.append(f'<td class="{cls}">{value}</td>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    css = f"""<style>.trader-table-scroll{{overflow-x:auto;width:100%;margin:16px 0}}.trader-table{{width:100%;min-width:1120px;border-collapse:collapse;background:#000;border:1px solid #FF003A;font-family:'Space Mono',monospace;font-size:11px}}.trader-table thead{{background:#0a0a0a;border-bottom:2px solid #FF003A}}.trader-table th{{color:#FF003A;padding:10px 8px;text-align:left;text-transform:uppercase;letter-spacing:.5px;font-size:10px;white-space:nowrap}}.trader-table td{{color:#FFF;padding:8px;border-bottom:1px solid rgba(255,255,255,.04);white-space:nowrap}}.trader-table tbody tr:hover{{background:#0a0a0a}}.trader-table .earned-value{{color:{EARNED_COLOR};font-weight:700}}.trader-table .invested-value{{color:{INVESTED_COLOR};font-weight:700}}.trader-table .sold-value{{color:{SOLD_COLOR};font-weight:700}}</style><div class="trader-table-scroll"><table class="trader-table"><thead><tr>{''.join(f'<th>{c}</th>' for c in columns)}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"""
    st.markdown(css, unsafe_allow_html=True)


def _render_detail(row: dict[str, Any], show_usd: bool) -> None:
    st.subheader(f"TRADER · {short_wallet(row['wallet'])}")
    st.caption(f"Wallet: `{row['wallet']}`")
    cols = st.columns(3)
    cols[0].metric("EARNED", _format_money(row.get("realized_pnl_usd" if show_usd else "realized_pnl_gun"), show_usd, True))
    cols[1].metric("INVESTED", _format_money(row.get("buy_volume_usd" if show_usd else "buy_volume_gun"), show_usd))
    cols[2].metric("SOLD", _format_money(row.get("sell_volume_usd" if show_usd else "sell_volume_gun"), show_usd))
    if not trader_is_pnl_eligible(row): st.info("Insufficient matched history for performance leaderboard.")
    detail = {"ROI": _format_percent(row.get("roi")), "Win Rate": _format_percent(row.get("win_rate")), "Coverage": _format_percent((row.get("pnl_coverage_sell_pct") or 0) / 100), "Matched Sales": row.get("matched_realized_sales", 0), "Unmatched Sales": row.get("unmatched_sales", 0), "Trades": row.get("trade_count", 0), "Purchases": row.get("buy_count", 0), "Sales": row.get("sell_count", 0), "Unique Items / Assets": f"{row.get('unique_items_traded', 0)} / {row.get('unique_assets_traded', 0)}", "Counterparties": row.get("unique_counterparties", 0), "Active Days": row.get("active_days", 0), "First Trade": row.get("first_trade_at") or "N/A", "Last Trade": row.get("last_trade_at") or "N/A"}
    st.dataframe(pd.DataFrame([detail]), use_container_width=True, hide_index=True)


def render_trader_overview(sort_by: str = "EARNED", show_usd: bool = True, highlight_wallet: Optional[str] = None) -> None:
    payload = load_current_snapshot()
    st.title("TRADER ANALYTICS")
    if not payload:
        st.warning("Trader Analytics data is temporarily unavailable.")
        return
    rows = payload.get("wallets", [])
    eligible_count = sum(trader_is_pnl_eligible(row) for row in rows)
    st.caption(f"Public OpenSea activity · Tracked Traders: {payload.get('wallet_count', len(rows)):,} · Observed Trades: {payload.get('event_count', 0):,} · P&L Eligible: {eligible_count:,} · Data since {str(payload.get('date_min') or 'N/A')[:10]}")
    if sort_by in PERFORMANCE_SORTS: st.caption(f"Eligibility: at least {PANDL_MIN_MATCHED_SALES} matched sales and {PANDL_MIN_COVERAGE_PCT:.0f}% P&L coverage.")
    ranked = sorted_trader_rows(rows, sort_by, show_usd)
    signature = (sort_by, show_usd)
    if st.session_state.get("trader_previous_selection") != signature:
        st.session_state.trader_previous_selection = signature; st.session_state.trader_page = 1
    visible, page, pages = paginate_traders(ranked, st.session_state.get("trader_page", 1)); st.session_state.trader_page = page
    render_trader_table(consolidated_table_rows(visible, show_usd))
    nav = st.columns([1, 2, 1])
    if nav[0].button("Previous", disabled=page <= 1, key="trader_prev"): st.session_state.trader_page = page - 1; st.rerun()
    nav[1].markdown(f"<div style='text-align:center;padding:8px;color:#FFF'>Page {page} of {pages}</div>", unsafe_allow_html=True)
    if nav[2].button("Next", disabled=page >= pages, key="trader_next"): st.session_state.trader_page = page + 1; st.rerun()
    selected = resolve_wallet_search(rows, highlight_wallet) if highlight_wallet else None
    if selected: _render_detail(selected, show_usd)
