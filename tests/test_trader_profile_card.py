import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "streamlit_opensea_sales"))

from ui import trader_overview as overview  # noqa: E402


def _rendered(monkeypatch, profile=None):
    captured = []
    monkeypatch.setattr(overview.st, "markdown", lambda value, **kwargs: captured.append(value))
    data = {
        "wallet": "0x" + "a" * 40,
        "_profile": {"display_name": "<Trader>", **(profile if profile is not None else {"bio": "<bio>"})}, "_ranks": {
            metric: {"rank": index + 1, "value": f"value-{index}"}
            for index, metric in enumerate(overview.SORT_OPTIONS)
        }, "_selected": False,
    }
    rows = overview.consolidated_table_rows([data])
    rows[0]["_profile"] = {"display_name": "<Trader>", **(profile if profile is not None else {"bio": "<bio>"})}
    overview.render_trader_table(rows)
    return captured[0]


def test_expanded_card_is_square_and_structured(monkeypatch):
    rendered = _rendered(monkeypatch)
    assert "trader-profile-card-grid" in rendered
    assert "trader-profile-avatar" in rendered
    assert ".trader-profile-card .trader-avatar-large" in rendered
    assert "aspect-ratio:1/1" in rendered
    assert "border-radius:0" in rendered
    assert "PROFILE DESCRIPTION" in rendered
    assert "WALLET ADDRESS" in rendered
    assert "TRADING STATS" in rendered
    assert rendered.count('<div><span>') == 6


def test_profile_card_escapes_content_and_copies_full_wallet(monkeypatch):
    wallet = "0x" + "b" * 40
    captured = []
    monkeypatch.setattr(overview.st, "markdown", lambda value, **kwargs: captured.append(value))
    rows = overview.consolidated_table_rows([{
        "wallet": wallet, "_profile_name": "<img src=x onerror=alert(1)>",
        "_profile": {"bio": "<script>alert(1)</script>"}, "_ranks": {}, "_selected": False,
    }])
    rows[0]["_profile"] = {"bio": "<script>alert(1)</script>"}
    rows[0]["Profile"] = "<img src=x onerror=alert(1)>"
    overview.render_trader_table(rows)
    rendered = captured[0]
    assert "&lt;img" in rendered and "&lt;script&gt;" in rendered
    assert f'data-wallet="{wallet}"' in rendered
    assert overview.short_wallet(wallet) in rendered
    assert "navigator.clipboard.writeText(this.dataset.wallet)" in rendered
    assert "COPIED" in rendered and "OpenSea profile" in rendered


def test_missing_bio_has_explicit_fallback(monkeypatch):
    rendered = _rendered(monkeypatch, {})
    assert "PROFILE DESCRIPTION" in rendered
    assert "NO DESCRIPTION" in rendered


def test_small_trigger_remains_circular_but_large_card_override_is_square():
    source = Path(overview.__file__).read_text(encoding="utf-8")
    assert ".trader-avatar-small" in source
    assert ".trader-profile-card .trader-avatar-large" in source
    assert "width:min(760px,calc(100vw - 32px))" in source
    assert "@media (max-width:768px)" in source
