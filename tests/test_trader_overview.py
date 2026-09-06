import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "streamlit_opensea_sales"))

from ui.trader_overview import (  # noqa: E402
    EARNED_COLOR,
    INVESTED_COLOR,
    SOLD_COLOR,
    PANDL_MIN_COVERAGE_PCT,
    PANDL_MIN_MATCHED_SALES,
    leaderboard_rows,
    paginate_traders,
    resolve_wallet_search,
    short_wallet,
    trader_is_pnl_eligible,
)

TRADER_SOURCE = (Path(__file__).parents[1] / "streamlit_opensea_sales" / "ui" / "trader_overview.py").read_text(encoding="utf-8")


def row(wallet, trades=10, volume=100, matched=3, coverage=75, pnl=10, roi=.1, win=.5, supported=True):
    return {"wallet": wallet, "trade_count": trades, "total_volume_usd": volume,
            "buy_volume_usd": volume, "sell_volume_usd": volume,
            "total_volume_gun": volume / 10, "matched_realized_sales": matched,
            "pnl_coverage_sell_pct": coverage, "realized_pnl_usd": pnl,
            "realized_pnl_gun": pnl / 10, "roi": roi, "win_rate": win,
            "pnl_supported": supported}


def test_calibrated_eligibility_contract():
    assert PANDL_MIN_MATCHED_SALES == 3
    assert PANDL_MIN_COVERAGE_PCT == 50.0
    assert trader_is_pnl_eligible(row("a"))
    assert not trader_is_pnl_eligible(row("b", matched=2))
    assert not trader_is_pnl_eligible(row("c", coverage=49))


def test_public_money_metric_labels_and_colors_are_explicit():
    assert EARNED_COLOR == "#67C77A"
    assert INVESTED_COLOR == "#D8C3A5"
    assert SOLD_COLOR == "#FFD400"


def test_pnl_rankings_exclude_ineligible_but_volume_does_not():
    rows = [row("0xB", pnl=20), row("0xA", pnl=100, matched=1), row("0xC", volume=300, matched=0)]
    earned = leaderboard_rows(rows, "EARNED")
    assert [r["wallet"] for r in earned] == ["0xB", "0xA", "0xC"]
    assert earned[0]["rank"] == 1 and earned[1]["rank"] is None and earned[2]["rank"] is None
    assert [r["wallet"] for r in leaderboard_rows(rows, "INVESTED")] == ["0xC", "0xA", "0xB"]


def test_metric_sorting_and_deterministic_ties():
    rows = [row("0xB", trades=10), row("0xA", trades=10), row("0xC", trades=2)]
    assert [r["wallet"] for r in leaderboard_rows(rows, "TRADES")] == ["0xA", "0xB", "0xC"]
    assert [r["wallet"] for r in leaderboard_rows(rows, "ROI")] == ["0xA", "0xB", "0xC"]
    assert [r["wallet"] for r in leaderboard_rows(rows, "WIN RATE")] == ["0xA", "0xB", "0xC"]


def test_wallet_search_and_short_display_preserve_canonical_match():
    wallet = "0x" + "A" * 40
    rows = [row(wallet.lower())]
    assert resolve_wallet_search(rows, "  " + wallet + " ")["wallet"] == wallet.lower()
    assert resolve_wallet_search(rows, "0x" + "B" * 40) is None
    assert short_wallet(wallet.lower()) == "0xaaaa…aaaa"


def test_pagination_clamps_without_rendering_all_rows():
    rows = [row(f"0x{i:040x}") for i in range(51)]
    visible, page, pages = paginate_traders(rows, page=99, page_size=25)
    assert len(visible) == 1 and page == 3 and pages == 3


def test_trader_pagination_geometry_and_context_are_scoped_and_deterministic():
    assert "color:var(--otg-text-secondary)" in TRADER_SOURCE
    assert "trader-ranking-context {{ font-size:11px; color:var(--otg-text-tertiary)" not in TRADER_SOURCE
    assert "grid-template-columns:110px minmax(0,1fr) 110px" in TRADER_SOURCE
    assert '[data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child' in TRADER_SOURCE
    assert '[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child' in TRADER_SOURCE
    assert 'button {{ width:110px!important' in TRADER_SOURCE
    assert '.st-key-trader_pagination' in TRADER_SOURCE
