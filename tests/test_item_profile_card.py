from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "streamlit_opensea_sales"))

from ui.item_profile_card import build_item_profile_card_html, item_profile_card_styles


def row(**overrides):
    value = {"item_name": "Cyrix", "rarity": "Epic", "_item_class": "Customization Item", "display_rank": "#8", "_supply": 15, "_supply_rank": 8, "image_url": "https://example.test/cyrix.png"}
    value.update(overrides)
    return value


def test_card_contains_complete_identity_and_metric_contract():
    html = build_item_profile_card_html(row(volume_gun=1, volume_usd=2, avg_price_gun=3, avg_price_usd=4, weighted_volume_gun=5, period_events=6, active_trading_days=7, market_strength_score=8, liquidity_score=9), "standalone")
    for text in ("Cyrix", "Epic", "Customization Item", "#8", "Market Strength", "Liquidity Score", "Volume GUN", "Volume USD", "Events", "Active Days", "Avg Price GUN", "Avg Price USD", "TOTAL SUPPLY", "SUPPLY RANK", "Data by GUNZscope"):
        assert text in html
    assert "Weighted Volume GUN" not in html


def test_missing_values_and_anomaly_rank_are_safe():
    html = build_item_profile_card_html(row(_supply_rank=None, market_strength_score=None), "overlay")
    assert "N/A" in html
    assert ">-</b>" in html
    assert "trader-profile" not in html


def test_standalone_and_overlay_share_metric_content():
    standalone = build_item_profile_card_html(row(volume_gun=12), "standalone")
    overlay = build_item_profile_card_html(row(volume_gun=12), "overlay")
    for text in ("Cyrix", "Volume GUN", "TOTAL SUPPLY", "SUPPLY RANK"):
        assert text in standalone and text in overlay
    assert "Weighted Volume GUN" not in standalone
    assert "Weighted Volume GUN" not in overlay


def test_image_is_contained_and_long_name_can_wrap():
    html = build_item_profile_card_html(row(item_name="A very long item name " * 5), "standalone")
    assert "object-fit:contain" in item_profile_card_styles()
    assert "overflow-wrap:anywhere" in item_profile_card_styles()
    assert "white-space:nowrap" not in html


def test_provider_only_row_has_no_item_analytics_link():
    html = build_item_profile_card_html(row(item_key=None), "standalone")
    assert 'class="top-item-profile-name" href=' not in html


def test_desktop_table_injects_shared_card_styles_before_overlay_markup():
    source = (Path(__file__).resolve().parents[1] / "streamlit_opensea_sales" / "ui" / "top_items_overview.py").read_text(encoding="utf-8")
    assert "table_html = item_profile_card_styles() +" in source
    assert "top-items-image-profile-overlay" in source
    assert "item_profile_card_styles()" in source


def test_desktop_overlay_media_is_square_and_wide():
    source = (Path(__file__).resolve().parents[1] / "streamlit_opensea_sales" / "ui" / "top_items_overview.py").read_text(encoding="utf-8")
    assert "grid-template-columns: 300px minmax(0, 1fr)" in source
    assert "width: 300px; height: 300px; aspect-ratio: 1 / 1" in source


def test_rarity_uses_existing_site_color_mapping():
    expected = {"Epic": "#a335ee", "Rare": "#0070dd", "Uncommon": "#1eff00", "Common": "#ffffff"}
    for rarity, color in expected.items():
        html = build_item_profile_card_html(row(rarity=rarity), "standalone")
        assert f'style="color:{color}"' in html
