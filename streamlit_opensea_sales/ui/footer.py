"""
technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
"""

import streamlit as st

from config import (
    OPENSEA_COLLECTION_URL,
    OPENSEA_ICON_URL,
    TWITTER_URL,
    BLACKPOINT_LOGO_URL
)

LEGAL_LINKS = (
    ("DISCLAIMER", "/legal/disclaimer"),
    ("PRIVACY", "/legal/privacy"),
    ("TERMS", "/legal/terms"),
)


def render_sidebar_footer():
    """technical documentation technical documentation technical documentation technical documentation technical documentation technical documentation technical documentation technical documentation."""
    legal_links_html = " / ".join(
        f'<a href="{href}">{label}</a>' for label, href in LEGAL_LINKS
    )
    st.sidebar.markdown("""
        <div class="sidebar-footer">
            <div class="footer-content">
                <div class="footer-attribution-row">
                    <div class="footer-section">
                        <span>Provided by</span>
                        <a href="{}" target="_blank">
                            <img class="footer-icon" src="{}" alt="OpenSea">
                        </a>
                    </div>
                    <span class="footer-attribution-separator" aria-hidden="true">/</span>
                    <div class="footer-section">
                        <span>Developed by</span>
                        <a href="{}" target="_blank">
                            <img class="footer-icon" src="{}" alt="Twitter">
                        </a>
                    </div>
                </div>
            </div>
            <div class="footer-divider" aria-hidden="true"></div>
            <div class="legal-footer-links">{}</div>
        </div>
    """.format(
        OPENSEA_COLLECTION_URL,
        OPENSEA_ICON_URL,
        TWITTER_URL,
        BLACKPOINT_LOGO_URL,
        legal_links_html,
    ), 
    unsafe_allow_html=True)
