from pathlib import Path


ROOT = Path(__file__).parents[1]
APP = ROOT / "streamlit_opensea_sales"
STATUS_BAR = APP / "ui" / "status_bar.py"
APP_SHELL = APP / "app_opensea_sales.py"
FOOTER = APP / "ui" / "footer.py"
MODE_SWITCH = APP / "ui" / "mode_switch.py"
WALLET = "0x956cff3a596AD30D6A767DfFc3F70CDE97CD2667"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_global_status_bar_is_fixed_and_mounted_before_public_early_routes():
    source = _source(STATUS_BAR)
    shell = _source(APP_SHELL)
    assert ".otg-global-status-bar{{position:fixed" in source
    assert "bottom:0" in source
    assert "height:var(--otg-status-bar-height)" in source
    assert "OTG ANALYTICS //" in source
    assert "BETA" in source
    mount = shell.index("render_global_status_bar()")
    assert mount < shell.index('if requested_mode == "feedback":')
    assert mount < shell.index('if requested_mode == "ecosystem":')
    assert 'if requested_mode != "internal_analytics":' in shell


def test_donation_wallet_copy_contract_is_exact_and_accessible():
    source = _source(STATUS_BAR)
    assert f'EVM_DONATION_WALLET = "{WALLET}"' in source
    assert 'data-wallet="{EVM_DONATION_WALLET}"' in source
    assert 'aria-label="Copy EVM donation wallet address"' in source
    assert "clipboard.writeText" in source
    assert "legacyCopy(wallet)" in source
    assert "'COPIED'" in source
    assert "1300" in source
    assert "EVM ADDRESS" in source
    assert "Ethereum" not in source
    assert "Polygon" not in source


def test_status_bar_tracks_sidebar_and_resets_for_absent_collapsed_or_mobile_sidebar():
    source = _source(STATUS_BAR)
    assert "sidebar.getBoundingClientRect()" in source
    assert "rect.width > 2 && rect.right > 0" in source
    assert "offset = 0" in source
    assert "--otg-status-bar-left" in source
    assert "ResizeObserver" in source
    assert "MutationObserver" in source
    assert "style.display !== 'none'" in source
    assert "style.visibility !== 'hidden'" in source
    assert "win.innerWidth > 768" in source
    assert "left:0!important" in source


def test_mobile_status_bar_is_compact_one_line_without_overflow():
    source = _source(STATUS_BAR)
    assert "@media(max-width:768px)" in source
    assert "0x956c&hellip;2667" in source
    assert '<span class="otg-status-mobile">EVM</span>' in source
    assert "white-space:nowrap" in source
    assert "min-width:0" in source
    assert "overflow-x:auto" not in source
    assert "@media(max-width:380px)" in source


def test_fixed_bar_reserves_main_content_space_without_replacing_sidebar_footer():
    source = _source(STATUS_BAR)
    footer = _source(FOOTER)
    shell = _source(APP_SHELL)
    assert '[data-testid="stMainBlockContainer"]' in source
    assert "padding-bottom:calc(var(--otg-status-bar-height) + 12px)!important" in source
    assert "def render_sidebar_footer" in footer
    assert "Provided by" in footer
    assert "Developed by" in footer
    assert "render_sidebar_footer()" in shell


def test_top_navigation_source_is_not_coupled_to_status_bar():
    nav = _source(MODE_SWITCH)
    assert "otg-global-status-bar" not in nav
    assert ".otg-nav-analytics,.otg-nav-analytics>summary{{width:auto;flex:0 0 auto}}" in nav
    assert ".otg-nav-dropdown{{width:176px;max-width:calc(100vw - 24px)}}" in nav


def test_static_roadmap_has_the_same_global_status_and_wallet_contract():
    roadmap = _source(ROOT / "roadmap" / "otg_analytics_roadmap_english_cta.html")
    assert 'class="otg-global-status-bar"' in roadmap
    assert "OTG ANALYTICS //" in roadmap
    assert WALLET in roadmap
    assert 'aria-label="Copy EVM donation wallet address"' in roadmap
    assert "navigator.clipboard.writeText" in roadmap
    assert "padding-bottom:32px" in roadmap
