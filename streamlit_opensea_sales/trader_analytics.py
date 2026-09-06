"""Offline, read-only trader analytics foundation.

This module deliberately contains no Streamlit, network, database, or write
operations.  It normalizes prepared OpenSea rows and aggregates only
observable marketplace activity.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

import pandas as pd


SCHEMA_VERSION = 1
SNAPSHOT_PATH = Path(__file__).parent / "data_opensea_sales" / "trader_analytics_snapshot.json"
_EVM_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def normalize_wallet(value: Any) -> Optional[str]:
    """Normalize a wallet without fuzzy matching or lossy transformations."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    value = str(value).strip()
    if not value:
        return None
    return value.lower() if _EVM_RE.fullmatch(value) else value


def _number(value: Any) -> Optional[float]:
    if value is None or pd.isna(value):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _timestamp(value: Any) -> Optional[pd.Timestamp]:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return None if pd.isna(parsed) else parsed


def _asset_identity(row: dict[str, Any]) -> Optional[str]:
    token_id = row.get("token_id")
    if pd.isna(token_id) if token_id is not None else True:
        return None
    try:
        token = str(int(float(token_id)))
    except (TypeError, ValueError):
        return None
    item_url = row.get("item_url")
    if item_url is None or pd.isna(item_url):
        return None
    parts = [part for part in urlparse(str(item_url)).path.split("/") if part]
    if len(parts) < 2:
        return None
    contract = parts[-2].strip().lower()
    return f"{contract}:{token}" if contract and token else None


def normalize_trade_events(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Return deterministic normalized events and ingestion diagnostics."""
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    diagnostics = {"input_rows": int(len(frame)), "duplicate_events": 0, "malformed_rows": 0, "self_trades": 0}
    for index, raw in frame.reset_index(drop=True).iterrows():
        row = raw.to_dict()
        timestamp = _timestamp(row.get("sale_date", row.get("parsed_date")))
        buyer = normalize_wallet(row.get("buyer"))
        seller = normalize_wallet(row.get("seller"))
        name = "" if row.get("name") is None or pd.isna(row.get("name")) else str(row.get("name")).strip()
        rarity = "" if row.get("rarity") is None or pd.isna(row.get("rarity")) else str(row.get("rarity")).strip()
        tx = None if row.get("transaction_hash") is None or pd.isna(row.get("transaction_hash")) else str(row.get("transaction_hash")).strip()
        raw_id = row.get("id")
        local_id = None if raw_id is None or pd.isna(raw_id) else str(raw_id).strip()
        asset_identity = _asset_identity(row)
        event_id = "|".join([
            tx or "",
            asset_identity or "",
            f"{timestamp}" if timestamp is not None else "",
            name,
            rarity,
            local_id or str(index),
        ])
        if event_id in seen:
            diagnostics["duplicate_events"] += 1
            continue
        if timestamp is None or not name or not buyer and not seller:
            diagnostics["malformed_rows"] += 1
            continue
        event = {
            "event_id": event_id,
            "timestamp": timestamp.isoformat(),
            "asset_identity": asset_identity,
            "item_identity": f"{name}|{rarity}",
            "item_name": name,
            "rarity": rarity,
            "buyer_wallet": buyer,
            "seller_wallet": seller,
            "price_gun": _number(row.get("price_gun")),
            "price_usd": _number(row.get("price_usd_at_sale")),
            "sale_type": str(row.get("type_token", "")) if not pd.isna(row.get("type_token")) else "",
            "transaction_hash": tx,
            "self_trade": bool(buyer and seller and buyer == seller),
        }
        seen.add(event_id)
        diagnostics["self_trades"] += int(event["self_trade"])
        events.append(event)
    events.sort(key=lambda event: (event["timestamp"], event["event_id"]))
    return events, diagnostics


def _metric_row(wallet: str) -> dict[str, Any]:
    return {
        "wallet": wallet, "buy_count": 0, "sell_count": 0, "trade_count": 0,
        "buy_volume_gun": 0.0, "sell_volume_gun": 0.0, "total_volume_gun": 0.0,
        "buy_volume_usd": 0.0, "sell_volume_usd": 0.0, "total_volume_usd": 0.0,
        "unique_items_traded": 0, "unique_assets_traded": 0, "unique_counterparties": 0,
        "active_days": 0, "first_trade_at": None, "last_trade_at": None,
        "matched_realized_sales": 0, "unmatched_sales": 0,
        "known_cost_basis_gun": 0.0, "known_sale_proceeds_gun": 0.0,
        "realized_pnl_gun": None, "known_cost_basis_usd": 0.0,
        "known_sale_proceeds_usd": 0.0, "realized_pnl_usd": None,
        "pnl_coverage_sell_pct": 0.0, "roi": None, "win_rate": None,
    }


def aggregate_trader_metrics(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate observable activity and conservative observable FIFO P&L."""
    events = sorted(events, key=lambda event: (event["timestamp"], event["event_id"]))
    rows: dict[str, dict[str, Any]] = {}
    sets = defaultdict(lambda: {"items": set(), "assets": set(), "counterparties": set(), "days": set()})
    lots: dict[tuple[str, str], deque[dict[str, Any]]] = defaultdict(deque)
    for event in events:
        buyer, seller = event.get("buyer_wallet"), event.get("seller_wallet")
        participants = {wallet for wallet in (buyer, seller) if wallet}
        for wallet in participants:
            row = rows.setdefault(wallet, _metric_row(wallet))
            row["trade_count"] += 1
            price_gun, price_usd = event.get("price_gun"), event.get("price_usd")
            if price_gun is not None: row["total_volume_gun"] += price_gun
            if price_usd is not None: row["total_volume_usd"] += price_usd
            sets[wallet]["items"].add(event["item_identity"])
            if event.get("asset_identity"): sets[wallet]["assets"].add(event["asset_identity"])
            sets[wallet]["counterparties"].update(participants - {wallet})
            sets[wallet]["days"].add(event["timestamp"][:10])
            row["first_trade_at"] = row["first_trade_at"] or event["timestamp"]
            row["last_trade_at"] = event["timestamp"]
        if buyer:
            row = rows[buyer]; row["buy_count"] += 1
            if price_gun is not None: row["buy_volume_gun"] += price_gun
            if price_usd is not None: row["buy_volume_usd"] += price_usd
        if seller:
            row = rows[seller]; row["sell_count"] += 1
            if price_gun is not None: row["sell_volume_gun"] += price_gun
            if price_usd is not None: row["sell_volume_usd"] += price_usd

        asset = event.get("asset_identity")
        price_gun, price_usd = event.get("price_gun"), event.get("price_usd")
        if event.get("self_trade") or not asset or price_gun is None:
            continue
        if seller:
            remaining = 1
            queue = lots[(seller, asset)]
            while remaining and queue:
                lot = queue[0]
                remaining -= 1
                row = rows[seller]
                row["matched_realized_sales"] += 1
                row["known_cost_basis_gun"] += lot["cost_gun"]
                row["known_sale_proceeds_gun"] += price_gun
                if lot["cost_usd"] is not None and price_usd is not None:
                    row["known_cost_basis_usd"] += lot["cost_usd"]
                    row["known_sale_proceeds_usd"] += price_usd
                if lot["cost_gun"] is not None:
                    row["realized_pnl_gun"] = (row["realized_pnl_gun"] or 0.0) + price_gun - lot["cost_gun"]
                if lot["cost_usd"] is not None and price_usd is not None:
                    row["realized_pnl_usd"] = (row["realized_pnl_usd"] or 0.0) + price_usd - lot["cost_usd"]
                if lot["cost_gun"] > 0: row["_wins"] = row.get("_wins", 0) + int(price_gun > lot["cost_gun"])
                if lot["cost_gun"] > 0: row["_roi_denominator"] = row.get("_roi_denominator", 0.0) + lot["cost_gun"]
                if lot["cost_gun"] > 0: queue.popleft()
            if remaining: rows[seller]["unmatched_sales"] += remaining
        if buyer:
            lots[(buyer, asset)].append({"cost_gun": price_gun, "cost_usd": price_usd, "event_id": event["event_id"]})

    for wallet, row in rows.items():
        row["unique_items_traded"] = len(sets[wallet]["items"])
        row["unique_assets_traded"] = len(sets[wallet]["assets"])
        row["unique_counterparties"] = len(sets[wallet]["counterparties"])
        row["active_days"] = len(sets[wallet]["days"])
        total_sells = row["matched_realized_sales"] + row["unmatched_sales"]
        row["pnl_coverage_sell_pct"] = (100.0 * row["matched_realized_sales"] / total_sells) if total_sells else 0.0
        if row["matched_realized_sales"]:
            cost = row.get("_roi_denominator", 0.0)
            row["roi"] = row["realized_pnl_gun"] / cost if cost else None
            row["win_rate"] = row.get("_wins", 0) / row["matched_realized_sales"]
        for key in ("_wins", "_roi_denominator"):
            row.pop(key, None)
    return [rows[wallet] for wallet in sorted(rows)]


def build_snapshot(events: list[dict[str, Any]], diagnostics: dict[str, int]) -> dict[str, Any]:
    timestamps = [event["timestamp"] for event in events]
    has_assets = bool(events) and all(event.get("asset_identity") for event in events)
    wallets = aggregate_trader_metrics(events)
    for wallet in wallets:
        wallet["pnl_supported"] = has_assets
    return {
        "schema_version": SCHEMA_VERSION, "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "source": "opensea", "event_count": len(events), "wallet_count": len(wallets),
        "date_min": min(timestamps) if timestamps else None, "date_max": max(timestamps) if timestamps else None,
        "identity_method": "item_url_contract_plus_token_id; item_identity_kept_separately",
        "pnl_method": "observable_asset_fifo_only", "pnl_supported": has_assets,
        "coverage": diagnostics, "wallets": wallets,
    }


def validate_snapshot(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported trader analytics schema")
    required = ("generated_at", "source", "event_count", "wallet_count", "identity_method", "pnl_method", "pnl_supported", "wallets")
    if any(key not in payload for key in required) or payload.get("source") != "opensea" or not isinstance(payload["wallets"], list):
        raise ValueError("invalid trader analytics snapshot")
    wallets = payload["wallets"]
    if any(not isinstance(row, dict) or not row.get("wallet") for row in wallets):
        raise ValueError("invalid trader wallet row")
    if len({row["wallet"] for row in wallets}) != len(wallets):
        raise ValueError("duplicate trader wallet")
    return payload


def get_snapshot_file_version(path: Path = SNAPSHOT_PATH) -> str:
    try:
        stat = path.stat()
    except OSError:
        return "missing"
    return f"{stat.st_mtime_ns}:{stat.st_size}"


@lru_cache(maxsize=8)
def _load_snapshot_cached(path_str: str, file_version: str) -> Optional[dict[str, Any]]:
    try:
        return validate_snapshot(json.loads(Path(path_str).read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def load_current_snapshot(path: Path = SNAPSHOT_PATH) -> Optional[dict[str, Any]]:
    return _load_snapshot_cached(str(path), get_snapshot_file_version(path))


def rank_trader_rows(rows: Iterable[dict[str, Any]], sort_by: str = "total_volume_gun", *, min_matched_sales: int = 1, min_coverage_pct: float = 0.0) -> list[dict[str, Any]]:
    """Prepare future leaderboard ordering without rendering a leaderboard."""
    allowed = {"total_volume_gun", "trade_count", "active_days", "realized_pnl_gun", "roi", "win_rate"}
    if sort_by not in allowed:
        raise ValueError(f"unsupported trader sort: {sort_by}")
    result = list(rows)
    if sort_by in {"realized_pnl_gun", "roi", "win_rate"}:
        result = [row for row in result if row.get("pnl_supported", True) and row.get("matched_realized_sales", 0) >= min_matched_sales and row.get("pnl_coverage_sell_pct", 0) >= min_coverage_pct and row.get(sort_by) is not None]
    return sorted(result, key=lambda row: (-(row.get(sort_by) or 0), row.get("wallet", "")))
