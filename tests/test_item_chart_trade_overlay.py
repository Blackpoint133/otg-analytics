from pathlib import Path

ROOT = Path(__file__).parents[1]
SOURCE = (ROOT / 'streamlit_opensea_sales' / 'ui' / 'item_chart_trade_overlay.py').read_text(encoding='utf-8')

def test_overlay_uses_component_and_lifecycle_contract():
    assert 'import streamlit.components.v1 as components' in SOURCE
    assert 'components.html' in SOURCE
    assert 'st.components.v1.html' not in SOURCE
    for value in ('__otgItemChartTradeState', 'item-sales-chart', 'otg_point_kind',
                  'nativePlotClickHandler', 'plotlyClickHandler', 'removeEventListener',
                  "removeListener('plotly_click'", 'closePinnedTooltip', 'closeTraderCard',
                  'closeAll', 'getBoundingClientRect', 'offsetWidth', 'offsetHeight',
                  '320px', 'calc(100vw - 24px)', "setAttribute('role','button')", 'tabIndex=0',
                  'Enter', 'Escape', 'textContent'):
        assert value in SOURCE
    assert 'removeAllListeners' not in SOURCE
    assert 'if(!tip)return' not in SOURCE

def test_overlay_positioning_and_bounded_polling_are_present():
    assert 'viewportWidth' in SOURCE or 'w.innerWidth' in SOURCE
    assert '16' in SOURCE
    assert 'n<30' in SOURCE
    assert 'setTimeout' in SOURCE
    assert 'boundPlot.on' in SOURCE
