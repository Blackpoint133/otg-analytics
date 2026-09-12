# TRADER CARD VIEWPORT FALLBACK

REPORT_SEQUENCE=019
RESULT=PARTIAL

HEAD_BEFORE=e119b08a7f4ca16212b46c7de304008e98f6f0d9
MAIN_HEAD_BEFORE=dacee4c675419dea127ceb5e8a70e1a7ffc36a0

ROOT_CAUSE=Trader cards were always top-anchored, allowing lower table rows to overflow below the visible table/viewport.
NORMAL_ROW_ALIGNMENT_PRESERVED=YES
LOWER_ROW_VIEWPORT_FALLBACK_ADDED=YES
TOP_ITEMS_BEHAVIOR_USED_AS_REFERENCE=YES

TABLE_LAYOUT_CHANGED=NO
CARD_INTERNAL_LAYOUT_CHANGED=NO
TRADING_STATS_CHANGED=NO
SEMANTICS_CHANGED=NO
UNRELATED_STYLE_CHANGES=NO

IMPLEMENTATION_COMMIT_SHA=57dd72d27c10b73d7fd520088db24c28e5a692c2
IMPLEMENTATION_PARENT_SHA=e119b08a7f4ca16212b46c7de304008e98f6f0d9
FILES_CHANGED=streamlit_opensea_sales/ui/trader_overview.py; tests/test_trader_profile_card.py

TESTS=37 passed (tests/test_trader_profile_card.py, tests/test_trader_overview.py)
COMPILE=PASS
PIP_CHECK=PASS
DIFF_CHECK=PASS

STAGING_RESTART_RESULT=PASS
STAGING_PID=429296
EXPECTED_HEAD_VERIFICATION=PASS (57dd72d27c10b73d7fd520088db24c28e5a692c2)
STAGING_SUPPLY_SOURCE=v3

VISUAL_VALIDATION=HUMAN_VALIDATION_REQUIRED
PRODUCTION_CHANGED=NO
MAIN_CHANGED=NO

The final six rows of each paginated Trader table page retain the approved
horizontal trigger/card geometry but use an upward vertical fallback. Normal
rows remain top-aligned at top:0; the existing 8px continuity helper preserves
the pointer path to the card.
