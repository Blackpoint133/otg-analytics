import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "streamlit_opensea_sales"))

from ui.trader_overview import (  # noqa: E402
    PANDL_MIN_COVERAGE_PCT,
    PANDL_MIN_MATCHED_SALES,
    leaderboard_rows,
    paginate_traders,
    resolve_wallet_search,
    short_wallet,
    trader_is_pnl_eligible,
)


def row(wallet, trades=10, volume=100, matched=3, coverage=75, pnl=10, roi=.1, win=.5, supported=True):
    return {"wallet": wallet, "trade_count": trades, "total_volume_usd": volume,
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


def test_pnl_rankings_exclude_ineligible_but_volume_does_not():
    rows = [row("0xB", pnl=20), row("0xA", pnl=100, matched=1), row("0xC", volume=300, matched=0)]
    assert [r["wallet"] for r in leaderboard_rows(rows, "Observed P&L")] == ["0xB"]
    assert [r["wallet"] for r in leaderboard_rows(rows, "Volume")] == ["0xC", "0xA", "0xB"]


def test_metric_sorting_and_deterministic_ties():
    rows = [row("0xB", trades=10), row("0xA", trades=10), row("0xC", trades=2)]
    assert [r["wallet"] for r in leaderboard_rows(rows, "Trades")] == ["0xA", "0xB", "0xC"]
    assert [r["wallet"] for r in leaderboard_rows(rows, "ROI")] == ["0xA", "0xB", "0xC"]
    assert [r["wallet"] for r in leaderboard_rows(rows, "Win Rate")] == ["0xA", "0xB", "0xC"]


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
