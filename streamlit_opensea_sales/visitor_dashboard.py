"""Protected, read-only visitor analytics dashboard."""

from __future__ import annotations

import hmac
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from visitor_dashboard_queries import (
    DISPLAY_TIMEZONE,
    load_dashboard_data,
    load_visitor_summaries,
    load_visitor_timeline,
    load_visitor_item_activity,
)
from product_event_queries import load_product_event_aggregates


AUTH_KEY = "visitor_dashboard_authenticated"
RANGE_LABELS = ("24H", "7D", "30D", "ALL")
MODE_LABELS = {"item": "Item Analytics", "market": "Market Analytics", "top_items": "Top Items Analytics", "trader": "Top Traders Analytics"}
DISPLAY_ZONE = ZoneInfo(DISPLAY_TIMEZONE)


def _password_configured() -> str:
    return os.getenv("OTG_INTERNAL_ANALYTICS_PASSWORD", "").strip()


def _render_login() -> bool:
    configured = _password_configured()
    st.title("Visitor Analytics")
    st.caption("Internal / read-only")
    if not configured:
        st.info("Internal analytics access is not configured.")
        return False
    with st.form("visitor_dashboard_login"):
        candidate = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Open dashboard", type="primary")
    if submitted:
        if hmac.compare_digest(candidate, configured):
            st.session_state[AUTH_KEY] = True
            st.rerun()
        st.error("Access denied.")
    return False


def _fmt_time(value: datetime | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return value.astimezone(DISPLAY_ZONE).strftime("%b %d, %I:%M %p PT").replace(" 0", " ")


def _chart_layout(fig: go.Figure, showlegend: bool = True) -> go.Figure:
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=25, b=35), template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#e8e8ec"), showlegend=showlegend)
    return fig


def _render_product_usage(product_data: pd.DataFrame | None) -> None:
    st.subheader("Product Usage")
    st.caption("Privacy-safe categorical interaction events. Wallets, usernames, search text, IPs and browser identifiers are not stored in product-event rows. Item selections remain in Item Activity.")
    if product_data is None:
        st.info("Product usage data is temporarily unavailable.")
        return
    if product_data.empty:
        st.info("No product usage events in this period.")
        return
    surface_labels = {"item": "Item Analytics", "market": "Market Analytics", "top_items": "Top Items Analytics", "trader": "Top Traders Analytics"}
    control_labels = {"wallet_filter": "Wallet Filter", "item_class_filter": "Item Class Filter", "trader_filter": "Trader Filter", "sort": "Sort", "period": "Period", "view": "View", "usd_price": "USD Price", "trend_line": "Trend Line", "token_price": "Token Price", "unique_wallets": "Unique Wallets"}
    event_labels = {"filter_apply": "Filter Apply", "filter_clear": "Filter Clear", "sort_change": "Sort Change", "period_change": "Period Change", "view_change": "View Change", "toggle_change": "Toggle Change"}
    value_labels = {"on": "ON", "off": "OFF", "market_strength": "MARKET STRENGTH", "volume": "VOLUME", "liquidity": "LIQUIDITY", "total_supply": "TOTAL SUPPLY", "earned": "EARNED", "invested": "INVESTED", "sold": "SOLD", "trades": "TRADES", "all": "ALL", "12m": "12M", "6m": "6M", "3m": "3M", "30d": "30D", "7d": "7D", "1d": "1D", "chart": "CHART", "table": "TABLE"}
    opens = product_data[product_data["event_type"] == "surface_open"]
    interactions = product_data[product_data["event_type"] != "surface_open"]
    metrics = st.columns(4)
    metrics[0].metric("Product Events", f"{int(product_data['events'].sum()):,}")
    metrics[1].metric("Surface Opens", f"{int(opens['events'].sum()):,}")
    metrics[2].metric("Feature Interactions", f"{int(interactions['events'].sum()):,}")
    metrics[3].metric("Latest Product Event", _fmt_time(product_data["latest_event"].max()))
    left, right = st.columns(2)
    with left:
        st.subheader("Surface Opens")
        if opens.empty:
            st.info("No surface-open events in this period.")
        else:
            grouped = opens.groupby("surface", as_index=False)["events"].sum()
            grouped["label"] = grouped["surface"].map(surface_labels).fillna(grouped["surface"])
            fig = go.Figure(go.Bar(x=grouped["events"], y=grouped["label"], orientation="h", marker_color="#ff003a", text=grouped["events"], textposition="auto"))
            st.plotly_chart(_chart_layout(fig, showlegend=False), use_container_width=True)
    with right:
        st.subheader("Feature Interactions")
        if interactions.empty:
            st.info("No feature interactions in this period.")
        else:
            grouped = interactions.copy()
            grouped["label"] = [
                f"{surface_labels.get(surface, surface)}  {control_labels.get(control, control)}"
                for surface, control in zip(grouped["surface"], grouped["control_key"])
            ]
            grouped = grouped.groupby("label", as_index=False)["events"].sum().sort_values(["events", "label"], ascending=[True, True]).tail(15)
            fig = go.Figure(go.Bar(x=grouped["events"], y=grouped["label"], orientation="h", marker_color="#62d9ff", text=grouped["events"], textposition="auto"))
            st.plotly_chart(_chart_layout(fig, showlegend=False), use_container_width=True)
    if interactions.empty:
        st.info("No feature interactions in this period.")
        return
    st.markdown("**Product Interaction Detail**")
    detail = interactions.copy()
    detail["Surface"] = detail["surface"].map(surface_labels).fillna(detail["surface"])
    detail["Interaction"] = detail["event_type"].map(event_labels).fillna(detail["event_type"])
    detail["Feature"] = detail["control_key"].map(control_labels).fillna(detail["control_key"])
    detail["Value"] = detail["value_key"].map(value_labels)
    unknown_value = detail["Value"].isna() & detail["value_key"].notna()
    detail.loc[unknown_value, "Value"] = detail.loc[unknown_value, "value_key"]
    detail["Value"] = detail["Value"].fillna("")
    detail["Latest Event"] = detail["latest_event"].map(_fmt_time)
    st.dataframe(detail.rename(columns={"events": "Events", "unique_sessions": "Unique Sessions", "unique_v2_visitors": "Unique Visitors"})[["Surface", "Interaction", "Feature", "Value", "Events", "Unique Sessions", "Unique Visitors", "Latest Event"]], hide_index=True, use_container_width=True)


def _render_dashboard(data: dict, product_data: pd.DataFrame | None = None) -> None:
    range_key = data["range_key"]
    st.title("Visitor Analytics")
    st.caption(f"Internal / read-only · Time zone: {DISPLAY_TIMEZONE} · Unique visitor metrics use V2 browser identity only.")
    if range_key == "ALL":
        st.caption("ALL: New = 1 recorded V2 session · Returning = 2+ recorded V2 sessions")

    kpis = data["kpis"]
    v2 = data["v2"]
    cards = st.columns(5)
    cards[0].metric("Sessions", f"{kpis['sessions']:,}")
    cards[1].metric("Unique Visitors", f"{int(v2.get('stable_visitors') or 0):,}", help="Unique browser profiles detected by the current V2 visitor identity system.")
    cards[2].metric("New", f"{int(v2.get('new_visitors') or 0):,}", help="V2 profiles first observed in the selected period.")
    cards[3].metric("Returning", f"{int(v2.get('returning_visitors') or 0):,}", help="V2 profiles observed before the selected period.")
    cards[4].metric("Latest Visit", _fmt_time(kpis["latest_visit"]), help="Latest recorded session start; not live presence.")

    st.subheader("Traffic Over Time")
    trend = data["trend"]
    if trend.empty:
        st.info("No visits in this period.")
    else:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_bar(x=trend["bucket"], y=trend["sessions"], name="Sessions", marker_color="#ff003a", hovertemplate="Sessions: %{y}<extra></extra>", secondary_y=False)
        fig.add_scatter(x=trend["bucket"], y=trend["stable_visitors"], name="Unique Visitors", mode="lines+markers", line=dict(color="#62d9ff"), hovertemplate="Unique Visitors: %{y}<extra></extra>", secondary_y=True)
        fig.update_yaxes(title_text="Sessions", secondary_y=False)
        fig.update_yaxes(title_text="Unique Visitors", secondary_y=True)
        st.plotly_chart(_chart_layout(fig), use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("New vs Returning")
        values = [int(v2.get("new_visitors") or 0), int(v2.get("returning_visitors") or 0)]
        if sum(values) == 0:
            st.info("No unique V2 visitor data in this period.")
        else:
            fig = go.Figure(go.Bar(x=values, y=["New", "Returning"], orientation="h", marker_color=["#62d9ff", "#ff003a"], text=values, textposition="auto"))
            st.plotly_chart(_chart_layout(fig, showlegend=False), use_container_width=True)
    with right:
        st.subheader("Initial Analytics Surface")
        st.caption("One initial analytics surface per recorded Streamlit session; later navigation is not represented here.")
        modes = data["modes"].copy()
        modes["label"] = modes["mode"].map(MODE_LABELS).fillna(modes["mode"])
        if modes.empty:
            st.info("No visits in this period.")
        else:
            fig = go.Figure(go.Bar(x=modes["sessions"], y=modes["label"], orientation="h", marker_color="#ff003a", text=modes["sessions"], textposition="auto"))
            st.plotly_chart(_chart_layout(fig, showlegend=False), use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Acquisition Sources")
        acquisition = data["acquisition"]
        if acquisition.empty:
            st.info("No acquisition data in this period.")
        else:
            fig = go.Figure(go.Bar(x=acquisition["source"], y=acquisition["sessions"], marker_color="#ff003a", text=acquisition["sessions"], textposition="auto"))
            st.plotly_chart(_chart_layout(fig, showlegend=False), use_container_width=True)
    with right:
        st.subheader("Campaign / Post Performance")
        posts = data["posts"]
        if posts.empty:
            st.info("No attributed campaign traffic in this period.")
        else:
            fig = go.Figure(go.Bar(x=posts["sessions"], y=posts["post"], orientation="h", marker_color="#ff003a", text=posts["sessions"], textposition="auto"))
            st.plotly_chart(_chart_layout(fig, showlegend=False), use_container_width=True)

    st.subheader("Post Performance")
    posts = data["posts"]
    if posts.empty:
        st.info("No attributed campaign traffic in this period.")
    else:
        display = posts.rename(columns={"post": "Post", "sessions": "Sessions", "stable_visitors": "Unique Visitors", "returning": "Returning", "item": "Item", "market": "Market", "top_items": "Top Items", "trader": "Top Traders", "latest_visit": "Latest Visit"})
        display["Latest Visit"] = display["Latest Visit"].map(_fmt_time)
        st.dataframe(display[["Post", "Sessions", "Unique Visitors", "Returning", "Item", "Market", "Top Items", "Top Traders", "Latest Visit"]], hide_index=True, use_container_width=True)

    _render_product_usage(product_data)

    st.subheader("Item Interest")
    st.caption("Based on recorded item contexts from analytics sessions; this is not a complete item-view clickstream.")
    items = data.get("item_interest", pd.DataFrame())
    if items.empty:
        st.info("No recorded item contexts in this period.")
    else:
        chart_items = items.head(15).sort_values(["sessions", "item_key"], ascending=[True, False])
        fig = go.Figure(go.Bar(
            x=chart_items["sessions"], y=chart_items["item_key"], orientation="h",
            marker_color="#ff003a", text=chart_items["sessions"], textposition="auto",
            hovertemplate="Recorded Item: %{y}<br>Sessions: %{x}<extra></extra>"))
        st.plotly_chart(_chart_layout(fig, showlegend=False), use_container_width=True)
        item_display = items.rename(columns={
            "item_key": "Recorded Item", "sessions": "Sessions",
            "unique_v2_visitors": "Unique Visitors", "returning_v2_visitors": "Returning",
            "latest_visit": "Latest Visit",
        }).copy()
        item_display["Latest Visit"] = item_display["Latest Visit"].map(_fmt_time)
        st.dataframe(item_display[["Recorded Item", "Sessions", "Unique Visitors", "Returning", "Latest Visit"]], hide_index=True, use_container_width=True)
        missing = int(data.get("item_missing", 0) or 0)
        if missing:
            st.caption(f"{missing:,} item sessions have no recorded item context.")

    st.subheader("Item Activity")
    st.caption("Explicit item selections from event tracking; automatic initial contexts are excluded from the primary ranking.")
    activity = data.get("item_activity", pd.DataFrame())
    if activity.empty:
        st.info("No item activity events in this period.")
    else:
        chart_activity = activity.head(15).sort_values(["selections", "item_key"], ascending=[True, False])
        fig = go.Figure(go.Bar(
            x=chart_activity["selections"], y=chart_activity["item_key"], orientation="h",
            marker_color="#62d9ff", text=chart_activity["selections"], textposition="auto",
            hovertemplate="Recorded Item: %{y}<br>Selections: %{x}<extra></extra>"))
        st.plotly_chart(_chart_layout(fig, showlegend=False), use_container_width=True)
        activity_display = activity.rename(columns={
            "item_key": "Recorded Item", "selections": "Selections",
            "unique_sessions": "Unique Sessions", "unique_v2_visitors": "Unique Visitors",
            "latest_selection": "Latest Selection",
        }).copy()
        activity_display["Latest Selection"] = activity_display["Latest Selection"].map(_fmt_time)
        st.dataframe(activity_display[["Recorded Item", "Selections", "Unique Sessions", "Unique Visitors", "Latest Selection"]], hide_index=True, use_container_width=True)
    initial_count = int(data.get("initial_default_events", 0) or 0)
    if initial_count:
        st.caption(f"Automatic initial contexts: {initial_count:,}.")

    _render_visitor_drilldown(range_key)


def _render_visitor_drilldown(range_key: str) -> None:
    """Render transient-alias V2 drilldown; no profile key is user-visible."""
    with st.expander("Visitor Drilldown", expanded=False):
        st.caption("Shows recorded session contexts, not every page or item viewed.")
        try:
            summaries = load_visitor_summaries(range_key)
        except Exception:
            st.info("Visitor drilldown is temporarily unavailable.")
            return
        if summaries.empty:
            st.info("No V2 visitor history in this period.")
            return
        summaries = summaries.reset_index(drop=True).copy()
        summaries["alias"] = [f"Visitor #{idx:03d}" for idx in range(1, len(summaries) + 1)]
        options = [f"{row.alias} · {int(row.sessions):,} sessions" for row in summaries.itertuples()]
        selected_label = st.selectbox("Visitor", options, key="visitor_dashboard_selector")
        selected_index = options.index(selected_label)
        selected = summaries.iloc[selected_index]
        profile_key = selected["profile_key"]
        cols = st.columns(4)
        cols[0].metric("Sessions", f"{int(selected['sessions']):,}")
        cols[1].metric("Recorded Items", f"{int(selected['recorded_items']):,}")
        cols[2].metric("First Seen", _fmt_time(selected["first_seen"]))
        cols[3].metric("Latest Visit", _fmt_time(selected["latest_visit"]))
        try:
            timeline = load_visitor_timeline(profile_key)
        except Exception:
            st.info("Visitor timeline is temporarily unavailable.")
            return
        if timeline.empty:
            st.info("No recorded V2 session contexts for this visitor.")
            return
        timeline = timeline.rename(columns={
            "started_at_utc": "Time", "mode": "Mode", "recorded_item": "Recorded Item",
            "acquisition": "Acquisition", "campaign": "Campaign", "post": "Post",
        }).copy()
        timeline["Time"] = timeline["Time"].map(_fmt_time)
        timeline["Mode"] = timeline["Mode"].map(MODE_LABELS).fillna(timeline["Mode"])
        st.dataframe(timeline[["Time", "Mode", "Recorded Item", "Acquisition", "Campaign", "Post"]].fillna(""), hide_index=True, use_container_width=True)
        st.markdown("**Item Activity**")
        try:
            activity = load_visitor_item_activity(profile_key)
        except Exception:
            st.info("Item activity is temporarily unavailable.")
            return
        if activity.empty:
            st.info("No item activity events for this visitor.")
        else:
            event_labels = {
                "initial_default": "Automatic Initial Context",
                "initial_explicit": "Initial Item Link",
                "item_select": "Item Selection",
            }
            activity = activity.rename(columns={
                "occurred_at_utc": "Time", "event_type": "Event",
                "item_key": "Recorded Item", "campaign": "Campaign", "post": "Post",
            }).copy()
            activity["Time"] = activity["Time"].map(_fmt_time)
            activity["Event"] = activity["Event"].map(event_labels).fillna(activity["Event"])
            st.dataframe(activity[["Time", "Event", "Recorded Item", "Campaign", "Post"]].fillna(""), hide_index=True, use_container_width=True)


def _clear_dashboard_cache() -> None:
    """Clear only the cached aggregate loader owned by this dashboard."""
    _cached_dashboard_data.clear()
    _cached_product_event_data.clear()


def render_visitor_dashboard() -> None:
    """Render the protected dashboard without invoking visitor collection."""
    if not st.session_state.get(AUTH_KEY, False):
        _render_login()
        return

    toolbar = st.columns([4, 1])
    with toolbar[0]:
        selected = st.radio("Period", RANGE_LABELS, index=0, horizontal=True, label_visibility="collapsed")
    with toolbar[1]:
        refresh = st.button("Refresh", use_container_width=True)
    if refresh:
        _clear_dashboard_cache()
        st.rerun()
    try:
        data = _cached_dashboard_data(selected)
    except Exception:
        st.error("Visitor analytics data is temporarily unavailable.")
        return
    try:
        product_data = _cached_product_event_data(selected)
    except Exception:
        product_data = None
    _render_dashboard(data, product_data)


@st.cache_data(ttl=120, show_spinner=False)
def _cached_dashboard_data(range_key: str) -> dict:
    return load_dashboard_data(range_key)


@st.cache_data(ttl=120, show_spinner=False)
def _cached_product_event_data(range_key: str) -> pd.DataFrame:
    return load_product_event_aggregates(range_key)
