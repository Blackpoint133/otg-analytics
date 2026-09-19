import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
APP = ROOT / "streamlit_opensea_sales"
sys.path.insert(0, str(APP))

from ecosystem_catalog import (  # noqa: E402
    ALLOWED_CATEGORIES,
    ALLOWED_TYPES,
    EcosystemCatalogError,
    catalog_counts,
    load_ecosystem_catalog,
    validate_catalog_payload,
)
from feedback_store import normalize_source_mode  # noqa: E402
from ui.feedback import _back_label, _back_target, _source_label  # noqa: E402


def test_ecosystem_catalog_has_exact_v1_shape_and_classification_counts():
    projects = load_ecosystem_catalog()
    assert len(projects) == 12
    assert catalog_counts(projects) == {
        "official": 8,
        "external_officially_linked": 1,
        "community": 3,
    }
    ids = [project["id"] for project in projects]
    tracking_keys = [project["tracking_key"] for project in projects]
    assert len(ids) == len(set(ids))
    assert len(tracking_keys) == len(set(tracking_keys))
    assert ids == tracking_keys
    assert not {"otg_market_analytics", "black_point_analytics"}.intersection(ids)
    assert all(project["type"] in ALLOWED_TYPES for project in projects)
    assert all(project["category"] in ALLOWED_CATEGORIES for project in projects)
    assert all(project["url"].startswith("https://") for project in projects)
    assert all(project["source_url"].startswith("https://") for project in projects)
    assert all(project["name"].strip() and project["description"].strip() for project in projects)


def test_ecosystem_catalog_has_required_identity_classifications():
    projects = {project["id"]: project for project in load_ecosystem_catalog()}
    assert projects["opensea_otg"]["type"] == "external_officially_linked"
    assert projects["walletzero"]["type"] == "community"
    assert projects["gunzscope"]["type"] == "community"
    assert projects["off_the_grid"]["type"] == "official"


def test_ecosystem_catalog_rejects_invalid_enum_and_duplicate_identity():
    payload = json.loads((APP / "config" / "ecosystem_projects.json").read_text(encoding="utf-8"))
    invalid_type = json.loads(json.dumps(payload))
    invalid_type["projects"][0]["type"] = "untrusted"
    with pytest.raises(EcosystemCatalogError):
        validate_catalog_payload(invalid_type)

    duplicate_id = json.loads(json.dumps(payload))
    duplicate_id["projects"][1]["id"] = duplicate_id["projects"][0]["id"]
    with pytest.raises(EcosystemCatalogError):
        validate_catalog_payload(duplicate_id)


def test_ecosystem_page_uses_one_reusable_secure_card_contract():
    source = (APP / "ui" / "ecosystem.py").read_text(encoding="utf-8")
    assert "def _card_markup" in source
    assert 'target="_blank"' in source
    assert 'rel="noopener noreferrer"' in source
    assert "_asset_data_uri" in source
    assert 'f"data:{mime};base64,' in source
    assert "http" not in source[source.index("def _logo_markup"):source.index("def _card_markup")]
    assert "search" not in source.lower()
    assert "selectbox" not in source.lower()
    assert "st.tabs" not in source
    assert "repeat(4,minmax(0,1fr))" in source
    assert "repeat(5,minmax(0,1fr))" in source
    assert "repeat(2,minmax(0,1fr))" in source
    assert "grid-template-columns:1fr" in source
    assert "OFFICIAL ECOSYSTEM" in source
    assert "MARKETPLACES" in source
    assert "COMMUNITY ECOSYSTEM" in source
    assert "Gunzilla Games" in source


def test_ecosystem_route_is_top_level_and_bypasses_analytics_writers():
    nav = (APP / "ui" / "mode_switch.py").read_text(encoding="utf-8")
    app = (APP / "app_opensea_sales.py").read_text(encoding="utf-8")
    ecosystem = (APP / "ui" / "ecosystem.py").read_text(encoding="utf-8")

    assert "ecosystem" in nav
    assert 'href="/?mode=ecosystem"' in nav
    dropdown_start = nav.index('class="otg-nav-dropdown"')
    dropdown_end = nav.index("</div></details>", dropdown_start)
    assert "ecosystem" not in nav[dropdown_start:dropdown_end]
    assert "analytics_active = current_mode in ('item', 'market', 'top_items', 'trader')" in nav
    assert "min-height:36px" in nav
    assert "@media(max-width:768px)" in nav
    assert ".otg-nav-analytics,.otg-nav-analytics>summary{{width:auto;flex:0 0 auto}}" in nav
    assert ".otg-nav-dropdown{{width:176px;max-width:calc(100vw - 24px)}}" in nav

    branch = app.index('if requested_mode == "ecosystem":')
    sidebar_logo = app.index("render_sidebar_logo()")
    session = app.index("    record_current_session_once(")
    event = app.index("            record_product_event(")
    item_loading = app.index("items_index, diagnostics = load_items_index()")
    assert branch < sidebar_logo < session < event < item_loading
    ecosystem_block = app[branch:sidebar_logo]
    assert "render_ecosystem_page()" in ecosystem_block
    assert "render_sidebar_footer()" not in ecosystem_block
    assert "record_product_event" not in ecosystem


def test_ecosystem_v2_is_compact_directory_layout_and_other_routes_keep_sidebar():
    source = (APP / "ui" / "ecosystem.py").read_text(encoding="utf-8")
    app = (APP / "app_opensea_sales.py").read_text(encoding="utf-8")
    assert "aspect-ratio:1 / .92" in source
    assert "-webkit-line-clamp:2" in source
    assert "ecosystem-grid-marketplaces" in source
    assert "min-height:238px" not in source
    assert "min-height:205px" in source
    assert "padding:10px" in source
    assert "@media (max-width:1100px)" in source
    assert "@media (max-width:900px)" in source
    assert "width:100%;min-height:31px" not in source
    assert "st.sidebar.markdown" in app
    assert "render_sidebar_logo()" in app
    assert "render_sidebar_footer()" in app


def test_ecosystem_section_icons_are_48px_left_aligned_heading_row_assets():
    source = (APP / "ui" / "ecosystem.py").read_text(encoding="utf-8")
    heading_start = source.index(".ecosystem-section-heading{")
    heading_end = source.index(".ecosystem-section-heading .ecosystem-section-icon", heading_start)
    heading_rule = source[heading_start:heading_end]
    assert "display:grid" in heading_rule
    assert "grid-template-columns:48px max-content minmax(0,1fr)" in heading_rule
    assert "grid-template-rows:48px" in heading_rule
    assert "align-items:center" in heading_rule
    assert "display:flex" not in heading_rule
    assert ".ecosystem-section-heading .ecosystem-section-icon{display:block;grid-column:1;grid-row:1;width:48px;height:48px;object-fit:contain" in source
    assert ".ecosystem-section-heading .ecosystem-section-title{grid-column:2;grid-row:1;white-space:nowrap}" in source
    assert ".ecosystem-section-heading .ecosystem-section-divider{display:block;grid-column:3;grid-row:1;width:100%;height:1px" in source
    assert ".ecosystem-section-heading::after" not in source
    assert "img/section_ecosystem/OFFICIAL_ECOSYSTEM.png" in source
    assert "img/section_ecosystem/MARKETPLACES.png" in source
    assert "img/section_ecosystem/COMMUNITY_ECOSYSTEM.png" in source
    assert '<div class="ecosystem-section-heading" role="heading" aria-level="2">' in source
    assert 'class="ecosystem-section-title"' in source
    assert 'class="ecosystem-section-divider" aria-hidden="true"' in source
    assert '<h2 id="ecosystem-' not in source


def test_ecosystem_section_headings_use_custom_accessible_dom_without_streamlit_anchor_contract():
    source = (APP / "ui" / "ecosystem.py").read_text(encoding="utf-8")
    assert 'role="heading" aria-level="2"' in source
    assert 'aria-labelledby="{section_title_id}"' in source
    assert 'id="{section_title_id}" class="ecosystem-section-title"' in source
    assert 'class="ecosystem-section-divider" aria-hidden="true"' in source
    assert "<h1" not in source[source.index("for project_type, title in SECTION_ORDER:"):]
    assert "<h2" not in source[source.index("for project_type, title in SECTION_ORDER:"):]
    assert "aria-label=\"Link to heading\"" not in source


def test_ecosystem_feedback_is_display_and_back_navigation_safe_without_db_migration():
    feedback = (APP / "ui" / "feedback.py").read_text(encoding="utf-8")
    notifications = (APP / "feedback_notifications.py").read_text(encoding="utf-8")
    assert _source_label("ecosystem") == "ECOSYSTEM"
    assert _back_label("ecosystem") == "ECOSYSTEM"
    assert _back_target("ecosystem", None) == "/?mode=ecosystem"
    assert "ecosystem" in feedback
    assert '"ecosystem": "ECOSYSTEM"' in feedback
    assert '"ecosystem": "ECOSYSTEM"' in notifications
    assert normalize_source_mode("ecosystem") == "unknown"
    assert "SOURCE_MODES = {" in (APP / "feedback_store.py").read_text(encoding="utf-8")
    assert "ecosystem" not in (ROOT / "sql" / "create_user_feedback.sql").read_text(encoding="utf-8")


def test_ecosystem_asset_provenance_is_local_or_explicit_fallback_only():
    provenance_path = APP / "config" / "ecosystem_asset_sources.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["schema_version"] == 1
    projects = load_ecosystem_catalog()
    assert {asset["project_id"] for asset in provenance["assets"]} == {project["id"] for project in projects}
    assert all(not str(asset["local_asset_path"]).startswith("http") for asset in provenance["assets"])
    assert provenance["fallback_projects"] == []
    assert {icon["section"] for icon in provenance["section_icons"]} == {"official", "external_officially_linked", "community"}
    assert "img/gunz_scope/logo_2.png" in provenance["notes"]


def test_ecosystem_uses_prepared_project_and_section_assets():
    projects = load_ecosystem_catalog()
    assert all(project["logo_asset"].startswith("img/logo_projects/") for project in projects)
    assert all((ROOT / project["logo_asset"]).is_file() for project in projects)
    source = (APP / "ui" / "ecosystem.py").read_text(encoding="utf-8")
    assert "SECTION_ICONS" in source
    assert "img/section_ecosystem/OFFICIAL_ECOSYSTEM.png" in source
    assert "img/section_ecosystem/MARKETPLACES.png" in source
    assert "img/section_ecosystem/COMMUNITY_ECOSYSTEM.png" in source
    assert "ecosystem-section-icon" in source
