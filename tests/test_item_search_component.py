from pathlib import Path


ROOT = Path(__file__).parents[1]
SOURCE = (ROOT / "streamlit_opensea_sales" / "ui" / "item_search_component" / "index.html").read_text(encoding="utf-8")


def test_item_search_has_explicit_editing_ownership_and_render_guard():
    for value in (
        "focused=false",
        "editing=false",
        "selected=null",
        "browse=false",
        "q.onfocus",
        "q.oninput",
        "if(!(focused&&editing))q.value=selected?selected.display_name:''",
        "focused=true;editing=true;browse=false",
    ):
        assert value in SOURCE


def test_native_paste_uses_text_plain_and_redraws_without_select_event():
    assert "q.addEventListener('paste'" in SOURCE
    assert "e.clipboardData.getData('text/plain')" in SOURCE
    assert "e.preventDefault()" in SOURCE
    assert "q.value=q.value.slice(0,start)+text+q.value.slice(end)" in SOURCE
    paste_start = SOURCE.index("q.addEventListener('paste'")
    paste_end = SOURCE.index("q.onkeydown", paste_start)
    paste_block = SOURCE[paste_start:paste_end]
    assert "draw()" in paste_block
    assert "send({action:'select'" not in paste_block


def test_search_normalization_covers_clipboard_formatting_without_mutating_records():
    assert "function normalizeSearch(value)" in SOURCE
    for value in (
        "\\u200B-\\u200D\\uFEFF",
        "\\u00A0",
        "\\u2018\\u2019\\u201A\\u201B",
        "\\u201C\\u201D\\u201E\\u201F",
        "replace(/[\"']/g,'')",
        "replace(/\\s+/g,' ')",
    ):
        assert value in SOURCE
    assert "r.display_name" in SOURCE
    assert "r.item_key" in SOURCE


def test_paste_and_selection_emit_only_one_selection_protocol():
    assert SOURCE.count("send({action:'select'") == 1
    assert SOURCE.count("event_id:id()") == 1
    paste_start = SOURCE.index("q.addEventListener('paste'")
    paste_end = SOURCE.index("q.onkeydown", paste_start)
    assert "action:'select'" not in SOURCE[paste_start:paste_end]


def test_item_search_preserves_keyboard_mouse_escape_and_selected_marker_contracts():
    for value in (
        "ArrowDown",
        "ArrowUp",
        "Enter",
        "Escape",
        "q.onblur",
        "function restore()",
        "q.value=selected?selected.display_name:''",
        "selected-diamond",
        "rarity_color",
        "onmousedown",
        "No results",
        "localeCompare",
    ):
        assert value in SOURCE
