"""Static, data-driven Ecosystem directory page."""

from __future__ import annotations

import base64
import html
from pathlib import Path

import streamlit as st

from ecosystem_catalog import load_ecosystem_catalog


REPO_ROOT = Path(__file__).resolve().parents[2]
SECTION_ORDER = (
    ("official", "OFFICIAL ECOSYSTEM"),
    ("external_officially_linked", "MARKETPLACES"),
    ("community", "COMMUNITY ECOSYSTEM"),
)
BADGE_LABELS = {
    "official": "OFFICIAL",
    "external_officially_linked": "EXTERNAL MARKETPLACE",
    "community": "COMMUNITY",
}
CATEGORY_LABELS = {
    "player_app": "PLAYER APP",
    "game_tools": "GAME TOOLS",
}
SECTION_ICONS = {
    "official": "img/section_ecosystem/OFFICIAL_ECOSYSTEM.png",
    "external_officially_linked": "img/section_ecosystem/MARKETPLACES.png",
    "community": "img/section_ecosystem/COMMUNITY_ECOSYSTEM.png",
}


def _asset_data_uri(relative_path: str | None) -> str | None:
    if not relative_path:
        return None
    path = REPO_ROOT / relative_path
    if not path.is_file():
        return None
    suffix = path.suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(suffix)
    if not mime:
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _fallback_text(project: dict) -> str:
    fallback = {
        "off_the_grid": "OTG",
        "otg_companion": "OTG",
        "technocore": "TC",
        "gunz_wallet": "G",
        "gunzscan": "GS",
        "gunz_bridge": "GB",
        "gunz_developers": "GD",
        "opensea_otg": "OS",
        "gunzscope": "GS",
        "otgstats": "OTG",
        "walletzero": "W0",
    }
    return fallback.get(project["id"], project["name"][0])


def _logo_markup(project: dict) -> str:
    asset_uri = _asset_data_uri(project.get("logo_asset"))
    if asset_uri:
        return f'<img class="ecosystem-card-logo-image" src="{asset_uri}" alt="" loading="lazy">'
    return f'<span class="ecosystem-card-logo-fallback" aria-hidden="true">{html.escape(_fallback_text(project))}</span>'


def _section_icon_markup(project_type: str) -> str:
    asset_uri = _asset_data_uri(SECTION_ICONS.get(project_type))
    if not asset_uri:
        return ""
    return f'<img class="ecosystem-section-icon" src="{asset_uri}" alt="" aria-hidden="true">'


def _card_markup(project: dict) -> str:
    project_id = html.escape(project["id"], quote=True)
    name = html.escape(project["name"])
    badge = html.escape(BADGE_LABELS[project["type"]])
    category = html.escape(CATEGORY_LABELS.get(project["category"], project["category"].replace("_", " ").upper()))
    description = html.escape(project["description"])
    url = html.escape(project["url"], quote=True)
    featured_class = " ecosystem-card-featured" if project["featured"] else ""
    return f'''<article class="ecosystem-card{featured_class}" data-project-id="{project_id}">
  <div class="ecosystem-card-logo">{_logo_markup(project)}</div>
  <div class="ecosystem-card-meta"><span class="ecosystem-badge ecosystem-badge-{html.escape(project["type"])}">{badge}</span><span class="ecosystem-category">{category}</span></div>
  <h3 class="ecosystem-card-name">{name}</h3>
  <p class="ecosystem-card-description">{description}</p>
  <div class="ecosystem-card-footer"><a class="ecosystem-card-visit" href="{url}" target="_blank" rel="noopener noreferrer"><span>VISIT</span><span aria-hidden="true">&#8599;</span></a></div>
</article>'''


def _page_css() -> str:
    return """<style>
.st-key-ecosystem_page{width:100%;max-width:1560px;margin:0 auto;padding:0;color:#F4F5F6}
.st-key-ecosystem_page .ecosystem-title{margin:0 0 5px;color:#FFFFFF;font-size:30px;font-weight:700;letter-spacing:1.8px;line-height:1.04;text-transform:uppercase}
.st-key-ecosystem_page .ecosystem-intro{max-width:760px;margin:0;color:#9FA5AD;font-size:13px;line-height:1.55}
.st-key-ecosystem_page .ecosystem-disclaimer{max-width:760px;margin:8px 0 0;color:#6D737B;font-size:10px;line-height:1.45}
.st-key-ecosystem_page .ecosystem-section{margin-top:20px}
.st-key-ecosystem_page .ecosystem-section-heading{display:grid;grid-template-columns:48px max-content minmax(0,1fr);grid-template-rows:48px;align-items:center;column-gap:10px;margin:0 0 10px;color:#F4F5F6;font-size:12px;letter-spacing:1.25px;line-height:1.2;text-transform:uppercase}
.st-key-ecosystem_page .ecosystem-section-heading .ecosystem-section-icon{display:block;grid-column:1;grid-row:1;width:48px;height:48px;object-fit:contain;object-position:center}
.st-key-ecosystem_page .ecosystem-section-heading .ecosystem-section-title{grid-column:2;grid-row:1;white-space:nowrap}
.st-key-ecosystem_page .ecosystem-section-heading .ecosystem-section-divider{display:block;grid-column:3;grid-row:1;width:100%;height:1px;background:#26292D}
.st-key-ecosystem_page .ecosystem-section-count{color:#777D85;font-size:9px;letter-spacing:.8px}
.st-key-ecosystem_page .ecosystem-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.st-key-ecosystem_page .ecosystem-grid-marketplaces{grid-template-columns:minmax(0,250px);justify-content:start}
.st-key-ecosystem_page .ecosystem-card{display:flex;min-width:0;min-height:0;aspect-ratio:1 / .92;box-sizing:border-box;flex-direction:column;padding:10px;background:#050505;border:1px solid #292C31;border-radius:0}
.st-key-ecosystem_page .ecosystem-card:hover{border-color:#555A62}
.st-key-ecosystem_page .ecosystem-card-featured{border-color:#383B41}
.st-key-ecosystem_page .ecosystem-card-logo{display:flex;align-items:flex-start;justify-content:flex-start;width:100%;height:40px;margin:0 0 8px}
.st-key-ecosystem_page .ecosystem-card-logo-image{display:block;max-width:108px;max-height:40px;width:auto;height:auto;object-fit:contain;object-position:left center}
.st-key-ecosystem_page .ecosystem-card-logo-fallback{display:inline-flex;align-items:center;justify-content:center;min-width:40px;height:40px;padding:0 7px;box-sizing:border-box;border:1px solid #42464D;border-left:2px solid #FF003A;color:#D5D8DC;font-size:12px;font-weight:700;letter-spacing:1px}
.st-key-ecosystem_page .ecosystem-card-meta{display:flex;align-items:center;gap:6px;min-height:15px;margin:0 0 5px}
.st-key-ecosystem_page .ecosystem-badge{display:inline-flex;align-items:center;min-height:17px;padding:0 5px;border:1px solid #596069;color:#D8DBDE;font-size:7px;font-weight:700;letter-spacing:.65px;line-height:1;text-transform:uppercase}
.st-key-ecosystem_page .ecosystem-badge-official{border-color:#FF003A;color:#FFFFFF}
.st-key-ecosystem_page .ecosystem-badge-external_officially_linked{border-color:#B1B6BD;color:#F0F1F2}
.st-key-ecosystem_page .ecosystem-badge-community{border-color:#656B73;color:#C8CDD2}
.st-key-ecosystem_page .ecosystem-category{color:#777D85;font-size:8px;font-weight:700;letter-spacing:.75px;text-transform:uppercase}
.st-key-ecosystem_page .ecosystem-card-name{margin:0;color:#FFFFFF;font-size:14px;font-weight:700;letter-spacing:.55px;line-height:1.15;text-transform:uppercase}
.st-key-ecosystem_page .ecosystem-card-description{display:-webkit-box;flex:1;margin:6px 0 7px;overflow:hidden;color:#9FA5AD;font-size:10px;line-height:1.3;-webkit-box-orient:vertical;-webkit-line-clamp:2}
.st-key-ecosystem_page .ecosystem-card-footer{display:flex;align-items:flex-end;min-height:18px}
.st-key-ecosystem_page .ecosystem-card-visit{display:inline-flex;align-items:center;gap:6px;box-sizing:border-box;padding:0 0 3px;border:0;border-bottom:1px solid #383C42;color:#E6E8EA!important;font-size:8px;font-weight:700;letter-spacing:.9px;line-height:1;text-decoration:none!important}
.st-key-ecosystem_page .ecosystem-card-visit:hover,.st-key-ecosystem_page .ecosystem-card-visit:focus-visible{border-color:#FF003A;color:#FF003A!important;outline:none}
@media (min-width:769px){.st-key-ecosystem_page{margin-top:-44px!important}}
@media (min-width:1500px){.st-key-ecosystem_page .ecosystem-grid{grid-template-columns:repeat(5,minmax(0,1fr))}}
@media (max-width:1100px){.st-key-ecosystem_page .ecosystem-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:900px){.st-key-ecosystem_page .ecosystem-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:768px){.st-key-ecosystem_page{max-width:100%}.st-key-ecosystem_page .ecosystem-title{font-size:25px}.st-key-ecosystem_page .ecosystem-grid,.st-key-ecosystem_page .ecosystem-grid-marketplaces{grid-template-columns:1fr;gap:9px}.st-key-ecosystem_page .ecosystem-card{aspect-ratio:auto;min-height:205px}.st-key-ecosystem_page .ecosystem-section{margin-top:18px}}
@media (prefers-reduced-motion:reduce){.st-key-ecosystem_page .ecosystem-card,.st-key-ecosystem_page .ecosystem-card-visit{transition:none}}
</style>"""


def render_ecosystem_page() -> None:
    try:
        projects = load_ecosystem_catalog()
    except Exception as exc:
        st.error("ECOSYSTEM CATALOG UNAVAILABLE")
        st.caption(f"Catalog validation failed: {type(exc).__name__}")
        return

    with st.container(key="ecosystem_page"):
        st.markdown(_page_css(), unsafe_allow_html=True)
        st.markdown(
            "<h1 class='ecosystem-title'>GUNZ ECOSYSTEM</h1>"
            "<p class='ecosystem-intro'>Games, applications, infrastructure, marketplaces, and community tools connected to the GUNZ ecosystem.</p>"
            "<p class='ecosystem-disclaimer'>Official, external marketplace, and community projects are identified separately. Inclusion in this directory does not imply ownership or endorsement by Gunzilla Games.</p>",
            unsafe_allow_html=True,
        )
        for project_type, title in SECTION_ORDER:
            section_projects = [project for project in projects if project["type"] == project_type]
            cards = "".join(_card_markup(project) for project in section_projects)
            section_title_id = f"ecosystem-{project_type}-title"
            st.markdown(
                f'<section class="ecosystem-section" aria-labelledby="{section_title_id}">'
                f'<div class="ecosystem-section-heading" role="heading" aria-level="2">'
                f'{_section_icon_markup(project_type)}'
                f'<span id="{section_title_id}" class="ecosystem-section-title">{title}</span>'
                f'<span class="ecosystem-section-divider" aria-hidden="true"></span>'
                f'</div>'
                f'<div class="ecosystem-grid{" ecosystem-grid-marketplaces" if project_type == "external_officially_linked" else ""}">{cards}</div></section>',
                unsafe_allow_html=True,
            )
