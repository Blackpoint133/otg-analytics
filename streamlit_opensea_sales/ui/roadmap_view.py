"""Native Streamlit preview for the tracked public roadmap HTML."""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


def _roadmap_path() -> Path:
    """Resolve the repository roadmap without environment-specific paths."""
    return Path(__file__).resolve().parents[2] / "roadmap" / "otg_analytics_roadmap_english_cta.html"


def render_roadmap() -> None:
    """Render the tracked standalone roadmap document in a scrollable frame."""
    path = _roadmap_path()
    if not path.is_file():
        st.error("Roadmap preview is unavailable.")
        return
    try:
        html = path.read_text(encoding="utf-8")
    except OSError:
        st.error("Roadmap preview could not be loaded.")
        return
    components.html(html, height=1800, scrolling=True)
