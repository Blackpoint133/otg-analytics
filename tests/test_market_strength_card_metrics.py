from pathlib import Path


SOURCE = (Path(__file__).parents[1] / "streamlit_opensea_sales" / "ui" / "top_items_overview.py").read_text(encoding="utf-8")


def test_market_strength_card_omits_total_supply_but_keeps_supply_rank():
    start = SOURCE.index("# Market Strength mode: main metric")
    end = SOURCE.index("elif ranking_mode == 'total_supply':", start)
    block = SOURCE[start:end]
    assert "Volume Rank" in block and "Liquidity Rank" in block
    assert "if ranking_mode != 'market_strength'" in SOURCE
    assert "TOTAL SUPPLY" in SOURCE and "SUPPLY RANK" in SOURCE


def test_other_card_modes_keep_total_supply_branch():
    assert "if ranking_mode != 'market_strength':" in SOURCE
    assert "ranking_mode == 'total_supply'" in SOURCE
