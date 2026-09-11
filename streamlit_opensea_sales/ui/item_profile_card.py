"""Reusable item analytics profile card markup."""

from html import escape
from typing import Any, Mapping

from ui.gunzscope_attribution import inline_logo
from formatters import get_rarity_style


_METRICS = (
    ("Market Strength", "market_strength_score", ".3f"),
    ("Liquidity Score", "liquidity_score", ".2f"),
    ("Volume GUN", "volume_gun", ",.2f"),
    ("Volume USD", "volume_usd", ",.2f"),
    ("Events", "period_events", ",.0f"),
    ("Active Days", "active_trading_days", ".0f"),
    ("Avg Price GUN", "avg_price_gun", ",.2f"),
    ("Avg Price USD", "avg_price_usd", ",.2f"),
)


def _value(row: Mapping[str, Any], key: str, spec: str) -> str:
    value = row.get(key)
    try:
        if value is None or value != value:
            return "N/A"
        return format(value, spec)
    except (TypeError, ValueError):
        return "N/A"


def build_item_profile_card_html(row: Mapping[str, Any], presentation: str = "standalone", item_url: str | None = None) -> str:
    """Build shared item-card content for standalone or overlay presentation."""
    if presentation not in {"standalone", "overlay"}:
        raise ValueError("presentation must be standalone or overlay")
    name = escape(str(row.get("item_name", "")).strip(), quote=True)
    rarity = escape(str(row.get("rarity", "")).strip(), quote=True)
    rarity_color, _ = get_rarity_style(str(row.get("rarity", "")).strip())
    item_class = escape(str(row.get("_item_class", "Unclassified")), quote=True)
    image = str(row.get("image_url") or "").strip()
    image_html = f'<img class="top-item-profile-image" src="{escape(image, quote=True)}" alt="{name}">' if image else '<div class="top-item-profile-placeholder">NO IMAGE</div>'
    link_open = f'<a class="top-item-profile-name" href="{escape(item_url, quote=True)}">' if item_url else '<div class="top-item-profile-name">'
    link_close = "</a>" if item_url else "</div>"
    supply = _value(row, "_supply", ",.0f")
    supply_rank = row.get("_supply_rank")
    supply_rank_text = "-" if supply_rank is None or supply_rank != supply_rank else str(supply_rank)
    return f'''<article class="top-item-profile-card top-item-profile-card--{presentation}">
<div class="top-item-profile-visual">{image_html}</div>
<div class="top-item-profile-content">
<div class="top-item-profile-identity">{link_open}{name}{link_close}<div class="top-item-profile-meta"><span class="top-item-profile-rarity" style="color:{escape(rarity_color, quote=True)}">{rarity}</span><span>{item_class}</span></div></div>
<section class="top-item-profile-section"><h3>RANKING</h3><div class="top-item-profile-rank"><span>GLOBAL RANK</span><b>{escape(str(row.get('display_rank', row.get('rank', '-'))))}</b></div></section>
<section class="top-item-profile-section"><h3>MARKET STATS</h3><div class="top-item-profile-stats">{''.join(f'<div class="top-item-profile-metric"><span>{label}</span><b>{_value(row, key, spec)}</b></div>' for label, key, spec in _METRICS)}</div></section>
<section class="top-item-profile-section"><h3>SUPPLY {inline_logo("top-item-profile-attribution")}</h3><div class="top-item-profile-stats"><div class="top-item-profile-metric"><span>TOTAL SUPPLY</span><b>{supply}</b></div><div class="top-item-profile-metric"><span>SUPPLY RANK</span><b>{escape(supply_rank_text)}</b></div></div></section>
</div></article>'''


def item_profile_card_styles() -> str:
    return '''<style>
.top-item-profile-card{box-sizing:border-box;display:grid;grid-template-columns:minmax(220px,370px) minmax(0,1fr);gap:22px;width:min(980px,calc(100vw - 40px));padding:22px;background:#050505;color:#fff;border:1px solid #303035;box-shadow:0 8px 24px #000;font-family:'Space Mono',monospace;overflow:hidden}
.top-item-profile-visual{width:100%;aspect-ratio:1/1;min-width:0;background:#080808;border:1px solid #303035;display:flex;align-items:center;justify-content:center;overflow:hidden}.top-item-profile-image{display:block;width:100%;height:100%;object-fit:contain}.top-item-profile-placeholder{color:#777;font-size:10px}.top-item-profile-content{min-width:0}.top-item-profile-name{display:block;color:#fff;text-decoration:none;font-family:'PP Supply Sans','Space Mono',sans-serif;font-size:32px;font-weight:700;line-height:1.05;overflow-wrap:anywhere}.top-item-profile-name:hover{color:#ff003a}.top-item-profile-meta{display:flex;gap:12px;flex-wrap:wrap;color:#c8c8cd;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin:8px 0 14px}.top-item-profile-section{margin-top:12px}.top-item-profile-section h3{color:#ff003a;font-size:10px;letter-spacing:1.5px;margin:0;padding:6px 8px;border:1px solid #ff003a;border-bottom:0}.top-item-profile-rank,.top-item-profile-metric{display:flex;justify-content:space-between;gap:12px;min-width:0;padding:6px 8px;border:1px solid #303035;background:#0b0b0b;font-size:10px}.top-item-profile-metric span{color:#c8c8cd;overflow-wrap:anywhere}.top-item-profile-metric b{color:#fff;text-align:right;overflow-wrap:anywhere}.top-item-profile-stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:3px}.top-item-profile-attribution{font-size:12px}
@media(max-width:768px){.top-item-profile-card{display:block;width:calc(100vw - 24px);max-width:none;padding:14px}.top-item-profile-visual{width:100%;max-width:300px;margin:0 auto 14px}.top-item-profile-name{font-size:24px}.top-item-profile-stats{grid-template-columns:1fr 1fr}}
@media(max-width:360px){.top-item-profile-card{width:calc(100vw - 16px);padding:10px}.top-item-profile-stats{grid-template-columns:1fr}.top-item-profile-name{font-size:21px}}
</style>''' + '''<style>.top-item-profile-name:link,.top-item-profile-name:visited,.top-item-profile-name:hover,.top-item-profile-name:focus,.top-item-profile-name:active{color:#FFFFFF !important;text-decoration:none !important}</style>'''
