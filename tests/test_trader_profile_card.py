import re
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
    assert "background-size:contain" in rendered
    assert "background-repeat:no-repeat" in rendered
    card = rendered.split('<div class="trader-profile-card">', 1)[1].split('</div></div></div>', 1)[0]
    assert 'trader-avatar-large" style=' in card
    assert "WALLET ADDRESS" in rendered
    assert "TRADING STATS" in rendered
    assert rendered.count("trader-profile-stat-icon trader-profile-stat-icon--") == 6
    assert "earned.png" not in rendered


def test_profile_card_copies_full_wallet_and_escapes_wallet(monkeypatch):
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
    assert "&lt;img" in rendered
    assert "&lt;script&gt;" not in rendered
    assert f'data-wallet="{wallet}"' in rendered
    assert wallet in rendered
    assert overview.short_wallet(wallet) != wallet
    source = Path(overview.__file__).read_text(encoding="utf-8")
    assert "parentWindow.navigator" in source
    assert "button.dataset.wallet" in source
    assert "execCommand('copy')" in source
    assert "const button=this" not in rendered
    assert "querySelector('.trader-wallet-copy-label')" in source
    assert "button.textContent" not in source
    assert "OpenSea profile" in rendered
    assert "COPIED" in source


def test_avatar_source_is_attached_to_expanded_avatar(monkeypatch):
    rendered = _rendered(monkeypatch)
    card = rendered.split('<div class="trader-profile-card">', 1)[1]
    large = card.split('class="trader-avatar trader-avatar-large"', 1)[1].split('></span>', 1)[0]
    small = rendered.split('class="trader-avatar trader-avatar-small"', 1)[1].split('></span>', 1)[0]
    assert "--trader-fallback-avatar" in large
    assert "--trader-fallback-avatar" in small


def test_opensea_link_is_under_identity_not_wallet(monkeypatch):
    rendered = _rendered(monkeypatch)
    identity = rendered.split('class="trader-profile-identity"', 1)[1]
    wallet = rendered.split('class="trader-wallet-row"', 1)[1]
    assert "OpenSea profile" in identity
    assert "OpenSea profile" not in wallet


def test_profile_description_is_removed_from_expanded_card(monkeypatch):
    rendered = _rendered(monkeypatch, {})
    assert "PROFILE DESCRIPTION" not in rendered
    assert "trader-profile-bio" not in rendered


def test_small_trigger_remains_circular_but_large_card_override_is_square():
    source = Path(overview.__file__).read_text(encoding="utf-8")
    assert ".trader-avatar-small" in source
    assert ".trader-profile-card .trader-avatar-large" in source
    assert "width:min(980px,calc(100vw - 40px))" in source
    assert "@media (max-width:768px)" in source


def test_trader_table_matches_top_items_density_contract():
    assert overview.TRADER_PAGE_SIZE == 20
    source = Path(overview.__file__).read_text(encoding="utf-8")
    assert "font-size:12px" in source
    assert "letter-spacing:.5px" in source
    assert ".trader-table th{{color:#FF003A;padding:10px 8px" in source
    assert ".trader-table td{{color:#FFF;padding:8px;text-align:left;font-size:11px" in source
    assert ".trader-avatar-small{{width:48px;height:48px}}" in source
    assert source.count("Rank") >= 1 and source.count("Matched Sales") >= 1


def test_trader_table_splits_image_and_trader_and_scopes_avatar_border(monkeypatch):
    rendered = _rendered(monkeypatch)
    header = rendered.split("<thead>", 1)[1].split("</thead>", 1)[0]
    assert re.findall(r"<th>([^<]+)</th>", header) == [
        "Rank", "Image", "Trader", "Earned", "Invested", "Sold", "Trades",
        "Purchases", "Sales", "ROI", "Win Rate", "Coverage", "Matched Sales",
    ]
    assert 'trader-image-profile-trigger' in rendered
    assert 'trader-profile-trigger' not in rendered
    assert 'trader-table-link' in rendered
    assert '.trader-table .trader-avatar-small{border:0;border-radius:0;overflow:visible;background-size:contain}' in rendered


def test_trader_header_uses_top_items_copy_and_typography_contract():
    source = Path(overview.__file__).read_text(encoding="utf-8")
    assert "<h3>TOP TRADERS</h3>" in source
    assert "SORTED BY {html.escape(sort_by)}" in source
    assert "ALL-TIME RANKING" in source
    assert "font-size:13px" in source
    assert "letter-spacing:.5px" in source
    assert "font-size:11px" in source
    assert "letter-spacing:.4px" in source


def test_metric_icon_mapping_and_cached_sources_are_complete():
    assert overview.METRIC_ICON_FILES == {
        "EARNED": "earned.png", "INVESTED": "invested.png", "SOLD": "sold.png",
        "TRADES": "trades.png", "ROI": "roi.png", "WIN RATE": "win_rate.png",
    }
    sources = overview.metric_icon_data_uris()
    assert all(value.startswith("data:image/png;base64,") for value in sources.values())
    assert overview.metric_icon_data_uris() is sources


def test_render_reuses_six_icon_definitions_for_many_rows(monkeypatch):
    captured = []
    monkeypatch.setattr(overview.st, "markdown", lambda value, **kwargs: captured.append(value))
    rows = []
    for index in range(25):
        rows.append({"wallet": f"0x{index:040x}", "_profile": {}, "_ranks": {}})
    overview.render_trader_table(overview.consolidated_table_rows(rows))
    rendered = "".join(captured)
    assert captured[1].count("data:image/png;base64,") == 6
    assert rendered.count("trader-profile-stat-icon--earned") == 27


def test_desktop_profile_content_bottom_anchor_contract_is_preserved():
    source = Path(overview.__file__).read_text(encoding="utf-8")
    assert "--trader-profile-square:350px" in source
    assert ".trader-profile-content { display:flex; flex-direction:column; }" in source
    assert ".trader-profile-stats-title { margin-top:auto; }" in source
    assert "grid-template-columns:var(--trader-profile-square) minmax(0,1fr)" in source
    assert "height:var(--trader-profile-square)" in source
    assert "@media (max-width:768px)" in source
    assert ".trader-profile-content { display:block; height:auto; max-height:none; }" in source


def test_trader_card_uses_direct_square_outer_frame():
    source = Path(overview.__file__).read_text(encoding="utf-8")
    assert ".trader-profile-card{{--trader-profile-square:350px;box-sizing:border-box;border:1px solid #303035;background:#050505;" in source
    assert "clip-path:polygon" not in source
    assert "padding:14px" in source
    assert "gap:16px;align-items:stretch" in source
    assert "inset:5px" not in source
    assert ".trader-profile-card-grid{{display:grid;position:relative;z-index:1;" in source
    assert ".trader-image-profile-trigger::after{{content:\"\";position:absolute;left:48px;top:0;width:16px" in source
    assert ".trader-image-profile-trigger .trader-profile-card{{left:64px;top:0;bottom:auto;pointer-events:auto}}" in source
    assert "css.replace(" not in source
    assert "spacing_override" not in source


def test_trader_stats_neutral_body_frame_remains_intact():
    source = Path(overview.__file__).read_text(encoding="utf-8")
    assert ".trader-profile-ranks{{border:1px solid #303035;margin-top:0;padding:0" in source
    assert ".trader-profile-ranks div{{display:grid;" in source
    assert "border:0;border-bottom:1px solid #303035" in source
    assert ".trader-profile-ranks div:last-child{{border-bottom:0}}" in source
    assert "border-right:1px solid #FF003A" in source


def test_trader_outer_shell_matches_item_square_corner_contract(monkeypatch):
    rendered = _rendered(monkeypatch)
    assert "--trader-profile-square:350px" in rendered
    assert "border:1px solid #303035" in rendered
    assert "padding:14px" in rendered
    assert "gap:16px" in rendered
    assert "background:#050505" in rendered
    assert "clip-path:polygon" not in rendered
    assert "inset:5px" not in rendered
    assert "inset:1px" not in rendered
    assert ".trader-profile-card::after{display:none}" in rendered
    assert ".trader-image-profile-trigger .trader-profile-card{left:64px;top:0;bottom:auto;pointer-events:auto}" in rendered
    assert ".trader-image-profile-trigger::after{content:\"\";position:absolute;left:48px;top:0;width:16px" in rendered
    assert ".trader-profile-card::before{content:\"\";position:absolute;left:0;right:0;height:8px;bottom:-8px}" in rendered


def test_lower_trader_rows_have_viewport_safe_upward_fallback():
    source = Path(overview.__file__).read_text(encoding="utf-8")
    assert ".trader-table tbody tr:nth-last-child(-n+6) .trader-profile-card{{top:auto;bottom:calc(100% + 8px)}}" in source
    assert ".trader-image-profile-trigger .trader-profile-card{{left:64px;top:0;bottom:auto;pointer-events:auto}}" in source
    assert ".trader-image-profile-trigger:hover .trader-profile-card" in source
    assert ".trader-image-profile-trigger:focus-within .trader-profile-card" in source
    assert ".trader-image-profile-trigger::after{{content:\"\";position:absolute;left:48px;top:0;width:16px;height:100%}}" in source
