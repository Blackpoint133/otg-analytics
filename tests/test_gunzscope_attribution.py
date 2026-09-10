import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "streamlit_opensea_sales"))

from ui.gunzscope_attribution import LOGO_PATH, inline_logo, logo_data_uri  # noqa: E402


def test_gunzscope_logo_uses_prepared_asset_and_is_cached():
    assert LOGO_PATH.as_posix().endswith("img/gunz_scope/logo_1.png")
    assert logo_data_uri().startswith("data:image/png;base64,")
    assert logo_data_uri() is logo_data_uri()


def test_inline_logo_is_compact_and_reusable():
    markup = inline_logo("test-logo")
    assert 'class="test-logo"' in markup
    assert 'alt="GUNZscope"' in markup
    assert 'width="16" height="16"' in markup
