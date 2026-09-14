import html
import streamlit as st
def build_item_chart_trade_overlay_html(contexts):
    from ui.trader_overview import build_trader_profile_card_html, trader_profile_card_styles
    cards = []
    for key, context in contexts.items():
        cards.append(f'<div class="item-chart-trader-card-overlay" data-wallet-key="{html.escape(key)}" hidden>{build_trader_profile_card_html(context)}</div>')
    return trader_profile_card_styles() + ''.join(cards) + '''<style>
.item-chart-pinned-trade-tooltip{position:fixed;z-index:10000;width:320px;max-width:calc(100vw - 24px);background:#080808;border:1px solid #5A5A62;border-radius:0;padding:8px 10px;color:#FFF;font-family:'Space Mono',monospace;font-size:11px;line-height:1.4;box-sizing:border-box;box-shadow:0 8px 24px #000;pointer-events:auto}.item-chart-pinned-trade-tooltip span{color:#FF003A;cursor:pointer}.item-chart-pinned-trade-tooltip span:hover,.item-chart-pinned-trade-tooltip span:focus-visible{color:#FFF;text-decoration:underline}.item-chart-trader-card-overlay{position:fixed;z-index:10001;max-height:calc(100vh - 32px);overflow:auto;width:min(980px,calc(100vw - 40px))}.item-chart-trader-card-overlay .trader-profile-card{width:100%;max-width:none}@media(max-width:768px){.item-chart-trader-card-overlay{width:calc(100vw - 24px);max-width:calc(100vw - 24px)}}
</style>'''

def render_item_chart_trade_overlay_wiring():
    from ui.trader_overview import render_trader_clipboard_wiring
    st.components.v1.html('''<script>
(function(){var w=window.parent,d=w.document,key='__otgItemChartTradeState';if(w[key]&&w[key].destroy)w[key].destroy();var tip=null,card=null,last=null,timer=null,dead=false;
function close(){if(tip)tip.remove();if(card)card.hidden=true;tip=card=null;}
function place(el,x,y,m){el.hidden=false;var r=el.getBoundingClientRect(),left=Math.max(m,Math.min(x,w.innerWidth-r.width-m)),top=Math.max(m,Math.min(y,w.innerHeight-r.height-m));el.style.left=left+'px';el.style.top=top+'px';}
function participant(label,key){var s=d.createElement('span');s.textContent=label;s.setAttribute('role','button');s.tabIndex=0;s.dataset.walletKey=key;s.addEventListener('click',function(e){e.stopPropagation();var c=d.querySelector('.item-chart-trader-card-overlay[data-wallet-key="'+CSS.escape(key)+'"]');if(!c)return;if(card===c){close();return}if(card)card.hidden=true;card=c;place(c,e.clientX||16,e.clientY||16,16)});s.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();s.click()}});return s}
function show(p,x,y){close();tip=d.createElement('div');tip.className='item-chart-pinned-trade-tooltip';var lines=String(p.customdata[0]||'').split('<br>');lines.forEach(function(t){var q=d.createElement('div');q.textContent=t;tip.appendChild(q)});[['Buyer: ',p.customdata[1],p.customdata[3]],['Seller: ',p.customdata[2],p.customdata[4]]].forEach(function(a){var q=d.createElement('div');q.appendChild(d.createTextNode(a[0]));q.appendChild(participant(a[1],a[2]));tip.appendChild(q)});d.body.appendChild(tip);place(tip,x+12,y+12,12)}
function bind(){var plot=Array.from(d.querySelectorAll('.js-plotly-plot')).find(function(x){return x.layout&&x.layout.meta&&x.layout.meta.otg_chart_id==='item-sales-chart'});if(!plot)return false;plot.addEventListener('click',function(e){last={x:e.clientX,y:e.clientY}});plot.on('plotly_click',function(e){var p=e.points&&e.points[0];if(!p||!p.data.meta||p.data.meta.otg_point_kind!=='trade')return;show(p,last?last.x:16,last?last.y:16);if(w.Plotly&&w.Plotly.Fx&&w.Plotly.Fx.unhover)w.Plotly.Fx.unhover(plot)});return true}
var state={destroy:function(){dead=true;if(timer)clearTimeout(timer);d.removeEventListener('click',outside);d.removeEventListener('keydown',keys);close();delete w[key]}};function outside(e){if(tip&&!tip.contains(e.target)&&card&&!card.contains(e.target)&&!e.target.closest('.js-plotly-plot'))close()}function keys(e){if(e.key==='Escape')close()}w[key]=state;d.addEventListener('click',outside);d.addEventListener('keydown',keys);function poll(n){if(dead)return;if(bind())return;if(n<30)timer=setTimeout(function(){poll(n+1)},100)}poll(0)
})();</script>''', height=0)
    render_trader_clipboard_wiring()
