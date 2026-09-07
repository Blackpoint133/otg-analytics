import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "streamlit_opensea_sales"))

from ui.trader_overview import (  # noqa: E402
    EARNED_COLOR,
    INVESTED_COLOR,
    SOLD_COLOR,
    consolidated_table_rows,
    PANDL_MIN_COVERAGE_PCT,
    PANDL_MIN_MATCHED_SALES,
    leaderboard_rows,
    paginate_traders,
    resolve_wallet_search,
    short_wallet,
    trader_is_pnl_eligible,
)
from opensea_account_profiles import fallback_name, get_profile, load_profile_snapshot, profile_name  # noqa: E402

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
    base_selector = '[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]'
    old_selector = '[data-testid="stHorizontalBlock"] > [data-testid="column"]'
    assert base_selector in TRADER_SOURCE
    assert f'{base_selector}:first-child' in TRADER_SOURCE
    assert f'{base_selector}:nth-child(2)' in TRADER_SOURCE
    assert f'{base_selector}:last-child' in TRADER_SOURCE
    assert old_selector not in TRADER_SOURCE
    assert 'max-width:none!important' in TRADER_SOURCE
    assert 'flex:none!important' in TRADER_SOURCE
    assert 'button {{ width:110px!important' in TRADER_SOURCE
    assert '.st-key-trader_pagination' in TRADER_SOURCE


def test_profile_loader_and_nonetwork_fallbacks(tmp_path):
    assert load_profile_snapshot(tmp_path / "missing.json")["profiles"] == {}
    wallet = "0x" + "A" * 40
    snapshot = {"schema_version": 1, "profiles": {wallet.lower(): {"wallet": wallet.lower(), "display_name": "Display", "username": "user"}}}
    path = tmp_path / "profiles.json"
    path.write_text(__import__("json").dumps(snapshot), encoding="utf-8")
    loaded = load_profile_snapshot(path)
    assert get_profile(wallet, loaded)["display_name"] == "Display"
    assert profile_name(wallet, get_profile(wallet, loaded)) == "Display"
    assert profile_name(wallet, {"username": "user"}) == "user"
    assert profile_name(wallet, {}) == fallback_name(wallet)
    assert fallback_name(wallet) == fallback_name(wallet)
    assert fallback_name(wallet) != fallback_name("0x" + "B" * 40)


def test_profile_table_contract_and_escaping(monkeypatch):
    import ui.trader_overview as overview
    captured = []
    monkeypatch.setattr(overview.st, "markdown", lambda value, **kwargs: captured.append(value))
    row_data = consolidated_table_rows([dict(row("0x" + "A" * 40), _profile={"display_name": "<Name>", "bio": "<b>bio</b>"}, _ranks={})])
    overview.render_trader_table(row_data)
    rendered = captured[0]
    assert "Profile" in rendered and "Wallet" not in rendered.split("<thead>", 1)[1].split("</thead>", 1)[0]
    assert "&lt;Name&gt;" in rendered
    assert "&lt;b&gt;bio&lt;/b&gt;" not in rendered or "bio" in rendered


def test_profile_fallback_avatar_is_embedded_once_for_25_rows(monkeypatch):
    import ui.trader_overview as overview
    captured = []
    monkeypatch.setattr(overview.st, "markdown", lambda value, **kwargs: captured.append(value))
    rows = []
    for index in range(25):
        rows.append(dict(row("0x" + f"{index:040x}"), _profile={}, _ranks={}))
    overview.render_trader_table(consolidated_table_rows(rows))
    rendered = captured[0]
    assert rendered.count("data:image/png;base64,") == 1
    assert "onerror" not in rendered
    assert len(rendered) > 0


def test_hover_rank_uses_em_dash_and_readable_metric_labels(monkeypatch):
    import ui.trader_overview as overview
    captured = []
    monkeypatch.setattr(overview.st, "markdown", lambda value, **kwargs: captured.append(value))
    ranks = {metric: {"rank": None, "value": "N/A"} for metric in overview.SORT_OPTIONS}
    ranks["INVESTED"] = {"rank": 4, "value": "4.00 USD"}
    overview.render_trader_table(consolidated_table_rows([dict(row("0x" + "A" * 40), _profile={}, _ranks=ranks)]))
    rendered = captured[0]
    assert "<span>ROI</span><b>—</b>" in rendered
    assert "<span>Win Rate</span><b>—</b>" in rendered
    assert "<span>Invested</span><b>#4</b>" in rendered
    assert "<span>ROI</span>" in rendered and "<span>Roi</span>" not in rendered
    assert "height:8px;bottom:-8px" in rendered
    assert "nth-child(-n+8) .trader-profile-card::before" in rendered
