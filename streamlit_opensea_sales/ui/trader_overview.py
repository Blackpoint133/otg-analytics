"""Public Trader Analytics presentation backed by the prepared snapshot."""

from __future__ import annotations

import html
import math
from typing import Any, Iterable, Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from trader_analytics import load_current_snapshot, normalize_wallet
from opensea_account_profiles import avatar_style_attribute, get_profile, load_profile_snapshot, profile_name

PANDL_MIN_MATCHED_SALES = 3
PANDL_MIN_COVERAGE_PCT = 50.0
TRADER_PAGE_SIZE = 25
EARNED_COLOR = "#67C77A"
INVESTED_COLOR = "#D8C3A5"
SOLD_COLOR = "#FFD400"
PERFORMANCE_SORTS = {"WIN RATE"}
SORT_OPTIONS = ["EARNED", "INVESTED", "SOLD", "TRADES", "ROI", "WIN RATE"]


def short_wallet(wallet: str) -> str:
    value = str(wallet)
    return value if len(value) <= 12 else f"{value[:6]}…{value[-4:]}"


def trader_is_pnl_eligible(row: dict[str, Any], show_usd: bool = False) -> bool:
    matched = row.get("matched_realized_sales_usd" if show_usd else "matched_realized_sales_gun", row.get("matched_realized_sales", 0))
    rate = row.get("win_rate_usd" if show_usd else "win_rate_gun", row.get("win_rate"))
    return bool(row.get("pnl_supported", False) and (matched or 0) >= PANDL_MIN_MATCHED_SALES and (row.get("pnl_coverage_sell_pct") or 0) >= PANDL_MIN_COVERAGE_PCT and rate is not None)


def resolve_wallet_search(rows: Iterable[dict[str, Any]], query: Optional[str]) -> Optional[dict[str, Any]]:
    wallet = normalize_wallet(query)
    if not wallet:
        return None
    return next((row for row in rows if normalize_wallet(row.get("wallet")) == wallet), None)


def _sort_field(sort_by: str, show_usd: bool) -> str:
    fields = {"EARNED": "realized_pnl_usd" if show_usd else "realized_pnl_gun", "INVESTED": "buy_volume_usd" if show_usd else "buy_volume_gun", "SOLD": "sell_volume_usd" if show_usd else "sell_volume_gun", "TRADES": "trade_count", "ROI": "roi_usd" if show_usd else "roi_gun", "WIN RATE": "win_rate_usd" if show_usd else "win_rate_gun"}
    if sort_by not in fields:
        raise ValueError(f"unsupported trader sort: {sort_by}")
    return fields[sort_by]


def sorted_trader_rows(rows: Iterable[dict[str, Any]], sort_by: str = "EARNED", show_usd: bool = True) -> list[dict[str, Any]]:
    field = _sort_field(sort_by, show_usd)
    result = [row.copy() for row in rows]
    def value(row):
        raw = row.get(field)
        if raw is None and field in {"roi_gun", "roi_usd"}:
            raw = row.get("roi")
        if raw is None and field in {"win_rate_gun", "win_rate_usd"}:
            raw = row.get("win_rate")
        return float(raw) if raw is not None and not pd.isna(raw) else float("-inf")
    if sort_by in {"EARNED", "ROI"}:
        result.sort(key=lambda row: (value(row) == float("-inf"), -value(row) if value(row) != float("-inf") else 0.0, -(int(row.get("trade_count") or 0)), str(row.get("wallet", ""))))
    elif sort_by in PERFORMANCE_SORTS:
        result.sort(key=lambda row: (not trader_is_pnl_eligible(row, show_usd), -value(row), -(int(row.get("trade_count") or 0)), str(row.get("wallet", ""))))
    else:
        result.sort(key=lambda row: (-value(row) if value(row) != float("-inf") else 0.0, -(int(row.get("trade_count") or 0)), str(row.get("wallet", ""))))
    eligible_count = (sum(value(row) != float("-inf") for row in result) if sort_by in {"EARNED", "ROI"} else sum(trader_is_pnl_eligible(row, show_usd) for row in result) if sort_by in PERFORMANCE_SORTS else sum(value(row) != float("-inf") for row in result))
    for index, row in enumerate(result):
        row["eligible"] = trader_is_pnl_eligible(row, show_usd) if sort_by in PERFORMANCE_SORTS else value(row) != float("-inf")
        row["rank"] = index + 1 if index < eligible_count and value(row) != float("-inf") else None
    return result


def page_for_wallet(ranked_rows: Iterable[dict[str, Any]], wallet: Optional[str], page_size: int = TRADER_PAGE_SIZE) -> Optional[int]:
    target = normalize_wallet(wallet)
    if not target:
        return None
    for index, row in enumerate(ranked_rows):
        if normalize_wallet(row.get("wallet")) == target:
            return index // max(1, int(page_size)) + 1
    return None


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


def _rank_maps(rows: list[dict[str, Any]], show_usd: bool) -> dict[str, dict[str, dict[str, Any]]]:
    maps = {}
    for metric in SORT_OPTIONS:
        ranked = sorted_trader_rows(rows, metric, show_usd)
        maps[metric] = {str(row.get("wallet")): {"rank": row.get("rank"), "value": _rank_display_value(row, metric, show_usd)} for row in ranked}
    return maps


def _rank_display_value(row: dict[str, Any], metric: str, show_usd: bool) -> str:
    if metric == "EARNED": return _format_money(row.get("realized_pnl_usd" if show_usd else "realized_pnl_gun"), show_usd, True)
    if metric == "INVESTED": return _format_money(row.get("buy_volume_usd" if show_usd else "buy_volume_gun"), show_usd)
    if metric == "SOLD": return _format_money(row.get("sell_volume_usd" if show_usd else "sell_volume_gun"), show_usd)
    if metric == "TRADES": return str(int(row.get("trade_count") or 0))
    if metric == "ROI": return _format_percent(row.get("roi_usd" if show_usd else "roi_gun"))
    return _format_percent(row.get("win_rate_usd" if show_usd else "win_rate_gun"))


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
        result.append({"Rank": row.get("_position", row.get("rank") or ""), "Profile": row.get("_profile_name") or profile_name(row.get("wallet", ""), row.get("_profile")), "Earned": _format_money(row.get("realized_pnl_usd" if show_usd else "realized_pnl_gun"), show_usd, True), "Invested": _format_money(row.get("buy_volume_usd" if show_usd else "buy_volume_gun"), show_usd), "Sold": _format_money(row.get("sell_volume_usd" if show_usd else "sell_volume_gun"), show_usd), "Trades": int(row.get("trade_count") or 0), "Purchases": int(row.get("buy_count") or 0), "Sales": int(row.get("sell_count") or 0), "ROI": _format_percent(row.get("roi_usd" if show_usd else "roi_gun")), "Win Rate": _format_percent(row.get("win_rate_usd" if show_usd else "win_rate_gun")), "Coverage": _format_percent((row.get("pnl_coverage_sell_pct") or 0) / 100), "Matched Sales": int(row.get("matched_realized_sales") or 0), "_wallet": row.get("wallet", ""), "_profile": row.get("_profile", {}), "_ranks": row.get("_ranks", {}), "_eligible": row.get("eligible", False), "_selected": bool(row.get("_selected", False))})
    return result


def render_trader_table(rows: list[dict[str, Any]]) -> None:
    columns = ["Rank", "Profile", "Earned", "Invested", "Sold", "Trades", "Purchases", "Sales", "ROI", "Win Rate", "Coverage", "Matched Sales"]
    body = []
    for row_number, row in enumerate(rows, 1):
        cells = []
        for column in columns:
            value = html.escape(str(row[column]))
            cls = column.lower().replace(" ", "-")
            if column == "Earned": cls += " earned-value"
            if column == "Invested": cls += " invested-value"
            if column == "Sold": cls += " sold-value"
            if column == "Profile":
                profile = row.get("_profile") or {}
                display = html.escape(str(row["Profile"]))
                wallet = str(row.get("_wallet") or "")
                username = str(profile.get("username") or "").strip()
                secondary = f'<span class="trader-profile-secondary">@{html.escape(username)}</span>' if username and username != row["Profile"] else ""
                avatar_style = " " + avatar_style_attribute(profile, wallet)
                verified = " ✓" if profile.get("is_verified") is True else ""
                ranks = row.get("_ranks", {})
                rank_lines = []
                for metric in SORT_OPTIONS:
                    entry = ranks.get(metric, {})
                    rank = entry.get("rank") or ""
                    label = {"EARNED": "Earned", "INVESTED": "Invested", "SOLD": "Sold", "TRADES": "Trades", "ROI": "ROI", "WIN RATE": "Win Rate"}[metric]
                    rank_lines.append(f'<div><span>{label}</span><b>{html.escape("#" + str(rank) if rank else "—")}</b><em>{html.escape(entry.get("value", "N/A"))}</em></div>')
                ens = str(profile.get("ens_name") or "").strip()
                ens_html = f'<div class="trader-profile-muted">ENS: {html.escape(ens)}</div>' if ens else ""
                rank_html = "".join(rank_lines)
                wallet_html = html.escape(wallet, quote=True)
                short = html.escape(short_wallet(wallet))
                copy_html = ('<button class="trader-wallet-copy" type="button" '
                             f'data-wallet="{wallet_html}">'
                             f'<span class="trader-wallet-short">{short}</span><span class="trader-wallet-copy-label">COPY</span></button>')
                card = f'<div class="trader-profile-card"><div class="trader-profile-card-grid"><div class="trader-profile-avatar"><span class="trader-avatar trader-avatar-large"{avatar_style}></span></div><div class="trader-profile-content"><div class="trader-profile-identity"><div><strong>{display}{verified}</strong>{secondary}<a class="trader-opensea-link" href="https://opensea.io/{wallet_html}" target="_blank" rel="noopener noreferrer">OpenSea profile ↗</a></div></div><div class="trader-profile-label">WALLET ADDRESS</div><div class="trader-wallet-row">{copy_html}</div>{ens_html}<div class="trader-profile-stats-title">TRADING STATS</div><div class="trader-profile-ranks">{rank_html}</div></div></div></div>'
                value = f'<span class="trader-profile-trigger"><span class="trader-avatar trader-avatar-small"{avatar_style}></span><span>{display}{verified}{secondary}</span>{card}</span>'
            cells.append(f'<td class="{cls}">{value}</td>')
        selected_class = " trader-row-selected" if row.get("_selected") else ""
        body.append(f'<tr class="{selected_class.strip()}">' + "".join(cells) + "</tr>")
    css = f"""<style>.trader-table-scroll{{overflow-x:auto;width:100%;margin:16px 0}}.trader-table{{width:100%;min-width:1120px;border-collapse:collapse;background:#000;border:1px solid #FF003A;font-family:'Space Mono',monospace;font-size:11px}}.trader-table thead{{background:#0a0a0a;border-bottom:2px solid #FF003A}}.trader-table th{{color:#FF003A;padding:10px 8px;text-align:left;text-transform:uppercase;letter-spacing:1px;font-size:10px;white-space:nowrap}}.trader-table td{{color:#FFF;padding:8px;border-bottom:1px solid rgba(255,255,255,.04);white-space:nowrap}}.trader-table tbody tr:hover{{background:#0a0a0a}}.trader-table tbody tr.trader-row-selected{{background:rgba(255,0,58,.07);box-shadow:inset 3px 0 0 #FF003A}}.trader-table .earned-value{{color:{EARNED_COLOR};font-weight:700}}.trader-table .invested-value{{color:{INVESTED_COLOR};font-weight:700}}.trader-table .sold-value{{color:{SOLD_COLOR};font-weight:700}}.trader-profile-trigger{{display:inline-flex;align-items:center;gap:8px;position:relative;cursor:default}}.trader-avatar{{display:inline-block;flex:0 0 auto;background-image:var(--trader-remote-avatar,none),var(--trader-fallback-avatar);background-size:cover;background-position:center;background-repeat:no-repeat;border-radius:50%;background-color:#111;border:1px solid #FF003A}}.trader-avatar-small{{width:28px;height:28px}}.trader-avatar-large{{width:44px;height:44px}}.trader-profile-secondary{{display:block;color:#C8C8CD;font-size:10px;font-weight:400}}.trader-profile-card{{--trader-profile-square:390px;display:none;position:absolute;z-index:1000;left:0;bottom:calc(100% + 8px);top:auto;width:min(980px,calc(100vw - 40px));white-space:normal;background:#050505;clip-path:polygon(0 12px,12px 0,calc(100% - 12px) 0,100% 12px,100% calc(100% - 12px),calc(100% - 12px) 100%,12px 100%,0 calc(100% - 12px));padding:22px;color:#FFF;line-height:1.35;box-shadow:0 8px 24px #000}}.trader-profile-card::after{{content:"";position:absolute;inset:5px;z-index:-1;border:1px solid #2f2f35;pointer-events:none}}.trader-profile-card::before{{content:"";position:absolute;left:0;right:0;height:8px;bottom:-8px}}.trader-table tbody tr:nth-child(-n+8) .trader-profile-card{{top:calc(100% + 8px);bottom:auto}}.trader-table tbody tr:nth-child(-n+8) .trader-profile-card::before{{top:-8px;bottom:auto}}.trader-profile-trigger:hover .trader-profile-card{{display:block}}.trader-profile-card-grid{{display:grid;grid-template-columns:var(--trader-profile-square) minmax(0,1fr);height:var(--trader-profile-square);gap:24px;align-items:stretch}}.trader-profile-avatar{{width:var(--trader-profile-square);height:var(--trader-profile-square);aspect-ratio:1/1;background:#080808;position:relative;overflow:hidden;border:1px solid #303035;box-sizing:border-box}}.trader-profile-card .trader-avatar-large{{display:block;width:100%;height:100%;aspect-ratio:1/1;border-radius:0;border:0;background-size:contain;background-position:center;background-repeat:no-repeat}}.trader-profile-avatar::before{{content:"OFF\\A THE\\A GRID";white-space:pre;color:#7b7b82;font-size:9px;line-height:1.05;letter-spacing:2px;position:absolute;left:10px;top:10px;z-index:1;pointer-events:none}}.trader-profile-avatar::after{{content:"TRADERS\\A BUILD\\A DIFFERENT";white-space:pre;color:#7b7b82;font-size:8px;line-height:1.05;letter-spacing:1px;position:absolute;right:10px;bottom:10px;text-align:right;z-index:1;pointer-events:none}}.trader-profile-content{{min-width:0;height:var(--trader-profile-square);max-height:var(--trader-profile-square);position:relative}}.trader-profile-content::before{{content:"TRADER\\A PROFILE";white-space:pre;position:absolute;right:0;top:-2px;color:#77777d;font-size:9px;line-height:1.1;letter-spacing:2px;text-align:right}}.trader-profile-identity{{display:flex;align-items:center;gap:10px;margin-bottom:10px;padding-right:92px}}.trader-profile-identity strong{{display:block;color:#FFF;font-size:32px;line-height:1.05;overflow-wrap:anywhere}}.trader-profile-card a{{color:#FF003A;margin:4px 0;text-decoration:none}}.trader-opensea-link{{display:inline-block;font-size:13px}}.trader-profile-muted{{color:#C8C8CD;font-size:10px;overflow-wrap:anywhere}}.trader-profile-label{{color:#C8C8CD;font-size:9px;font-weight:700;letter-spacing:1.5px;margin-top:6px}}.trader-wallet-row{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:6px 8px;border:1px solid #3a3a40;border-left:2px solid #FF003A;background:#090909}}.trader-wallet-copy{{display:flex;align-items:center;justify-content:space-between;gap:16px;min-width:250px;background:transparent;border:0;color:#FFF;padding:2px;font:inherit;cursor:pointer;text-align:left}}.trader-wallet-copy:hover{{color:#FFF}}.trader-wallet-copy span{{color:#FF003A;margin-left:0}}.trader-wallet-short{{overflow-wrap:anywhere}}.trader-profile-stats-title{{display:flex;justify-content:space-between;color:#FF003A;font-size:10px;font-weight:700;letter-spacing:1.5px;margin-top:10px;border:1px solid #FF003A;border-bottom:0;padding:6px 8px}}.trader-profile-stats-title::after{{content:"ONCHAIN PERFORMANCE";color:#77777d;font-weight:400}}.trader-profile-ranks{{border:1px solid #FF003A;margin-top:0;padding:4px 6px;font-size:10px;background:#080808}}.trader-profile-ranks div{{display:grid;grid-template-columns:12px minmax(70px,1fr) 44px minmax(100px,1fr);gap:6px;align-items:center;border:1px solid #303035;border-left:2px solid #FF003A;background:#0b0b0b;padding:4px 6px;margin:2px 0;min-height:18px}}.trader-profile-ranks div::before{{content:"//";color:#FF003A}}.trader-profile-ranks b{{color:#FFF;border-right:1px solid #FF003A;padding-right:6px}}.trader-profile-ranks em{{color:#C8C8CD;font-style:normal;text-align:right;overflow-wrap:anywhere}}@media (max-width:768px){{.trader-profile-card{{--trader-profile-square:auto;width:min(560px,calc(100vw - 24px));left:0}}.trader-profile-card-grid{{grid-template-columns:1fr;height:auto}}.trader-profile-avatar{{width:min(100%,300px);height:auto;aspect-ratio:1/1}}.trader-profile-content{{height:auto;max-height:none}}.trader-profile-identity strong{{font-size:24px}}.trader-profile-content::before{{font-size:8px}}}}</style><div class="trader-table-scroll"><table class="trader-table"><thead><tr>{''.join(f'<th>{c}</th>' for c in columns)}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"""
    st.markdown(css, unsafe_allow_html=True)
    components.html("""
<script>
(function () {
  function wire() {
    var doc;
    try { doc = window.parent.document; } catch (e) { return false; }
    var buttons = doc.querySelectorAll('.trader-wallet-copy[data-wallet]');
    if (!buttons.length) return false;
    buttons.forEach(function (button) {
      if (button.dataset.otgClipboardBound) return;
      button.dataset.otgClipboardBound = '1';
      button.addEventListener('click', function () {
        var label = button.querySelector('.trader-wallet-copy-label');
        if (!label) return;
        var restore = function () { label.textContent = 'COPY'; };
        var write = (navigator.clipboard && navigator.clipboard.writeText)
          ? navigator.clipboard.writeText(button.dataset.wallet)
          : Promise.reject(new Error('Clipboard API unavailable'));
        write.then(function () {
          label.textContent = 'COPIED';
          window.setTimeout(restore, 1200);
        }).catch(restore);
      });
    });
    return true;
  }
  var timer = window.setInterval(function () { if (wire()) window.clearInterval(timer); }, 100);
  wire();
})();
</script>
""", height=0, width=0)


def _render_metric_guide() -> None:
    from ui.section_guide import render_section_guide_panel
    render_section_guide_panel("""<p><b>EARNED</b> Realized profit/loss only from sales matched to a previous purchase of the exact same NFT.</p><p><b>INVESTED</b> Total value of all observed OpenSea purchases. <b>SOLD</b> Total value of all observed OpenSea sales.</p><p><b>TRADES</b> Observed marketplace participations. <b>PURCHASES</b> Observed purchases. <b>SALES</b> Observed sales.</p><p><b>ROI</b> Realized return on the acquisition cost of matched sold NFTs only. It is not return on total Invested.</p><p><b>WIN RATE</b> Share of evaluable matched sales closed in profit. <b>COVERAGE</b> Share of observed sales that could be matched to a previous acquisition. <b>MATCHED SALES</b> Sales linked to an observed previous purchase of the exact contract + tokenId.</p><p class="trader-guide-note"><b>Currency:</b> When USD Price is enabled, monetary metrics, ROI and Win Rate use historical USD values based on the GUN/USD price at the time of each transaction. When USD Price is disabled, those metrics use GUN values.</p><p class="trader-guide-note">Metrics are based only on observed OpenSea activity. Unknown external transfers, mints, in-game acquisitions, other marketplaces, fees and royalties are not included unless explicitly present in source data.</p>""", trusted_html=True)


def render_trader_overview(sort_by: str = "EARNED", show_usd: bool = True, highlight_wallet: Optional[str] = None, guide_open: bool = False) -> None:
    payload = load_current_snapshot()
    if guide_open:
        _render_metric_guide()
    st.markdown(f"""
        <style>
        .trader-ranking-header {{ margin-bottom:16px; }}
        .trader-ranking-header h3 {{
            margin:0 0 4px 0; border-bottom:2px solid var(--otg-accent);
            padding-bottom:6px; text-transform:uppercase; font-size:16px;
            letter-spacing:1px; font-family:'PP Supply Sans','Space Mono',monospace,sans-serif;
            color:var(--otg-accent); font-weight:700;
        }}
        .trader-ranking-subtitle {{ font-size:13px; color:var(--otg-text-secondary); text-transform:uppercase; letter-spacing:.5px; margin:4px 0; }}
        .trader-ranking-context {{ font-size:11px; color:var(--otg-text-secondary); text-transform:uppercase; letter-spacing:.4px; margin:4px 0 12px; }}
        .st-key-trader_pagination [data-testid="stHorizontalBlock"] {{ display:grid!important; grid-template-columns:110px minmax(0,1fr) 110px!important; column-gap:0!important; width:100%!important; align-items:start!important; }}
        .st-key-trader_pagination [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{ width:100%!important; min-width:0!important; max-width:none!important; padding:0!important; flex:none!important; }}
        .st-key-trader_pagination [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {{ display:flex!important; justify-content:flex-start!important; }}
        .st-key-trader_pagination [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {{ display:flex!important; justify-content:flex-end!important; }}
        .st-key-trader_pagination [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {{ display:flex!important; justify-content:center!important; }}
        .st-key-trader_pagination button {{ width:110px!important; background:#000!important; color:#FFF!important; border:1px solid #FF003A!important; border-radius:0!important; }}
        .st-key-trader_pagination button:hover:not(:disabled) {{ background:#FF003A!important; color:#000!important; }}
        .st-key-trader_pagination button:disabled {{ opacity:.35!important; }}
        </style>
        <div class="trader-ranking-header">
            <h3>TOP TRADERS ANALYTICS</h3>
            <div class="trader-ranking-subtitle">PUBLIC OPENSEA TRADER OVERVIEW</div>
            <div class="trader-ranking-context">SORT BY {html.escape(sort_by)} · {'USD' if show_usd else 'GUN'}</div>
        </div>
    """, unsafe_allow_html=True)
    if not payload:
        st.warning("Top Traders Analytics data is temporarily unavailable.")
        return
    rows = payload.get("wallets", [])
    profile_snapshot = load_profile_snapshot()
    render_trader_table.fallback_names = profile_snapshot.get("fallback_names", {})
    rank_maps = _rank_maps(rows, show_usd)
    rows = [dict(row, _profile=get_profile(row.get("wallet", ""), profile_snapshot), _ranks={metric: rank_maps[metric].get(str(row.get("wallet")), {}) for metric in SORT_OPTIONS}) for row in rows]
    fallback_names = profile_snapshot.get("fallback_names", {})
    rows = [dict(row, _profile=row.get("_profile", {})) for row in rows]
    for row in rows:
        row["_profile"] = row.get("_profile", {})
        row["_profile_name"] = profile_name(row.get("wallet", ""), row["_profile"], fallback_names)
    ranked = [dict(row, _position=index + 1) for index, row in enumerate(sorted_trader_rows(rows, sort_by, show_usd))]
    selected_wallet = normalize_wallet(highlight_wallet)
    signature = (sort_by, show_usd, selected_wallet)
    if st.session_state.get("trader_previous_selection") != signature:
        st.session_state.trader_previous_selection = signature
        st.session_state.trader_page = page_for_wallet(ranked, selected_wallet) or 1
    visible, page, pages = paginate_traders(ranked, st.session_state.get("trader_page", 1)); st.session_state.trader_page = page
    visible = [dict(row, _selected=bool(selected_wallet and normalize_wallet(row.get("wallet")) == selected_wallet)) for row in visible]
    render_trader_table(consolidated_table_rows(visible, show_usd))
    with st.container(key="trader_pagination"):
        nav = st.columns([1, 2, 1], gap="small")
        if nav[0].button("Previous", disabled=page <= 1, key="trader_prev", use_container_width=False): st.session_state.trader_page = page - 1; st.rerun()
        nav[1].markdown(f"<div style='text-align:center;padding:8px;color:#FFF'>Page {page} of {pages}</div>", unsafe_allow_html=True)
        if nav[2].button("Next", disabled=page >= pages, key="trader_next", use_container_width=False): st.session_state.trader_page = page + 1; st.rerun()
