"""Reusable sidebar trigger pattern for analytics section guides."""

from __future__ import annotations

import streamlit as st


def render_section_guide_panel(content: str) -> None:
    """Render the shared main-content shell for a section guide."""
    st.markdown(
        f'<div class="trader-metric-guide"><p>{content}</p></div>',
        unsafe_allow_html=True,
    )


def render_section_guide_button(section_key: str, *, label: str = "GUIDE") -> bool:
    """Render a section-scoped sidebar guide toggle and return its open state."""
    state_key = f"{section_key}_guide_open"
    control_key = f"{section_key}_guide"
    is_open = bool(st.session_state.get(state_key, False))
    st.sidebar.markdown(
        f"""<style>
        .st-key-{control_key} button {{
            width:100%!important;min-height:28px!important;height:28px!important;
            padding:4px 10px!important;margin-bottom:3px!important;
            font-family:'PP Supply Sans','Space Mono',monospace,sans-serif!important;
            background:#0a0a0a!important;color:#666!important;
            border:1px solid #333!important;border-radius:1px!important;
            font-size:10px!important;font-weight:700!important;
            text-transform:uppercase!important;letter-spacing:.5px!important;
        }}
        .st-key-{control_key} button:hover {{background:#0f0f0f!important;border-color:#444!important;color:#888!important;}}
        .st-key-{control_key} button[data-testid="stBaseButton-primary"] {{background:#FF003A!important;color:#FFFFFF!important;border-color:#FF003A!important;}}
        .st-key-{control_key} button[data-testid="stBaseButton-primary"]:hover {{background:#E60033!important;color:#FFFFFF!important;border-color:#FF003A!important;}}
        </style>""",
        unsafe_allow_html=True,
    )
    if st.sidebar.button(label, key=control_key, use_container_width=True, type="primary" if is_open else "secondary"):
        st.session_state[state_key] = not st.session_state.get(state_key, False)
        st.rerun()
    return bool(st.session_state.get(state_key, False))
