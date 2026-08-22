"""
technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
"""

import base64
import streamlit as st

from config import (
    get_analytics_logo_path,
    OPENSEA_COLLECTION_URL,
    OPENSEA_ICON_URL,
    TWITTER_URL,
)

LEGAL_LINKS = (
    ("DISCLAIMER", "/legal/disclaimer"),
    ("PRIVACY", "/legal/privacy"),
    ("TERMS", "/legal/terms"),
)


def render_sidebar_footer():
    """technical documentation technical documentation technical documentation technical documentation technical documentation technical documentation technical documentation technical documentation."""
    try:
        with open(get_analytics_logo_path(), "rb") as f:
            developed_by_logo = (
                "data:image/png;base64,"
                + base64.b64encode(f.read()).decode()
            )
    except OSError:
        developed_by_logo = ""

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
                            <img class="footer-icon" src="{}" alt="OTG Analytics">
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
        developed_by_logo,
        legal_links_html,
    ), 
    unsafe_allow_html=True)
