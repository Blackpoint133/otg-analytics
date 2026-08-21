"""
technical diagnostic text technical diagnostic text (loader).

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
"""

import base64
import streamlit as st
from config import get_assets_loading_image


def show_loader():
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    technical diagnostic text-technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    """
    loading_image_path = get_assets_loading_image()
    
    try:
        with open(loading_image_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode()
    except Exception:
        # Fallback: technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note, technical implementation note technical implementation note technical implementation note
        img_base64 = ""
    
    st._main.html(f"""
    <style>
    @keyframes loading {{
        0% {{ left: -40%; }}
        100% {{ left: 100%; }}
    }}

    @keyframes fadeOut {{
        0% {{ opacity: 1; }}
        100% {{ opacity: 0; }}
    }}

    #loader-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: #000000;
        z-index: 999999;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        animation: fadeOut 0.5s ease-in-out 3s forwards;
        pointer-events: none;
    }}

    #loader-image {{
        max-width: 300px;
        margin-bottom: 30px;
    }}

    #loader-bar {{
        width: 200px;
        height: 3px;
        background: #111;
        overflow: hidden;
        position: relative;
    }}

    #loader-bar::before {{
        content: "";
        position: absolute;
        left: -40%;
        width: 40%;
        height: 100%;
        background: #FF003A;
        animation: loading 1.2s infinite;
    }}
    </style>

    <div id="loader-overlay">
        {f'<img id="loader-image" src="data:image/png;base64,{img_base64}">' if img_base64 else ''}
        <div id="loader-bar"></div>
    </div>
    """)
