from pathlib import Path

from ui import sidebar


def test_visible_trader_sorts_exclude_roi_and_win_rate():
    assert sidebar.TRADER_VISIBLE_SORT_OPTIONS == ("EARNED", "INVESTED", "SOLD", "TRADES")
    source = (Path(sidebar.__file__)).read_text(encoding="utf-8")
    loop = source.split('with st.sidebar.container(key="trader_sort_controls"):', 1)[1].split("from ui.section_guide", 1)[0]
    assert "TRADER_VISIBLE_SORT_OPTIONS" in loop
    assert '"ROI"' not in loop
    assert '"WIN RATE"' not in loop


def test_internal_trader_metrics_remain_six():
    from ui import trader_overview

    assert trader_overview.SORT_OPTIONS == ["EARNED", "INVESTED", "SOLD", "TRADES", "ROI", "WIN RATE"]
