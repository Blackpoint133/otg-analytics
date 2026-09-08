"""Reusable sidebar trigger pattern for analytics section guides."""

from __future__ import annotations

import streamlit as st


def render_section_guide_button(section_key: str, *, label: str = "GUIDE") -> bool:
    """Render a section-scoped sidebar guide toggle and return its open state."""
    state_key = f"{section_key}_guide_open"
    control_key = f"{section_key}_guide"
    st.sidebar.markdown(
        f"""<style>
        .st-key-{control_key} button {{
            width:100%!important;background:#000!important;color:#FFF!important;
            border:1px solid #333!important;border-radius:0!important;
            font-size:10px!important;letter-spacing:.08em!important;
        }}
        .st-key-{control_key} button:hover {{background:#181D27!important;border-color:#FF003A!important;}}
        </style>""",
        unsafe_allow_html=True,
    )
    if st.sidebar.button(label, key=control_key, use_container_width=True, type="secondary"):
        st.session_state[state_key] = not st.session_state.get(state_key, False)
        st.rerun()
    return bool(st.session_state.get(state_key, False))
