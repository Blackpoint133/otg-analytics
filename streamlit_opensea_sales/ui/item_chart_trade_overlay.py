import html

import streamlit.components.v1 as components


def build_item_chart_trade_overlay_html(contexts):
    from ui.trader_overview import build_trader_profile_card_html, trader_profile_card_styles

    cards = [
        f'<div class="item-chart-trader-card-overlay" data-wallet-key="{html.escape(key)}" hidden>'
        f'{build_trader_profile_card_html(value)}</div>'
        for key, value in contexts.items()
    ]
    return trader_profile_card_styles() + ''.join(cards) + '''<style>.item-chart-trade-tooltip{position:fixed;z-index:10000;width:320px;max-width:calc(100vw - 24px);background:#080808;border:1px solid #5A5A62;border-radius:0;padding:8px 10px;color:#FFFFFF;font-family:'Space Mono',monospace;font-size:11px;line-height:1.4;box-sizing:border-box;box-shadow:0 8px 24px #000;pointer-events:auto}.item-chart-trade-tooltip span{color:#FF003A;cursor:pointer}.item-chart-trade-tooltip span:hover,.item-chart-trade-tooltip span:focus-visible{color:#FFFFFF;text-decoration:underline}.item-chart-trader-card-overlay{position:fixed;z-index:2147483000;max-height:calc(100vh - 32px);overflow:auto;width:min(980px,calc(100vw - 40px))}.item-chart-trader-card-overlay .trader-profile-card{width:100%;max-width:none}@media(max-width:768px){.item-chart-trader-card-overlay{width:calc(100vw - 24px);max-width:calc(100vw - 24px)}}</style>'''


def render_item_chart_trade_overlay_wiring():
    from ui.trader_overview import render_trader_clipboard_wiring

    components.html(
        r'''<script>
(function(){
var w=window.parent,d=w.document,key='__otgItemChartTradeState';
if(w[key]&&typeof w[key].destroy==='function')w[key].destroy();
var tip=null,pinned=false,activePointKey=null,card=null,boundPlot=null,lastPointer=null,
    interactionToken=0,pointClickToken=0,timer=null,backgroundTimer=null,observer=null,dead=false,observerTimer=null,
    nativePlotClickHandler=null,nativeChartClickHandler=null,plotlyHoverHandler=null,plotlyUnhoverHandler=null,plotlyClickHandler=null;

function portalCard(c){if(!c.__otgOriginParent){c.__otgOriginParent=c.parentNode;c.__otgOriginNextSibling=c.nextSibling}d.body.appendChild(c);c.__otgPortaled=true}
function restoreCard(c){var p=c.__otgOriginParent,s=c.__otgOriginNextSibling;if(p&&p.isConnected){if(s&&s.parentNode===p)p.insertBefore(c,s);else p.appendChild(c)}else if(c.parentNode)c.parentNode.removeChild(c);delete c.__otgOriginParent;delete c.__otgOriginNextSibling;delete c.__otgPortaled}
function closePinnedTooltip(){if(tip)tip.remove();tip=null;activePointKey=null;pinned=false}
function closeTraderCard(){if(card){card.hidden=true;restoreCard(card)}card=null}
function closeAll(){closeTraderCard();closePinnedTooltip()}
function placeTooltip(el,x,y){el.hidden=false;var width=el.offsetWidth,height=el.offsetHeight;el.style.left=Math.max(12,Math.min(x,w.innerWidth-width-12))+'px';el.style.top=Math.max(12,Math.min(y,w.innerHeight-height-12))+'px'}
function placeCard(c){c.hidden=false;c.style.visibility='hidden';c.style.left='0px';c.style.top='0px';var tipRect=tip.getBoundingClientRect(),cardWidth=c.offsetWidth,cardHeight=c.offsetHeight,gap=12,margin=16;var candidates=[{name:'RIGHT',left:tipRect.right+gap,top:tipRect.top},{name:'LEFT',left:tipRect.left-gap-cardWidth,top:tipRect.top},{name:'BELOW',left:tipRect.left,top:tipRect.bottom+gap},{name:'ABOVE',left:tipRect.left,top:tipRect.top-gap-cardHeight}];function clamp(v,min,max){return Math.max(min,Math.min(v,max))}function fits(x){return x.left>=margin&&x.left+cardWidth<=w.innerWidth-margin&&x.top>=margin&&x.top+cardHeight<=w.innerHeight-margin}var fitsRight=fits(candidates[0]),fitsLeft=fits(candidates[1]),fitsBelow=fits(candidates[2]),fitsAbove=fits(candidates[3]);var chosen=fitsRight?candidates[0]:fitsLeft?candidates[1]:fitsBelow?candidates[2]:fitsAbove?candidates[3]:candidates.reduce(function(best,x){function penalty(y){return Math.max(0,margin-y.left)+Math.max(0,y.left+cardWidth-(w.innerWidth-margin))+Math.max(0,margin-y.top)+Math.max(0,y.top+cardHeight-(w.innerHeight-margin))}return penalty(x)<penalty(best)?x:best});var left=clamp(chosen.left,margin,w.innerWidth-cardWidth-margin),top=clamp(chosen.top,margin,w.innerHeight-cardHeight-margin);c.style.left=left+'px';c.style.top=top+'px';c.style.visibility='visible'}
function participant(label,key){var s=d.createElement('span');s.textContent=label;s.setAttribute('role','button');s.tabIndex=0;s.dataset.walletKey=key;s.addEventListener('click',function(e){e.stopPropagation();if(!pinned||!key)return;var c=d.querySelector('.item-chart-trader-card-overlay[data-wallet-key="'+CSS.escape(key)+'"]');if(!c)return;if(card===c){closeTraderCard();return}closeTraderCard();portalCard(c);c.scrollTop=0;card=c;placeCard(c)});s.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();if(pinned)s.click()}});return s}
function renderPoint(p,x,y){if(!tip){tip=d.createElement('div');tip.className='item-chart-trade-tooltip';d.body.appendChild(tip)}while(tip.firstChild)tip.removeChild(tip.firstChild);String(p.customdata[0]||'').split('<br>').forEach(function(t){var q=d.createElement('div');q.textContent=t;tip.appendChild(q)});[['Buyer: ',p.customdata[1],p.customdata[3]],['Seller: ',p.customdata[2],p.customdata[4]]].forEach(function(a){var q=d.createElement('div');q.appendChild(d.createTextNode(a[0]));q.appendChild(participant(a[1],a[2]));tip.appendChild(q)});placeTooltip(tip,x+12,y+12)}
function pointKey(p){return p.curveNumber+':'+p.pointNumber}
function capturePointer(e){if(e.type==='pointerdown'){interactionToken+=1;pointClickToken=0}if(Number.isFinite(e.clientX)&&Number.isFinite(e.clientY))lastPointer={x:e.clientX,y:e.clientY}}
function resolvePointAnchor(plot,p){if(lastPointer)return lastPointer;var r=plot.getBoundingClientRect(),l=plot._fullLayout&&plot._fullLayout._size,x=p.xaxis&&p.xaxis.l2p?p.xaxis.l2p(p.x):null,y=p.yaxis&&p.yaxis.l2p?p.yaxis.l2p(p.y):null;if(Number.isFinite(x)&&Number.isFinite(y))return{x:r.left+(l?l.l:0)+x,y:r.top+(l?l.t:0)+y};return{x:r.left+r.width/2,y:r.top+r.height/2}}
function isCurrentItemPlot(plot){return!!(plot&&plot.isConnected&&plot.classList&&plot.classList.contains('js-plotly-plot')&&plot.layout&&plot.layout.meta&&plot.layout.meta.otg_chart_id==='item-sales-chart')}
function findCurrentPlot(){var plots=Array.from(d.querySelectorAll('.js-plotly-plot')).filter(isCurrentItemPlot);return plots.length?plots[plots.length-1]:null}
function scheduleBackgroundClose(){var token=interactionToken;if(backgroundTimer)w.clearTimeout(backgroundTimer);backgroundTimer=w.setTimeout(function(){backgroundTimer=null;if(dead||token!==interactionToken)return;if(pointClickToken===token){pointClickToken=0;return}closeAll()},0)}
function bindPlot(plot){if(!isCurrentItemPlot(plot))return;if(boundPlot===plot)return;if(boundPlot)unbindPlot();boundPlot=plot;nativePlotClickHandler=capturePointer;boundPlot.addEventListener('pointermove',nativePlotClickHandler);boundPlot.addEventListener('pointerdown',nativePlotClickHandler);nativeChartClickHandler=scheduleBackgroundClose;boundPlot.addEventListener('click',nativeChartClickHandler);plotlyHoverHandler=function(e){var p=e.points&&e.points[0];if(!p||!p.data.meta||p.data.meta.otg_point_kind!=='trade'||pinned)return;activePointKey=pointKey(p);var a=resolvePointAnchor(boundPlot,p);renderPoint(p,a.x,a.y)};plotlyUnhoverHandler=function(){if(!pinned)closePinnedTooltip()};plotlyClickHandler=function(e){var p=e.points&&e.points[0];if(!p||!p.data.meta||p.data.meta.otg_point_kind!=='trade')return;pointClickToken=interactionToken;var k=pointKey(p);if(activePointKey===k&&tip){pinned=true;return}closeTraderCard();pinned=true;activePointKey=k;var a=resolvePointAnchor(boundPlot,p);renderPoint(p,a.x,a.y)};boundPlot.on('plotly_hover',plotlyHoverHandler);boundPlot.on('plotly_unhover',plotlyUnhoverHandler);boundPlot.on('plotly_click',plotlyClickHandler)}
function unbindPlot(){if(!boundPlot)return;boundPlot.removeEventListener('pointermove',nativePlotClickHandler);boundPlot.removeEventListener('pointerdown',nativePlotClickHandler);boundPlot.removeEventListener('click',nativeChartClickHandler);if(typeof boundPlot.removeListener==='function'){boundPlot.removeListener('plotly_hover',plotlyHoverHandler);boundPlot.removeListener('plotly_unhover',plotlyUnhoverHandler);boundPlot.removeListener('plotly_click',plotlyClickHandler)}boundPlot=null;nativePlotClickHandler=null;nativeChartClickHandler=null;plotlyHoverHandler=null;plotlyUnhoverHandler=null;plotlyClickHandler=null}
function ensureBound(){if(dead)return;var plot=findCurrentPlot();if(plot===boundPlot&&plot&&plot.isConnected)return;if(boundPlot){unbindPlot();closeAll()}if(plot)bindPlot(plot)}
function outside(e){if((tip&&tip.contains(e.target))||(card&&card.contains(e.target))||(e.target.closest&&e.target.closest('.js-plotly-plot')))return;closeAll()}
function keys(e){if(e.key==='Escape')closeAll()}
var state={destroy:function(){dead=true;if(timer)w.clearTimeout(timer);if(backgroundTimer)w.clearTimeout(backgroundTimer);if(observerTimer)w.clearTimeout(observerTimer);timer=null;backgroundTimer=null;observerTimer=null;if(observer){observer.disconnect();observer=null}unbindPlot();d.removeEventListener('click',outside);d.removeEventListener('keydown',keys);closeAll();delete w[key]}};
w[key]=state;d.addEventListener('click',outside);d.addEventListener('keydown',keys);
if(w.MutationObserver&&(d.documentElement||d.body)){observer=new w.MutationObserver(function(){ensureBound()});observer.observe(d.documentElement||d.body,{childList:true,subtree:true})}
function poll(n){if(dead)return;ensureBound();if(!boundPlot&&n<30)timer=w.setTimeout(function(){timer=null;poll(n+1)},100)}
poll(0)
})();</script>''',
        height=0,
    )
    render_trader_clipboard_wiring()
