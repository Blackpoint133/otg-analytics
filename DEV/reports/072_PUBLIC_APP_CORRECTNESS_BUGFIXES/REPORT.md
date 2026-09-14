# Report 072 — Public App Correctness Bugfixes

REPORT_SEQUENCE=072
RESULT=PASS
HEAD_BEFORE=52da6f2d1675ba5f3dab45b41483a3a2570bcedf
MAIN_HEAD_BEFORE=dacee4c675419dea127ceb5e8a70e1a7ffc36a0
SOURCE_AUDIT=PASS

TRADER_VISIBLE_SORT_OPTIONS=EARNED,INVESTED,SOLD,TRADES
ROI_SIDEBAR_SORT_ADDED=NO
WIN_RATE_SIDEBAR_SORT_ADDED=NO
TRADER_GUIDE_PROFILE_RANK_CLARIFIED=YES

TOP_ITEMS_PD_NA_ROOT_CAUSE=unsafe scalar value != value checks evaluated pandas.NA
TOP_ITEMS_PD_NA_CRASH_FIXED=YES
TOP_ITEMS_CURRENT_ROWS_CARD_BUILD_ERRORS=0

SILENCE_HAT_ITEM_FOUND=YES
SILENCE_HAT_ORIGINAL_FILE=silence_hat_epic.csv
SILENCE_HAT_ORIGINAL_ROWS=9
SILENCE_HAT_ORIGINAL_DATE_MIN=2025-07-27
SILENCE_HAT_ORIGINAL_DATE_MAX=2026-07-16
SILENCE_HAT_ENRICHED_FILE_EXISTS=YES
SILENCE_HAT_ENRICHED_ROWS=10
SILENCE_HAT_ENRICHED_REQUIRED_COLUMNS=PASS
SILENCE_HAT_ENRICHED_USD_ROWS=10
SILENCE_HAT_ENRICHED_GUN_USD_ROWS=10
SILENCE_HAT_HISTORICAL_USD_STATUS_BEFORE=enriched_merge_rejected
SILENCE_HAT_SALES_WITHIN_PRICE_HISTORY_RANGE=9/9
SILENCE_HAT_SALES_WITH_EXACT_PRICE_DATE=9/9
SILENCE_HAT_CAUSE=OTHER_PROVEN_CAUSE
SILENCE_HAT_CANONICAL_SOURCE_ENRICHED_EXISTS=YES
SILENCE_HAT_CANONICAL_SOURCE_ENRICHED_ROWS=10
SILENCE_HAT_CANONICAL_SOURCE_USD_ROWS=10
SILENCE_HAT_RESULT=FIXED
SILENCE_HAT_HISTORICAL_USD_AVAILABLE_AFTER=true
SILENCE_HAT_LOADER_USD_ROWS_AFTER=10
CURRENT_PRICE_USED_AS_HISTORICAL_FALLBACK=NO

TRADER_WALLETS_TOTAL=1342
PERSISTED_FALLBACK_NAMES_BEFORE=1342
TRADER_WALLETS_WITHOUT_PERSISTED_FALLBACK_BEFORE=0
WALLET_LIKE_DISPLAY_NAMES=3
WALLET_LIKE_USERNAMES=3
RAW_WALLET_DISPLAY_NAME_LEAKS_BEFORE=3
PERSISTED_FALLBACK_NAMES_AFTER=1342
TRADER_WALLETS_WITHOUT_PERSISTED_FALLBACK_AFTER=0
RAW_WALLET_DISPLAY_NAME_LEAKS_AFTER=0
CURRENT_NON_HUMAN_TRADERS_WITHOUT_NONAME=0
CURRENT_DUPLICATE_NONAME_ALIASES=0
NONAME_NAMESPACE_FORMAT=NoName####
NONAME_EXISTING_ALIASES_PRESERVED=YES
PROFILE_HOUSEKEEPING_NETWORK_REQUESTS=0

TARGETED_TESTS=122 passed
FULL_TESTS=576 passed, 4 unrelated pre-existing failures, 5 subtests passed
COMPILE=PASS
PIP_CHECK=PASS
DIFF_CHECK=PASS

IMPLEMENTATION_FILES=scripts/refresh_common_data.py;streamlit_opensea_sales/opensea_account_profiles.py;streamlit_opensea_sales/ui/item_profile_card.py;streamlit_opensea_sales/ui/sidebar.py;streamlit_opensea_sales/ui/trader_overview.py;tests/test_item_profile_card.py;tests/test_opensea_account_profiles.py;tests/test_refresh_common_data.py;tests/test_section_guide.py;tests/test_trader_search.py
IMPLEMENTATION_COMMIT_SHA=b0df347839257a847209af597d1aeec93c59c598

STAGING_RESTART_RESULT=PASS
STAGING_HEAD=b0df347839257a847209af597d1aeec93c59c598
STAGING_PORT=8504
STAGING_SUPPLY_SOURCE=v3

APPLICATION_VISUAL_VALIDATION=HUMAN_VALIDATION_REQUIRED
PRODUCTION_DATABASE_CHANGED=NO
PRODUCTION_APPLICATION_CHANGED=NO
PRODUCTION_ENVIRONMENT_CHANGED=NO
PRODUCTION_DATA_CHANGED=NO
PRODUCTION_RESTARTED=NO
MAIN_CHANGED=NO

The Silence Hat defect was a stale staging original-sales file: the canonical
source had matching enriched historical USD data, while staging had fewer
original rows and the loader rejected reconciliation. The existing common-data
refresh workflow was extended to synchronize both original and enriched sales
files; no pricing fallback or ad-hoc CSV edit was used. After refresh the
loader returned 10 rows with 10 historical USD values. One sale date was beyond
the historical price-file range, but the canonical enriched source supplied
transaction-time USD data.

The profile housekeeping command was run on staging with `--limit 0`; it made
zero OpenSea/API requests and persisted fallback aliases for all 1,342 current
trader wallets. Effective aliases are shared by trader rendering and search,
reject wallet-like profile labels, preserve existing aliases, and remain
collision-free.

The full suite’s four failures are unrelated existing contracts:
`test_item_analytics_panel.py::test_final_item_and_market_guide_copy_is_present`,
`test_market_visual_refinement.py::test_all_desktop_mode_containers_share_pre_trader_zero_offset`,
`test_top_items_supply.py::test_total_supply_render_does_not_require_market_rank`,
and `test_trader_profile_sync.py::test_trader_visible_title_is_renamed`.
They were not changed.
