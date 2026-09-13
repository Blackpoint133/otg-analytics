"""Top-right analytics navigation."""

from typing import Literal
from urllib.parse import urlencode
import streamlit as st


def render_mode_switch() -> Literal['item', 'market', 'top_items', 'trader', 'feedback']:
    raw_mode = st.query_params.get('mode', 'item')
    if isinstance(raw_mode, list):
        raw_mode = raw_mode[0]
    current_mode = 'trader' if raw_mode in ('trader', 'top_traders') else raw_mode
    if current_mode not in ('item', 'market', 'top_items', 'trader', 'feedback'):
        current_mode = 'item'
    active = {key: ('active' if current_mode == mode else '') for key, mode in {
        'item': 'item', 'market': 'market', 'top_items': 'top_items', 'top_traders': 'trader'
    }.items()}
    source_mode = 'trader' if current_mode == 'trader' else current_mode
    if current_mode == 'feedback':
        source_mode = st.query_params.get('source', 'unknown')
        if isinstance(source_mode, list):
            source_mode = source_mode[0] if source_mode else 'unknown'
        if source_mode not in ('item', 'market', 'top_items', 'trader'):
            source_mode = 'unknown'
    feedback_params = {'mode': 'feedback', 'source': source_mode}
    if source_mode == 'item':
        item_key = st.query_params.get('item')
        if isinstance(item_key, list):
            item_key = item_key[0] if item_key else None
        if item_key:
            feedback_params['item'] = str(item_key)
    feedback_href = '/?' + urlencode(feedback_params)
    feedback_active = 'active' if current_mode == 'feedback' else ''
    analytics_active = current_mode in ('item', 'market', 'top_items', 'trader')
    st.markdown(f'''<style>
.otg-top-nav{{display:flex;align-items:center;justify-content:flex-end;gap:8px;width:100%;min-height:36px;margin:0 0 8px 0;padding:0;position:relative;z-index:50}}
.otg-top-nav-control{{height:34px;box-sizing:border-box;display:inline-flex;align-items:center;justify-content:center;padding:0 14px;background:transparent;border:1px solid transparent;border-radius:0;font-family:'PP Supply Sans','Space Mono',monospace,sans-serif;font-size:11px;font-weight:700;line-height:1;letter-spacing:.8px;text-transform:uppercase;white-space:nowrap;color:#AEB3BA;text-decoration:none!important;text-shadow:none;transform:none;position:relative;cursor:pointer;transition:color 180ms cubic-bezier(.2,.7,.2,1),background-color 180ms cubic-bezier(.2,.7,.2,1),text-shadow 180ms cubic-bezier(.2,.7,.2,1),opacity 180ms cubic-bezier(.2,.7,.2,1)}}
.otg-top-nav-control:not(.otg-nav-disabled)::after{{content:'';position:absolute;left:50%;bottom:2px;width:44%;height:1px;background:#FF003A;pointer-events:none;opacity:0;transform:translateX(-50%) scaleX(0);transform-origin:center center;transition:opacity 190ms cubic-bezier(.2,.7,.2,1),transform 190ms cubic-bezier(.2,.7,.2,1)}}
a.otg-top-nav-control:link,a.otg-top-nav-control:visited{{color:#AEB3BA!important;text-decoration:none!important}}
.otg-top-nav-control:hover{{color:#FFFFFF!important;background:rgba(255,255,255,.032);border-color:transparent;text-decoration:none!important;transform:none;text-shadow:0 0 6px rgba(255,255,255,.055)}}.otg-top-nav-control:not(.otg-nav-disabled):hover::after,.otg-top-nav-control:not(.otg-nav-disabled):focus-visible::after{{opacity:.88;transform:translateX(-50%) scaleX(1)}}
.otg-top-nav-control:focus-visible,.otg-nav-dropdown a:focus-visible{{outline:none;color:#FFFFFF!important;background:rgba(255,255,255,.045);text-decoration:none!important;text-shadow:0 0 6px rgba(255,255,255,.055)}}
.otg-nav-analytics{{position:relative}}.otg-nav-analytics>summary{{list-style:none}}.otg-nav-analytics>summary::-webkit-details-marker{{display:none}}.otg-top-nav-control.active,.otg-nav-analytics>summary.active{{color:#FFFFFF!important;border-color:transparent;border-bottom:1px solid transparent;background:rgba(255,255,255,.025);text-decoration:none!important;text-shadow:0 0 5px rgba(255,255,255,.045)}}.otg-top-nav-control.active:not(.otg-nav-disabled)::after,.otg-nav-analytics>summary.active:not(.otg-nav-disabled)::after{{opacity:.72;transform:translateX(-50%) scaleX(1)}}.otg-top-nav-control.active:not(.otg-nav-disabled):hover::after{{opacity:.92}}
.otg-nav-chevron{{margin-left:7px;font-size:9px;color:currentColor;transition:transform 140ms ease}}.otg-nav-chevron::after{{content:'⌄'}}.otg-nav-analytics[open] .otg-nav-chevron{{transform:rotate(180deg)}}
.otg-nav-dropdown{{position:absolute;top:calc(100% + 6px);left:0;width:190px;box-sizing:border-box;padding:6px;background:#070809;border:none;box-shadow:0 12px 30px rgba(0,0,0,.62);z-index:100;opacity:0;visibility:hidden;pointer-events:none;transform:translateY(-4px);transition:opacity 180ms cubic-bezier(.2,.7,.2,1),visibility 180ms cubic-bezier(.2,.7,.2,1)}}
.otg-nav-analytics:hover .otg-nav-dropdown,.otg-nav-analytics:focus-within .otg-nav-dropdown,.otg-nav-analytics[open] .otg-nav-dropdown{{opacity:1;visibility:visible;pointer-events:auto;transform:translateY(0)}}
.otg-nav-dropdown a{{height:34px;display:flex;align-items:center;padding:0 10px;box-sizing:border-box;border:none;background:transparent;color:#A7ACB3!important;font-size:10px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;text-decoration:none!important;transition:color 180ms cubic-bezier(.2,.7,.2,1),background-color 180ms cubic-bezier(.2,.7,.2,1),text-shadow 180ms cubic-bezier(.2,.7,.2,1)}}.otg-nav-dropdown a:hover{{color:#FFFFFF!important;background:rgba(255,255,255,.055);border:none;text-decoration:none!important;padding-left:10px;text-shadow:0 0 12px rgba(255,255,255,.08)}}.otg-nav-dropdown a.active{{color:#FFFFFF!important;background:rgba(255,255,255,.080);border:none;text-decoration:none!important;text-shadow:0 0 14px rgba(255,255,255,.10)}}
.otg-nav-disabled{{cursor:default;user-select:none}}.otg-nav-disabled:hover{{background:transparent;border-color:transparent;color:#5F646C;text-shadow:none;transform:none;opacity:.72}}.otg-nav-login{{background:transparent;border-color:transparent;color:#5F646C;opacity:.72}}.otg-nav-login:hover{{color:#5F646C;border-color:transparent;background:transparent;text-shadow:none;transform:none;opacity:.72}}
@media(max-width:768px){{.otg-top-nav{{justify-content:flex-end;gap:6px;min-height:32px;margin-bottom:8px}}.otg-top-nav-control{{height:30px;padding-left:8px;padding-right:8px;font-size:9px;letter-spacing:.6px}}.otg-nav-analytics,.otg-nav-analytics>summary{{width:176px}}.otg-nav-dropdown{{width:176px}}.otg-nav-dropdown a{{min-height:34px;height:34px}}}}
@media(prefers-reduced-motion:reduce){{.otg-top-nav-control,.otg-nav-chevron,.otg-nav-dropdown,.otg-nav-dropdown a{{transition:none}}.otg-top-nav-control:hover{{transform:none}}}}
</style><nav class="otg-top-nav" aria-label="Primary navigation"><details class="otg-nav-analytics"><summary class="otg-top-nav-control {'active' if analytics_active else ''}">ANALYTICS<span class="otg-nav-chevron" aria-hidden="true"></span></summary><div class="otg-nav-dropdown"><a class="{active['item']}" href="/?mode=item">ITEM</a><a class="{active['market']}" href="/?mode=market">MARKET</a><a class="{active['top_items']}" href="/?mode=top_items">TOP ITEMS</a><a class="{active['top_traders']}" href="/?mode=top_traders">TOP TRADERS</a></div></details><a class="otg-top-nav-control" href="/?mode=roadmap">ROADMAP</a><a class="otg-top-nav-control {feedback_active}" href="{feedback_href}">FEEDBACK</a><span class="otg-top-nav-control otg-nav-disabled otg-nav-login" aria-disabled="true" title="Coming soon">LOG IN</span></nav>''', unsafe_allow_html=True)
    return current_mode
