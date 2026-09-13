"""Top-right analytics navigation."""

from typing import Literal
import streamlit as st


def render_mode_switch() -> Literal['item', 'market', 'top_items', 'trader']:
    raw_mode = st.query_params.get('mode', 'item')
    if isinstance(raw_mode, list):
        raw_mode = raw_mode[0]
    current_mode = 'trader' if raw_mode in ('trader', 'top_traders') else raw_mode
    if current_mode not in ('item', 'market', 'top_items', 'trader'):
        current_mode = 'item'
    active = {key: ('active' if current_mode == mode else '') for key, mode in {
        'item': 'item', 'market': 'market', 'top_items': 'top_items', 'top_traders': 'trader'
    }.items()}
    st.markdown(f'''<style>
.otg-top-nav{{display:flex;align-items:center;justify-content:flex-end;gap:8px;width:100%;min-height:36px;margin:0 0 8px 0;padding:0;position:relative;z-index:50}}
.otg-top-nav-control{{height:34px;box-sizing:border-box;display:inline-flex;align-items:center;justify-content:center;padding:0 14px;background:#050505;border:1px solid #303035;border-radius:0;font-family:'PP Supply Sans','Space Mono',monospace,sans-serif;font-size:10px;font-weight:700;line-height:1;letter-spacing:1px;text-transform:uppercase;white-space:nowrap;color:#D8D8D8;text-decoration:none;cursor:pointer;transition:color 150ms ease,border-color 150ms ease,background-color 150ms ease,transform 150ms ease}}
.otg-top-nav-control:hover{{color:#FF003A;border-color:#FF003A;background:rgba(255,0,58,.06);transform:translateY(-1px)}}
.otg-top-nav-control:focus-visible,.otg-nav-dropdown a:focus-visible{{outline:1px solid #FF003A;outline-offset:2px}}
.otg-nav-analytics{{position:relative}}.otg-nav-analytics>summary{{list-style:none;color:#FFFFFF;border-color:#FF003A;border-bottom:2px solid #FF003A;background:rgba(255,0,58,.04)}}.otg-nav-analytics>summary::-webkit-details-marker{{display:none}}
.otg-nav-chevron{{margin-left:7px;font-size:9px;color:currentColor;transition:transform 140ms ease}}.otg-nav-chevron::after{{content:'⌄'}}.otg-nav-analytics[open] .otg-nav-chevron{{transform:rotate(180deg)}}
.otg-nav-dropdown{{position:absolute;top:calc(100% + 6px);left:0;width:190px;box-sizing:border-box;padding:6px;background:#050505;border:1px solid #303035;box-shadow:0 10px 24px rgba(0,0,0,.55);z-index:100;opacity:0;visibility:hidden;pointer-events:none;transform:translateY(-4px);transition:opacity 140ms ease,transform 140ms ease,visibility 140ms ease}}
.otg-nav-analytics:hover .otg-nav-dropdown,.otg-nav-analytics:focus-within .otg-nav-dropdown,.otg-nav-analytics[open] .otg-nav-dropdown{{opacity:1;visibility:visible;pointer-events:auto;transform:translateY(0)}}
.otg-nav-dropdown a{{height:34px;display:flex;align-items:center;padding:0 10px;box-sizing:border-box;border-left:2px solid transparent;background:transparent;color:#C8C8C8!important;font-size:10px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;text-decoration:none!important;transition:color 120ms ease,background-color 120ms ease,border-color 120ms ease,padding-left 120ms ease}}.otg-nav-dropdown a:hover{{color:#FFFFFF!important;background:rgba(255,0,58,.07);border-left-color:#FF003A;padding-left:13px}}.otg-nav-dropdown a.active{{color:#FF003A!important;border-left-color:#FF003A;background:rgba(255,0,58,.04)}}
.otg-nav-disabled{{cursor:default;user-select:none}}.otg-nav-disabled:hover{{color:#707070;border-color:#303035;background:#050505;transform:none}}.otg-nav-login{{background:#151515;border-color:#404040;color:#A0A0A0}}.otg-nav-login:hover{{color:#A0A0A0;border-color:#404040;background:#151515;transform:none}}
@media(max-width:768px){{.otg-top-nav{{justify-content:flex-end;gap:6px;min-height:32px;margin-bottom:8px}}.otg-top-nav-control{{height:30px;padding-left:8px;padding-right:8px;font-size:9px;letter-spacing:.6px}}.otg-nav-analytics,.otg-nav-analytics>summary{{width:176px}}.otg-nav-dropdown{{width:176px}}.otg-nav-dropdown a{{min-height:34px;height:34px}}}}
@media(prefers-reduced-motion:reduce){{.otg-top-nav-control,.otg-nav-chevron,.otg-nav-dropdown,.otg-nav-dropdown a{{transition:none}}.otg-top-nav-control:hover{{transform:none}}}}
</style><nav class="otg-top-nav" aria-label="Primary navigation"><details class="otg-nav-analytics"><summary class="otg-top-nav-control">ANALYTICS<span class="otg-nav-chevron" aria-hidden="true"></span></summary><div class="otg-nav-dropdown"><a class="{active['item']}" href="/?mode=item">ITEM</a><a class="{active['market']}" href="/?mode=market">MARKET</a><a class="{active['top_items']}" href="/?mode=top_items">TOP ITEMS</a><a class="{active['top_traders']}" href="/?mode=top_traders">TOP TRADERS</a></div></details><a class="otg-top-nav-control" href="/?mode=roadmap">ROADMAP</a><span class="otg-top-nav-control otg-nav-disabled" aria-disabled="true" title="Coming soon">FEEDBACK</span><span class="otg-top-nav-control otg-nav-disabled otg-nav-login" aria-disabled="true" title="Coming soon">LOG IN</span></nav>''', unsafe_allow_html=True)
    return current_mode
