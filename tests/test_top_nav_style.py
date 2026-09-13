from pathlib import Path


SOURCE = (Path(__file__).parents[1] / "streamlit_opensea_sales/ui/mode_switch.py").read_text(encoding="utf-8")


def test_navigation_geometry_is_unchanged():
    for token in ("gap:8px", "min-height:36px", "margin:0 0 8px 0", "height:34px", "padding:0 14px", "width:190px", "top:calc(100% + 6px)"):
        assert token in SOURCE
    for token in ("gap:6px", "min-height:32px", "height:30px", "padding-left:8px", "padding-right:8px"):
        assert token in SOURCE


def test_top_level_ghost_states_are_neutral_and_stationary():
    assert "background:transparent" in SOURCE
    assert "border:1px solid transparent" in SOURCE
    assert "color:#9EA3AA" in SOURCE
    assert "a.otg-top-nav-control:link" in SOURCE and "a.otg-top-nav-control:visited" in SOURCE
    assert "color:#F5F7FA!important" in SOURCE
    assert "background:rgba(255,255,255,.045)" in SOURCE
    assert "transform:none" in SOURCE
    assert "color:#FFFFFF!important" in SOURCE
    assert "background:rgba(255,255,255,.065)" in SOURCE
    assert "outline:none" in SOURCE
    assert "text-decoration:none!important" in SOURCE
    assert "#FF003A" not in SOURCE
    assert "rgba(255,0,58" not in SOURCE


def test_dropdown_is_neutral_without_accent_bars():
    assert "background:#070809" in SOURCE
    assert "border:none" in SOURCE
    assert "0 12px 30px rgba(0,0,0,.62)" in SOURCE
    assert "color:#A7ACB3!important" in SOURCE
    assert "rgba(255,255,255,.055)" in SOURCE
    assert "rgba(255,255,255,.080)" in SOURCE
    assert "padding-left:10px" in SOURCE


def test_login_remains_disabled_and_neutral():
    assert 'aria-disabled="true"' in SOURCE
    assert 'title="Coming soon"' in SOURCE
    assert ".otg-nav-login{{background:transparent" in SOURCE
    assert "color:#5F646C" in SOURCE


def test_navigation_functionality_and_structure_are_preserved():
    for token in ('<nav class="otg-top-nav"', '<details class="otg-nav-analytics">', 'summary class="otg-top-nav-control', 'href="/?mode=item"', 'href="/?mode=market"', 'href="/?mode=top_items"', 'href="/?mode=top_traders"', 'href="/?mode=roadmap"', 'href="{feedback_href}"'):
        assert token in SOURCE
    assert "otg-nav-analytics>summary::-webkit-details-marker" in SOURCE
