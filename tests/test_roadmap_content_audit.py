from pathlib import Path
import re


ROADMAP = (Path(__file__).parents[1] / "roadmap" / "otg_analytics_roadmap_english_cta.html").read_text(encoding="utf-8")


def test_roadmap_is_opensea_scoped_with_only_auto_buy_exception():
    assert ROADMAP.lower().count("in-game marketplace") == 1
    auto_buy = ROADMAP.index("AUTO-BUY ANALYTICS")
    assert auto_buy < ROADMAP.lower().index("in-game marketplace")
    assert ROADMAP.lower().index("in-game marketplace") < ROADMAP.index("</article>", auto_buy)
    outside_auto_buy = ROADMAP[:auto_buy] + ROADMAP[ROADMAP.index("</article>", auto_buy):]
    assert not re.search(r"in-game|in game", outside_auto_buy, re.I)
    assert not re.search(r"cross-market|cross market", ROADMAP, re.I)
    assert "IN-GAME + OPENSEA SALES OVERLAY" not in ROADMAP


def test_roadmap_reflects_current_live_products_and_interactions():
    assert "ITEM / MARKET / TOP ITEMS / TOP TRADERS" in ROADMAP
    assert "future in-game analytics" not in ROADMAP
    assert "TOP ITEMS ANALYTICS" in ROADMAP
    roadmap_upper = ROADMAP.upper()
    assert "TOTAL SUPPLY" in roadmap_upper and "FILTERED RANK" in roadmap_upper and "GLOBAL RANK" in roadmap_upper
    assert "Top Traders Analytics" in ROADMAP
    assert "IMAGE</strong> opens the detailed Trader Profile Card" in ROADMAP
    assert "standalone Trader Profile Cards" in ROADMAP
    assert "COVERAGE" in roadmap_upper and "MATCHED SALES" in roadmap_upper


def test_roadmap_stage_three_and_pipeline_are_opensea_scoped():
    assert "REAL-TIME OPENSEA ANALYTICS" in ROADMAP
    assert "ACTIVE LISTINGS + SALES OVERLAY" in ROADMAP
    assert "active OpenSea listings and completed OpenSea sales" in ROADMAP
    assert "observed OpenSea sales history" in ROADMAP
    assert "Break down observed OpenSea sales by OTG item class" in ROADMAP
    assert "5 in-game classes" not in ROADMAP
    assert "auto-buy bot or script" in ROADMAP
    assert "explainable probability score" in ROADMAP
