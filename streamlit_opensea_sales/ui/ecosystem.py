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
  <a class="ecosystem-card-visit" href="{url}" target="_blank" rel="noopener noreferrer">VISIT <span aria-hidden="true">&#8599;</span></a>
</article>'''


def _page_css() -> str:
    return """<style>
.st-key-ecosystem_page{width:100%;margin:0;padding:0;color:#F4F5F6}
.st-key-ecosystem_page .ecosystem-title{margin:0 0 7px;color:#FFFFFF;font-size:31px;font-weight:700;letter-spacing:1.8px;line-height:1.04;text-transform:uppercase}
.st-key-ecosystem_page .ecosystem-intro{max-width:760px;margin:0;color:#9FA5AD;font-size:13px;line-height:1.55}
.st-key-ecosystem_page .ecosystem-disclaimer{max-width:760px;margin:10px 0 0;color:#6D737B;font-size:10px;line-height:1.5}
.st-key-ecosystem_page .ecosystem-section{margin-top:31px}
.st-key-ecosystem_page .ecosystem-section-heading{display:flex;align-items:center;gap:12px;margin:0 0 12px;color:#F4F5F6;font-size:13px;letter-spacing:1.25px;line-height:1.2;text-transform:uppercase}
.st-key-ecosystem_page .ecosystem-section-heading::after{content:"";height:1px;flex:1;background:#26292D}
.st-key-ecosystem_page .ecosystem-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.st-key-ecosystem_page .ecosystem-card{display:flex;min-width:0;min-height:292px;box-sizing:border-box;flex-direction:column;padding:16px;background:#050505;border:1px solid #292C31;border-radius:0}
.st-key-ecosystem_page .ecosystem-card:hover{border-color:#555A62}
.st-key-ecosystem_page .ecosystem-card-featured{border-color:#383B41}
.st-key-ecosystem_page .ecosystem-card-logo{display:flex;align-items:center;justify-content:flex-start;width:100%;height:62px;margin:0 0 14px}
.st-key-ecosystem_page .ecosystem-card-logo-image{display:block;max-width:126px;max-height:58px;width:auto;height:auto;object-fit:contain;object-position:left center}
.st-key-ecosystem_page .ecosystem-card-logo-fallback{display:inline-flex;align-items:center;justify-content:center;min-width:58px;height:58px;padding:0 9px;box-sizing:border-box;border:1px solid #42464D;color:#BFC4CA;font-size:16px;font-weight:700;letter-spacing:1px}
.st-key-ecosystem_page .ecosystem-card-meta{display:flex;align-items:center;gap:9px;min-height:18px;margin:0 0 9px}
.st-key-ecosystem_page .ecosystem-badge{display:inline-flex;align-items:center;min-height:20px;padding:0 7px;border:1px solid #596069;color:#D8DBDE;font-size:9px;font-weight:700;letter-spacing:.75px;line-height:1;text-transform:uppercase}
.st-key-ecosystem_page .ecosystem-badge-official{border-color:#FF003A;color:#FFFFFF}
.st-key-ecosystem_page .ecosystem-badge-external_officially_linked{border-color:#B1B6BD;color:#F0F1F2}
.st-key-ecosystem_page .ecosystem-badge-community{border-color:#656B73;color:#C8CDD2}
.st-key-ecosystem_page .ecosystem-category{color:#777D85;font-size:9px;font-weight:700;letter-spacing:.8px;text-transform:uppercase}
.st-key-ecosystem_page .ecosystem-card-name{margin:0;color:#FFFFFF;font-size:17px;font-weight:700;letter-spacing:.65px;line-height:1.15;text-transform:uppercase}
.st-key-ecosystem_page .ecosystem-card-description{flex:1;margin:11px 0 17px;color:#9FA5AD;font-size:12px;line-height:1.5}
.st-key-ecosystem_page .ecosystem-card-visit{display:inline-flex;align-items:center;justify-content:space-between;width:100%;min-height:31px;box-sizing:border-box;padding:0 9px;border:1px solid #383C42;color:#E6E8EA!important;font-size:10px;font-weight:700;letter-spacing:1px;line-height:1;text-decoration:none!important}
.st-key-ecosystem_page .ecosystem-card-visit:hover,.st-key-ecosystem_page .ecosystem-card-visit:focus-visible{border-color:#FF003A;color:#FF003A!important;outline:none}
@media (min-width:769px){.st-key-ecosystem_page{margin-top:-44px!important}}
@media (max-width:1024px){.st-key-ecosystem_page .ecosystem-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:768px){.st-key-ecosystem_page .ecosystem-title{font-size:25px}.st-key-ecosystem_page .ecosystem-grid{grid-template-columns:1fr;gap:11px}.st-key-ecosystem_page .ecosystem-card{min-height:250px}.st-key-ecosystem_page .ecosystem-section{margin-top:25px}}
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
            st.markdown(
                f'<section class="ecosystem-section" aria-labelledby="ecosystem-{project_type}">'
                f'<h2 id="ecosystem-{project_type}" class="ecosystem-section-heading">{title}</h2>'
                f'<div class="ecosystem-grid">{cards}</div></section>',
                unsafe_allow_html=True,
            )
