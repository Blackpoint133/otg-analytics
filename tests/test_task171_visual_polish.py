from pathlib import Path


ROOT = Path(__file__).parents[1]
APP = ROOT / "streamlit_opensea_sales"
ECOSYSTEM = (APP / "ui" / "ecosystem.py").read_text(encoding="utf-8")
ITEM = (APP / "ui" / "item_overview.py").read_text(encoding="utf-8")
TOP_ITEMS = (APP / "ui" / "top_items_overview.py").read_text(encoding="utf-8")
CONFIG = (APP / "config.py").read_text(encoding="utf-8")
STATUS_BAR = (APP / "ui" / "status_bar.py").read_text(encoding="utf-8")


def _function(source: str, name: str, next_name: str) -> str:
    start = source.index(f"def {name}(")
    end = source.index(f"def {next_name}(", start)
    return source[start:end]


def test_community_section_has_explicit_status_bar_clearance_without_card_changes():
    assert 'ecosystem-section-community" if project_type == "community"' in ECOSYSTEM
    assert ".ecosystem-section-community{margin-bottom:calc(var(--otg-status-bar-height, 32px) + 16px)}" in ECOSYSTEM
    assert "aspect-ratio:1 / .92" in ECOSYSTEM
    assert "ecosystem-card-logo-image" in ECOSYSTEM
    assert "repeat(5,minmax(0,1fr))" in ECOSYSTEM


def test_item_table_uses_local_twelve_row_page_without_changing_global_page_size():
    assert "ITEMS_PER_PAGE = 10" in CONFIG
    assert "ITEM_ANALYTICS_TABLE_PAGE_SIZE = 12" in ITEM
    assert "_render_item_sales_table(filtered_df, show_usd, current_gun_price, ITEM_ANALYTICS_TABLE_PAGE_SIZE, highlight_wallet)" in ITEM


def test_item_table_has_scoped_compact_bottom_margin_without_changing_global_table_rule():
    global_styles = (APP / "ui" / "styles.py").read_text(encoding="utf-8")
    assert ".st-key-item_sales_table_wrapper .sales-table {" in ITEM
    assert "margin-bottom: 8px !important" in ITEM
    assert ".sales-table {{" in global_styles
    assert "margin: 25px 0;" in global_styles


def test_item_pager_matches_approved_top_items_geometry_and_button_style():
    item_pager = _function(ITEM, "_render_item_table_pager", "_render_item_sales_table")
    top_pager = _function(TOP_ITEMS, "_render_top_items_pager", "_normalize_top_item_image_url")
    contracts = (
        "grid-template-columns:110px minmax(0,1fr) 110px",
        "justify-content:flex-start",
        "justify-content:center",
        "justify-content:flex-end",
        "width:110px!important",
        "background:#000!important",
        "color:#FFF!important",
        "border:1px solid #FF003A!important",
        "border-radius:0!important",
        "background:#FF003A!important; color:#000!important",
        "opacity:.35!important",
        'st.columns([1, 2, 1], gap="small")',
    )
    for contract in contracts:
        assert contract in item_pager
        assert contract in top_pager
    assert 'key="item_table_pagination"' in item_pager


def test_item_pager_always_renders_both_buttons_with_endpoint_disabled_states():
    pager = _function(ITEM, "_render_item_table_pager", "_render_item_sales_table")
    assert 'st.button("Previous", disabled=current_page <= 1' in pager
    assert 'st.button("Next", disabled=current_page >= total_pages' in pager
    assert pager.count("use_container_width=False") == 2
    assert 'st.query_params["page"] = str(current_page - 1)' in pager
    assert 'st.query_params["page"] = str(current_page + 1)' in pager
    assert "use_container_width=True" not in pager


def test_old_item_pager_divider_and_generic_wrapper_button_styles_are_removed():
    table = _function(ITEM, "_render_item_sales_table", "_filter_item_table_by_wallet")
    assert 'st.markdown("---")' not in table
    assert ".st-key-item_sales_table_wrapper button" not in ITEM
    assert "#11141C" not in ITEM
    assert "#181D27" not in ITEM
    assert "_render_item_table_pager(current_page, total_pages)" in table


def test_top_items_pager_and_task170_status_content_remain_approved():
    top_pager = _function(TOP_ITEMS, "_render_top_items_pager", "_normalize_top_item_image_url")
    assert 'key="top_items_pagination"' in top_pager
    assert 'disabled=page <= 1' in top_pager
    assert 'disabled=page >= pages' in top_pager
    assert "0x956cff3a596AD30D6A767DfFc3F70CDE97CD2667" in STATUS_BAR
    assert "OTG ANALYTICS //" in STATUS_BAR
    assert "--otg-status-bar-height:32px" in STATUS_BAR
