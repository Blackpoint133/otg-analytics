from pathlib import Path

ROOT = Path(__file__).parents[1]
SOURCE = (ROOT / 'streamlit_opensea_sales' / 'ui' / 'item_chart_trade_overlay.py').read_text(encoding='utf-8')

def test_overlay_uses_component_and_lifecycle_contract():
    assert 'import streamlit.components.v1 as components' in SOURCE
    assert 'components.html' in SOURCE
    assert 'st.components.v1.html' not in SOURCE
    for value in ('__otgItemChartTradeState', 'item-sales-chart', 'otg_point_kind',
                  'nativePlotClickHandler', 'capturePointer', 'pointermove', 'pointerdown',
                  'clientX', 'clientY', 'resolvePointAnchor', 'plotlyClickHandler', 'removeEventListener',
                  "removeListener('plotly_click'", 'closePinnedTooltip', 'closeTraderCard',
                  'closeAll', 'getBoundingClientRect', 'offsetWidth', 'offsetHeight',
                  '320px', 'calc(100vw - 24px)', "setAttribute('role','button')", 'tabIndex=0',
                  'Enter', 'Escape', 'textContent'):
        assert value in SOURCE
    assert 'removeAllListeners' not in SOURCE
    assert 'if(!tip)return' not in SOURCE

def test_profile_card_portal_preserves_and_restores_existing_node():
    for value in ('function portalCard', 'function restoreCard', 'd.body.appendChild(c)',
                  '__otgOriginParent', '__otgOriginNextSibling', 'c.__otgPortaled=true',
                  'c.scrollTop=0', 'p.isConnected', 's.parentNode===p',
                  'p.insertBefore(c,s)', 'p.appendChild(c)', 'c.parentNode.removeChild(c)'):
        assert value in SOURCE
    assert 'cloneNode' not in SOURCE
    assert SOURCE.index('portalCard(c)') < SOURCE.index('c.scrollTop=0')
    assert SOURCE.index('c.hidden=false') < SOURCE.index('c.offsetWidth')
    assert 'z-index:2147483000' in SOURCE
    assert "addEventListener('pointermove',nativePlotClickHandler)" in SOURCE
    assert "addEventListener('pointerdown',nativePlotClickHandler)" in SOURCE
    assert "removeEventListener('pointermove',nativePlotClickHandler)" in SOURCE
    assert "removeEventListener('pointerdown',nativePlotClickHandler)" in SOURCE
    assert 'lastPointer?lastPointer.x:16' not in SOURCE
    assert 'lastPointer?lastPointer.y:16' not in SOURCE

def test_overlay_positioning_and_bounded_polling_are_present():
    assert 'viewportWidth' in SOURCE or 'w.innerWidth' in SOURCE
    assert '16' in SOURCE
    assert 'n<30' in SOURCE
    assert 'setTimeout' in SOURCE
    assert 'boundPlot.on' in SOURCE

def test_profile_visibility_and_four_direction_placement():
    assert 'c.hidden=false' in SOURCE
    assert SOURCE.index('c.hidden=false') < SOURCE.index('c.offsetWidth')
    assert "c.style.visibility='hidden'" in SOURCE
    assert "c.style.visibility='visible'" in SOURCE
    assert 'closeTraderCard' in SOURCE and 'closePinnedTooltip' in SOURCE
    for value in ('fitsRight', 'fitsLeft', 'fitsBelow', 'fitsAbove', 'tipRect.right+gap',
                  'tipRect.left-gap-cardWidth', 'tipRect.bottom+gap', 'tipRect.top-gap-cardHeight',
                  'reduce', 'w.innerWidth-cardWidth-margin', 'w.innerHeight-cardHeight-margin'):
        assert value in SOURCE

def test_unified_tooltip_and_profile_anchor_contract():
    assert '.item-chart-trade-tooltip' in SOURCE
    assert '.item-chart-pinned-trade-tooltip' not in SOURCE
    assert 'plotlyHoverHandler' in SOURCE and 'plotlyUnhoverHandler' in SOURCE
    assert 'activePointKey' in SOURCE and 'pinned' in SOURCE
    assert 'tip.getBoundingClientRect()' in SOURCE
    assert 's.getBoundingClientRect()' not in SOURCE
    assert 'removeListener' in SOURCE
    assert 'removeAllListeners' not in SOURCE

def test_anchor_resolution_is_shared_by_hover_and_click():
    assert SOURCE.count('resolvePointAnchor(boundPlot,p)') == 2
    assert 'plot.getBoundingClientRect()' in SOURCE
    assert 'xaxis.l2p' in SOURCE
    assert 'yaxis.l2p' in SOURCE
    assert 'r.left+r.width/2' in SOURCE
