"""
technical diagnostic text technical diagnostic text CSS technical diagnostic text technical diagnostic text Off The Grid.

technical diagnostic text technical diagnostic text technical diagnostic text CSS technical diagnostic text technical diagnostic text, technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text-technical diagnostic text.
"""

import streamlit as st

from config import FONT_FAMILY
from theme import OTG_THEME


def apply_global_styles():
    """
    technical diagnostic text technical diagnostic text technical diagnostic text CSS technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text-technical diagnostic text.
    
    technical diagnostic text:
    - technical diagnostic text CSS technical diagnostic text (--otg-*) technical diagnostic text technical diagnostic text technical diagnostic text
    - technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text !important
    - technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text Streamlit
    - technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    """
    
    # technical implementation note CSS technical implementation note (technical implementation note technical implementation note <style> technical implementation note)
    global_css_parts = []
    global_css_parts.append(OTG_THEME.to_css_variables())
    
    # technical implementation note technical implementation note
    global_css_parts.append(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=PP+Supply+Sans:wght@400;700&display=swap');
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text */
        body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {{
            font-family: {FONT_FAMILY};
            letter-spacing: 0.5px;
        }}
        
        /* technical diagnostic text technical diagnostic text - technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text */
        [data-testid="stSidebar"] {{
            border-right: 2px solid var(--otg-border);
            background-color: var(--otg-bg-secondary) !important;
        }}
        
        /* technical diagnostic text */
        h1, h2, h3, h4, h5, h6 {{
            font-family: {FONT_FAMILY};
            font-weight: 700;
        }}
        
        h3 {{
            border-bottom: 1px solid var(--otg-border);
            padding-bottom: 8px;
            text-transform: uppercase;
            font-size: 14px;
            letter-spacing: 1px;
        }}
        
        /* technical diagnostic text */
        a {{
            color: var(--otg-accent) !important;
            transition: color 0.1s linear;
        }}
        
        a:hover {{
            transition: color 0.1s linear;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text */
        [data-testid="stExpandSidebarButton"],
        [data-testid="stSidebarCollapseButton"] {{
            background-color: transparent !important;
            color: var(--otg-accent) !important;
            opacity: 0.9 !important;
        }}
        
        [data-testid="stExpandSidebarButton"]:hover,
        [data-testid="stSidebarCollapseButton"]:hover {{
            opacity: 1 !important;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text */
        button[kind="secondary"] {{
            border-radius: 0 !important;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text */
        button:has(+ input[type="hidden"][value*="prev_btn"]),
        button:has(+ input[type="hidden"][value*="next_btn"]) {{
            border: 2px solid #FF003A !important;
            background-color: #000000 !important;
            color: #FF003A !important;
            font-weight: 700 !important;
            width: 36px !important;
            height: 36px !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.1s linear !important;
            font-family: {FONT_FAMILY} !important;
        }}
        
        button:has(+ input[type="hidden"][value*="prev_btn"]):hover,
        button:has(+ input[type="hidden"][value*="next_btn"]):hover {{
            background-color: #FF003A !important;
            color: #000000 !important;
        }}
        
        button:has(+ input[type="hidden"][value*="prev_btn"]):disabled,
        button:has(+ input[type="hidden"][value*="next_btn"]):disabled {{
            opacity: 0.3 !important;
            cursor: not-allowed !important;
        }}
        </style>
    """)
    
    # technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
    global_css_parts.append(f"""
        <style>
        /* technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text */
        .otg-pagination button {{
            border: 2px solid #FF003A !important;
            background-color: #000000 !important;
            color: #FF003A !important;
            font-weight: 700 !important;
            width: 36px !important;
            height: 36px !important;
            padding: 0 !important;
            min-width: 36px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.1s linear !important;
            font-family: {FONT_FAMILY} !important;
            font-size: 16px !important;
            border-radius: 0 !important;
            margin: 0 auto !important;
        }}
        
        .otg-pagination button:hover:not(:disabled) {{
            background-color: #FF003A !important;
            color: #000000 !important;
        }}
        
        .otg-pagination button:disabled {{
            opacity: 0.3 !important;
            cursor: not-allowed !important;
        }}
        
        /* technical diagnostic text: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text */
        button[data-testid*="prev_btn"], 
        button[data-testid*="next_btn"] {{
            border: 2px solid #FF003A !important;
            background-color: #000000 !important;
            color: #FF003A !important;
            font-weight: 700 !important;
            width: 36px !important;
            height: 36px !important;
            padding: 0 !important;
            min-width: 36px !important;
            max-width: 36px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.1s linear !important;
            font-family: {FONT_FAMILY} !important;
            font-size: 16px !important;
            border-radius: 0 !important;
            margin: 0 auto !important;
        }}
        
        button[data-testid*="prev_btn"]:hover:not(:disabled),
        button[data-testid*="next_btn"]:hover:not(:disabled) {{
            background-color: #FF003A !important;
            color: #000000 !important;
        }}
        
        button[data-testid*="prev_btn"]:disabled,
        button[data-testid*="next_btn"]:disabled {{
            opacity: 0.3 !important;
            cursor: not-allowed !important;
        }}
        </style>
    """)
    
    # technical implementation note technical implementation note Expander technical implementation note
    global_css_parts.append(f"""
        <style>
        /* Expander technical diagnostic text */
        [data-testid="stExpander"] {{
            border: 2px solid var(--otg-border) !important;
            border-radius: 0 !important;
        }}
        
        [data-testid="stExpander"] details {{
            border-radius: 0 !important;
        }}
        
        [data-testid="stExpander"] summary {{
            padding: 12px 16px !important;
            margin: 0 !important;
            cursor: pointer;
            border-bottom: 1px solid var(--otg-border) !important;
            font-weight: 700;
        }}
        
        [data-testid="stExpander"] summary:hover {{
            background-color: var(--otg-surface-hover) !important;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text */
        [data-testid="stExpander"] * {{
            border-radius: 0 !important;
        }}
        </style>
    """)
    
    # technical implementation note technical implementation note technical implementation note (selectbox, date input, checkboxes)
    global_css_parts.append(f"""
        <style>
        /* Selectbox */
        [data-testid="stSelectbox"] {{
            border-bottom: 2px solid var(--otg-border) !important;
        }}
        
        [data-testid="stSelectbox"] input {{
            border: none !important;
            border-radius: 0 !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }}

        [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [role="listbox"], [role="option"] {{
            background-color: #080808 !important;
            color: #FFFFFF !important;
            border-color: var(--otg-border) !important;
        }}
        [data-testid="stSelectbox"] [data-baseweb="select"] span,
        [data-testid="stSelectbox"] [data-baseweb="select"] input,
        [data-testid="stSelectbox"] [data-baseweb="select"] svg {{
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
        }}
        [role="option"]:hover, [role="option"][aria-selected="true"] {{
            background-color: #252525 !important;
            color: #FFFFFF !important;
        }}
        
        /* Hide selectbox dropdown indicator */
        [data-testid="stSelectbox"] svg {{
            display: none !important;
        }}
        
        /* Date input */
        [data-testid="stDateInput"] {{  
            border-bottom: 2px solid var(--otg-border) !important;
        }}
        
        [data-testid="stDateInput"] input {{
            color: inherit !important;
            border: none !important;
            border-radius: 0 !important;
            font-family: {FONT_FAMILY};
        }}
        
        /* Checkbox */
        [data-testid="stCheckbox"] label {{
            font-family: {FONT_FAMILY};
            font-size: 13px;
        }}
        
        /* Number input */
        [data-testid="stNumberInput"] input {{
            color: inherit !important;
            border: none !important;
            border-radius: 0 !important;
            font-family: {FONT_FAMILY};
        }}
        
        /* Sidebar technical diagnostic text */
        [data-testid="stSidebar"] h2 {{
            color: var(--otg-accent) !important;
            border-bottom: 1px solid var(--otg-border);
            padding-bottom: 8px;
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 13px;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text */
        [data-testid="stNumberInput"] {{
            max-width: 120px;
            margin: 0 auto;
        }}
        </style>
    """)
    
    # technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
    global_css_parts.append(f"""
        <style>
        /* technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text */
        .sales-history-details {{
            border: 2px solid var(--otg-accent);
            border-radius: 0;
            background-color: var(--otg-bg-primary);
            margin-top: 20px;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text */
        .pagination-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
            margin-top: 20px;
            margin-bottom: 10px;
            padding: 0 10px;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text */
        .pagination-info {{
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 13px;
            color: var(--otg-text-secondary);
            margin-top: 10px;
            font-family: {FONT_FAMILY};
            letter-spacing: 0.5px;
        }}
        
        /* technical diagnostic text technical diagnostic text input technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text */
        .pagination-input {{
            width: 100%;
            max-width: 100px;
            text-align: center;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text */
        @media (max-width: 640px) {{
            .pagination-container {{
                gap: 10px;
                margin-top: 15px;
                margin-bottom: 8px;
            }}
            
            .pagination-info {{
                font-size: 12px;
                flex-direction: column;
                gap: 5px;
            }}
        }}
        </style>
    """)
    
    # technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
    global_css_parts.append(f"""
        <style>
        .metric-container {{
            margin-bottom: 1rem;
            padding: 12px;
            border-left: 2px solid var(--otg-accent);
            border-radius: 0;
            font-family: {FONT_FAMILY};
        }}
        
        .metric-label {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.4rem;
        }}
        
        .metric-value {{
            font-size: 16px;
            font-weight: 700;
            color: var(--otg-accent);
            font-family: {FONT_FAMILY};
        }}
        
        /* Reduce spacing for metric columns in market overview */
        [data-testid="stMetric"] {{
            margin-bottom: 0.8rem !important;
        }}
        
        [data-testid="stMetric"] > div:first-child {{
            margin-bottom: 0.2rem !important;
        }}
        </style>
    """)
    
    # technical implementation note technical implementation note technical implementation note technical implementation note
    global_css_parts.append(f"""
        <style>
        .sales-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 13px;
            border-radius: 0;
            overflow: hidden;
            border: 2px solid var(--otg-accent);
            font-family: {FONT_FAMILY};
        }}
        
        .sales-table thead tr {{
            color: var(--otg-accent);
            text-align: left;
            font-weight: 700;
            border-bottom: 2px solid var(--otg-accent);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 12px;
        }}
        
        .sales-table th, .sales-table td {{
            padding: 14px 15px;
            font-family: {FONT_FAMILY};
        }}
        
        .sales-table tbody tr {{
            border-bottom: 1px solid rgba(255, 0, 58, 0.2);
            transition: background-color 0.1s linear;
        }}
        
        .sales-table tbody tr:hover {{
            color: var(--otg-text-primary);
        }}
        
        .sales-table tbody tr:last-of-type {{
            border-bottom: 2px solid var(--otg-accent);
        }}
        
        .sales-table .link-cell a {{
            color: var(--otg-accent);
            text-decoration: underline;
            font-family: {FONT_FAMILY};
            transition: color 0.1s linear;
        }}
        
        .sales-table .link-cell a:hover {{
            color: var(--otg-text-primary);
        }}
        </style>
    """)
    
    # technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
    global_css_parts.append(f"""
        <style>
        .rarity-container {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 1rem;
        }}
        
        .rarity-dot {{
            width: 10px;
            height: 10px;
            border-radius: 0;
            display: inline-block;
            border: 1px solid currentColor;
        }}
        
        .rarity-text {{
            font-size: 0.9em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .rarity-common {{ color: var(--otg-text-primary); }}
        .rarity-uncommon {{ color: #1eff00; }}
        .rarity-rare {{ color: #0070dd; }}
        .rarity-epic {{ color: #a335ee; }}
        .rarity-legendary {{ color: #ff8000; }}
        
        .image-container {{
            padding: 10px;
            margin-bottom: 20px;
        }}
        
        .image-container img {{
            display: block;
            width: 100%;
            max-width: 100%;
            height: auto;
        }}
        </style>
    """)
    
    # technical implementation note technical implementation note technical implementation note
    global_css_parts.append(f"""
        <style>
        .otg-logo {{
            margin-bottom: 20px;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        
        .otg-logo img {{
            width: 100%;
            max-width: 250px;
            height: auto;
            display: block;
            margin: 0 auto;
            opacity: 0.85;
            transition: opacity 0.1s linear;
            filter: brightness(1.1) contrast(1.2);
        }}
        
        .otg-logo a:hover img {{
            opacity: 1;
            cursor: pointer;
            filter: brightness(1.2) contrast(1.3);
        }}
        </style>
    """)
    
    # technical implementation note technical implementation note footer
    global_css_parts.append(f"""
        <style>
        .sidebar-footer {{
            position: relative;
            width: 100%;
            padding: 12px 0;
            text-align: center;
            margin-top: auto;
            border-top: 2px solid var(--otg-accent);
        }}
        
        .footer-content {{
            margin: 0 auto;
            width: 100%;
        }}

        .footer-attribution-row {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            width: 100%;
            flex-wrap: nowrap;
        }}

        .footer-attribution-row .footer-section {{
            width: auto;
            flex: 0 0 auto;
            white-space: nowrap;
        }}

        .footer-attribution-separator {{
            flex: 0 0 auto;
            color: var(--otg-text-secondary);
            font-size: 11px;
            line-height: 1;
        }}
        
        .footer-section {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            font-size: 11px;
            width: 100%;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #FFFFFF !important;
        }}

        .footer-section span, .footer-attribution-separator {{
            color: #FFFFFF !important;
        }}
        
        .footer-divider {{
            width: 60%;
            height: 1px;
            background: linear-gradient(
                90deg,
                transparent 0%,
                rgba(255, 0, 58, 0.18) 18%,
                rgba(255, 0, 58, 0.55) 38%,
                var(--otg-accent) 50%,
                rgba(255, 0, 58, 0.55) 62%,
                rgba(255, 0, 58, 0.18) 82%,
                transparent 100%
            );
            margin: 6px auto 4px;
        }}
        
        .footer-icon {{
            height: 16px !important;
            width: 16px !important;
            transition: opacity 0.1s linear;
            filter: brightness(1.1);
        }}
        
        .sidebar-footer a {{
            text-decoration: none;
            transition: color 0.1s linear;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .sidebar-footer a:hover {{
            color: var(--otg-accent);
        }}

        .legal-footer-links {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            align-items: center;
            gap: 6px 8px;
            margin-top: 0;
            color: var(--otg-text-secondary);
            font-size: 10px;
            line-height: 1.4;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}

        .legal-footer-links a {{
            color: var(--otg-text-secondary) !important;
            font-size: inherit;
            line-height: inherit;
            text-decoration: none;
        }}

        .legal-footer-links a:hover {{
            color: var(--otg-accent) !important;
        }}
        </style>
    """)
    
    # technical implementation note technical implementation note technical implementation note technical implementation note
    global_css_parts.append(f"""
        <style>
        .support-section {{
            padding: 16px;
            border: 2px solid var(--otg-accent);
            background-color: var(--otg-surface);
            border-radius: 0;
        }}
        
        .support-text {{
            color: var(--otg-text-primary);
            margin-bottom: 1rem;
            font-family: {FONT_FAMILY};
        }}
        
        .wallet-label {{
            color: var(--otg-text-secondary);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }}
        
        .wallet-address {{
            color: var(--otg-accent);
            font-family: {FONT_FAMILY};
            font-weight: 700;
            padding: 8px 12px;
            background-color: var(--otg-bg-primary);
            border: 1px solid var(--otg-accent);
            border-radius: 0;
            word-break: break-all;
        }}
        </style>
    """)
    
    # technical implementation note technical implementation note technical implementation note technical implementation note
    global_css_parts.append(f"""
        <style>
        /* technical diagnostic text technical diagnostic text technical diagnostic text */
        .otg-pagination {{
            display: flex;
            justify-content: center;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 20px;
            margin-bottom: 10px;
            padding: 0 10px;
        }}
        
        /* technical diagnostic text technical diagnostic text (technical diagnostic text/technical diagnostic text) */
        .otg-pagination-btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            border: 2px solid #FF003A;
            background-color: #000000;
            color: #FF003A;
            font-family: {FONT_FAMILY};
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.1s linear;
            border-radius: 0;
            padding: 0;
        }}
        
        .otg-pagination-btn:hover:not(:disabled) {{
            background-color: #FF003A;
            color: #000000;
        }}
        
        .otg-pagination-btn:disabled {{
            opacity: 0.3;
            cursor: not-allowed;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text */
        .otg-pagination-number {{
            font-family: {FONT_FAMILY};
            font-size: 16px;
            font-weight: 700;
            color: #FF003A;
            min-width: 40px;
            text-align: center;
            letter-spacing: 0.5px;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text (technical diagnostic text X technical diagnostic text Y | technical diagnostic text Z) */
        .otg-pagination-info {{
            font-family: {FONT_FAMILY};
            font-size: 12px;
            color: #C8C8CD;
            text-align: center;
            width: 100%;
            margin-top: 4px;
            padding-top: 0;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text */
        @media (max-width: 640px) {{
            .otg-pagination {{
                gap: 10px;
                margin-top: 15px;
                margin-bottom: 8px;
            }}
            
            .otg-pagination-btn {{
                width: 32px;
                height: 32px;
                font-size: 14px;
            }}
            
            .otg-pagination-number {{
                font-size: 14px;
            }}
            
            .otg-pagination-info {{
                font-size: 11px;
            }}
        }}
        </style>
    """)
    
    # technical implementation note technical implementation note tooltip technical implementation note technical implementation note
    global_css_parts.append("""
        <style>
        .tooltip {
            position: relative;
            display: inline-block;
        }
        .tooltip .tooltiptext {
            visibility: hidden;
            background-color: rgba(0, 0, 0, 0.8);
            color: #fff;
            text-align: center;
            border-radius: 4px;
            padding: 5px 8px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            transform: translateX(-50%);
            font-size: 12px;
            white-space: nowrap;
        }
        .tooltip:hover .tooltiptext {
            visibility: visible;
        }
        </style>
    """)
    
    # technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note (technical implementation note technical implementation note technical implementation note)
    global_css_parts.append(f"""
        <style>
        /* technical diagnostic text technical diagnostic text technical diagnostic text - technical diagnostic text technical diagnostic text */
        .stApp {{
            background-color: #000000 !important;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text */
        [data-testid="stAppViewContainer"] {{
            background-color: #000000 !important;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text */
        [data-testid="stMain"] {{
            background-color: #000000 !important;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text */
        [data-testid="stMainBlockContainer"] {{
            background-color: #000000 !important;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text */
        .block-container {{
            background-color: #000000 !important;
        }}

        [data-testid="stStatusWidget"] {{
            display: none !important;
        }}

        @media (min-width: 769px) {{
            [data-testid="stMainBlockContainer"] {{
                padding-top: 5.25rem !important;
            }}

            .st-key-market_main_content,
            .st-key-top_items_main_content {{
                margin-top: 41.6px !important;
            }}
        }}
        
        /* technical diagnostic text technical diagnostic text - technical diagnostic text technical diagnostic text technical diagnostic text */
        [data-testid="stSidebar"] {{
            background-color: #000000 !important;
        }}
        
        /* technical diagnostic text technical diagnostic text technical diagnostic text */
        [data-testid="stSidebarNav"] {{
            background-color: #000000 !important;
        }}
        </style>
    """)
    
    # ════════════════════════════════════════════════════════════════
    # FINAL FIX: Header CSS at the very end to ensure override
    # ════════════════════════════════════════════════════════════════
    global_css_parts.append(
        "<style>"
        "header{background:#000000!important;}"
        "header[data-testid='stHeader']{background:#000000!important;}"
        ".stAppHeader{background:#000000!important;}"
        "</style>"
    )

    st._main.html("\n".join(global_css_parts))
