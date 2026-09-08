import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

APP = Path(__file__).parents[1] / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

from trader_analytics import (  # noqa: E402
    aggregate_trader_metrics,
    build_snapshot,
    load_current_snapshot,
    normalize_trade_events,
    normalize_wallet,
    rank_trader_rows,
    validate_snapshot,
)

_BUILDER_SPEC = importlib.util.spec_from_file_location(
    "build_trader_analytics",
    Path(__file__).parents[1] / "scripts" / "build_trader_analytics.py",
)
builder = importlib.util.module_from_spec(_BUILDER_SPEC)
_BUILDER_SPEC.loader.exec_module(builder)


def raw_frame():
    return pd.DataFrame([
        {"id": 1, "sale_date": "2026-01-01T00:00:00Z", "name": "A", "rarity": "Common", "token_id": 10, "item_url": "https://opensea.io/assets/gunzilla/0xABCDEF/10", "buyer": "0x" + "B" * 40, "seller": "0x" + "A" * 40, "price_gun": 10, "price_usd_at_sale": 1.0, "type_token": "GUN", "transaction_hash": "0xtx1"},
        {"id": 2, "sale_date": "2026-01-02T00:00:00Z", "name": "A", "rarity": "Common", "token_id": 10, "item_url": "https://opensea.io/assets/gunzilla/0xABCDEF/10", "buyer": "0x" + "C" * 40, "seller": " 0x" + "B" * 40 + " ", "price_gun": 14, "price_usd_at_sale": 2.0, "type_token": "WGUN", "transaction_hash": "0xtx2"},
        {"id": 3, "sale_date": "2026-01-02T00:00:00Z", "name": "B", "rarity": "Rare", "token_id": 11, "item_url": "https://opensea.io/assets/gunzilla/0xABCDEF/11", "buyer": "0x" + "D" * 40, "seller": "0x" + "D" * 40, "price_gun": 4, "price_usd_at_sale": 0.5, "type_token": "GUN", "transaction_hash": "0xtx3"},
    ])


def test_wallet_normalization_is_trimmed_and_case_canonical_only_for_evm():
    assert normalize_wallet(" 0x" + "A" * 40 + " ") == "0x" + "a" * 40
    assert normalize_wallet("Wallet-A") == "Wallet-A"
    assert normalize_wallet("  ") is None


def test_event_identity_asset_identity_and_self_trade():
    events, diag = normalize_trade_events(raw_frame())
    assert len(events) == 3
    assert events[0]["asset_identity"] == "0xabcdef:10"
    assert events[2]["self_trade"] is True
    assert diag["self_trades"] == 1


def test_duplicate_and_malformed_rows_are_safe():
    frame = pd.concat([raw_frame().iloc[[0]], raw_frame().iloc[[0]], raw_frame().iloc[[1]]], ignore_index=True)
    frame.loc[2, "sale_date"] = None
    events, diag = normalize_trade_events(frame)
    assert len(events) == 1
    assert diag["duplicate_events"] == 1
    assert diag["malformed_rows"] == 1


def test_activity_metrics_and_self_trade_count_once():
    events, _ = normalize_trade_events(raw_frame())
    rows = {row["wallet"]: row for row in aggregate_trader_metrics(events)}
    wallet_b = "0x" + "b" * 40
    wallet_d = "0x" + "d" * 40
    assert rows[wallet_b]["buy_count"] == 1 and rows[wallet_b]["sell_count"] == 1
    assert rows[wallet_b]["trade_count"] == 2
    assert rows[wallet_d]["trade_count"] == 1
    assert rows[wallet_d]["buy_count"] == rows[wallet_d]["sell_count"] == 1
    assert rows[wallet_d]["total_volume_gun"] == 4
    assert rows[wallet_b]["unique_counterparties"] == 2


def test_observable_fifo_pnl_uses_event_usd_and_does_not_reuse_acquisition():
    events, _ = normalize_trade_events(raw_frame())
    rows = {row["wallet"]: row for row in aggregate_trader_metrics(events)}
    wallet_b = "0x" + "b" * 40
    assert rows[wallet_b]["matched_realized_sales"] == 1
    assert rows[wallet_b]["unmatched_sales"] == 0
    assert rows[wallet_b]["realized_pnl_gun"] == 4
    assert rows[wallet_b]["realized_pnl_usd"] == 1.0
    assert rows[wallet_b]["pnl_coverage_sell_pct"] == 100.0
    assert rows[wallet_b]["roi"] == 0.4
    assert rows[wallet_b]["win_rate"] == 1.0


def test_currency_specific_realized_roi_and_win_rate_are_explicit():
    frame = raw_frame().iloc[[0, 1]].copy()
    events, _ = normalize_trade_events(frame)
    row = {item["wallet"]: item for item in aggregate_trader_metrics(events)}["0x" + "b" * 40]
    assert row["realized_pnl_gun"] == 4
    assert row["realized_pnl_usd"] == 1.0
    assert row["roi_gun"] == 0.4
    assert row["roi_usd"] == 1.0
    assert row["win_count_gun"] == 1 and row["win_count_usd"] == 1
    assert row["win_rate_gun"] == 1.0 and row["win_rate_usd"] == 1.0
    assert row["roi"] == row["roi_gun"]
    assert row["win_rate"] == row["win_rate_gun"]


def test_currency_specific_profitability_can_disagree():
    frame = raw_frame().iloc[[0, 1]].copy()
    frame.loc[0, "price_usd_at_sale"] = 10.0
    frame.loc[1, "price_usd_at_sale"] = 1.0
    events, _ = normalize_trade_events(frame)
    row = {item["wallet"]: item for item in aggregate_trader_metrics(events)}["0x" + "b" * 40]
    assert row["roi_gun"] > 0
    assert row["roi_usd"] < 0
    assert row["win_rate_gun"] == 1.0
    assert row["win_rate_usd"] == 0.0


def test_unmatched_sale_is_not_profit():
    events, _ = normalize_trade_events(raw_frame().iloc[[1]])
    row = aggregate_trader_metrics(events)[0]
    assert row["sell_volume_gun"] == 14
    assert row["unmatched_sales"] == 1
    assert row["realized_pnl_gun"] is None
    assert row["roi"] is None


def test_snapshot_schema_and_deterministic_ranking():
    events, diag = normalize_trade_events(raw_frame())
    payload = build_snapshot(events, diag)
    assert validate_snapshot(payload)["wallet_count"] == 4
    ranked = rank_trader_rows(payload["wallets"], "trade_count")
    assert ranked[0]["trade_count"] == 2
    assert ranked[0]["wallet"] < ranked[1]["wallet"] or ranked[0]["trade_count"] > ranked[1]["trade_count"]


def test_invalid_snapshot_and_missing_snapshot_are_safe(tmp_path):
    path = tmp_path / "trader.json"
    path.write_text("not-json", encoding="utf-8")
    assert load_current_snapshot(path) is None
    path.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    assert load_current_snapshot(path) is None


def test_pnl_ranking_requires_explicit_eligibility():
    rows = [{"wallet": "b", "realized_pnl_gun": 10, "matched_realized_sales": 1, "pnl_coverage_sell_pct": 100, "pnl_supported": True}, {"wallet": "a", "realized_pnl_gun": 20, "matched_realized_sales": 0, "pnl_coverage_sell_pct": 0, "pnl_supported": True}]
    ranked = rank_trader_rows(rows, "realized_pnl_gun")
    assert [row["wallet"] for row in ranked] == ["b"]


def test_snapshot_publication_is_atomic(tmp_path):
    output = tmp_path / "snapshot.json"
    output.write_text('{"old": true}', encoding="utf-8")
    builder.publish_atomic({"schema_version": 1}, output)
    assert json.loads(output.read_text(encoding="utf-8")) == {"schema_version": 1}
    assert not list(tmp_path.glob(".snapshot.json.*.tmp"))
