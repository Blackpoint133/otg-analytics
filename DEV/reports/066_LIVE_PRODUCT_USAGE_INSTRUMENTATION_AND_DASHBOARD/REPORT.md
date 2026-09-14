# Report 066 — Live Product Usage Instrumentation and Visitor Analytics Dashboard

REPORT_SEQUENCE=066
RESULT=IMPLEMENTATION_READY_BLOCKED_GLOBAL_ANALYTICS_DISABLED

HEAD_BEFORE=a341e3fee944625c0f378a36822f6146f98c3b4e
MAIN_HEAD_BEFORE=dacee4c675419dea127ceb5e8a70e1a7ffc36a0

SOURCE_AUDIT=PASS

PRODUCT_EVENTS_LIVE_INSTRUMENTATION=YES
SURFACE_OPEN_INSTRUMENTED=YES
ITEM_WALLET_FILTER_INSTRUMENTED=YES
ITEM_USD_TOGGLE_INSTRUMENTED=YES
ITEM_TREND_TOGGLE_INSTRUMENTED=YES
ITEM_VIEW_INSTRUMENTED=YES
ITEM_SELECT_DUPLICATED=NO
MARKET_USD_TOGGLE_INSTRUMENTED=YES
MARKET_TOKEN_PRICE_INSTRUMENTED=YES
MARKET_UNIQUE_WALLETS_INSTRUMENTED=YES
MARKET_PERIOD_INSTRUMENTED=YES
TOP_ITEMS_USD_TOGGLE_INSTRUMENTED=YES
TOP_ITEMS_CLASS_FILTER_INSTRUMENTED=YES
TOP_ITEMS_SORT_INSTRUMENTED=YES
TOP_ITEMS_PERIOD_INSTRUMENTED=YES
TOP_ITEMS_CLASS_NAMES_STORED=NO
TRADER_USD_CONTRACT_ADDED=YES
TRADER_USD_TOGGLE_INSTRUMENTED=YES
TRADER_FILTER_INSTRUMENTED=YES
TRADER_SORT_INSTRUMENTED=YES
TRADER_IDENTITY_STORED_IN_PRODUCT_EVENTS=NO

SEARCH_TEXT_TRACKED=NO
AUTOCOMPLETE_KEYSTROKES_TRACKED=NO
WALLETS_TRACKED_IN_PRODUCT_EVENTS=NO
USERNAMES_TRACKED_IN_PRODUCT_EVENTS=NO
PUBLIC_VISUAL_CHANGED=NO
PUBLIC_CALCULATIONS_CHANGED=NO

PRODUCT_USAGE_DASHBOARD_ADDED=YES
PRODUCT_USAGE_POSITION=AFTER_POST_PERFORMANCE_BEFORE_ITEM_INTEREST
PRODUCT_USAGE_SEPARATE_CACHE=YES
REFRESH_CLEARS_PRODUCT_CACHE=YES
PRODUCT_QUERY_FAILURE_ISOLATED=YES
PRODUCT_USAGE_METRICS=Product Events,Surface Opens,Feature Interactions,Latest Product Event
SURFACE_OPEN_CHART=YES
FEATURE_INTERACTIONS_CHART=YES
PRODUCT_INTERACTION_DETAIL_TABLE=YES
GLOBAL_UNIQUE_SESSION_SUMMATION_USED=NO
GLOBAL_UNIQUE_VISITOR_SUMMATION_USED=NO
SITE_ITEM_EVENTS_CHANGED=NO
SITE_ANALYTICS_SESSION_SEMANTICS_CHANGED=NO

STAGING_DB_TARGET_VERIFICATION=DISTINCT_FROM_PRODUCTION
DB_TARGET_DETAILS_REDACTED=YES
TRADER_USD_MIGRATION_FILE=sql/add_site_product_events_trader_usd_toggle.sql
TRADER_USD_MIGRATION_RESULT=APPLIED_TO_DISTINCT_STAGING_DATABASE
TRADER_USD_DB_ROLLBACK_TEST=PASS
INVALID_TRADER_USD_DB_REJECTION=PASS

STAGING_PRODUCT_EVENTS_ENABLE_RESULT=BLOCKED_GLOBAL_ANALYTICS_DISABLED
STAGING_PRODUCT_EVENTS_FLAG=NOT_ENABLED
GLOBAL_ANALYTICS_WRITE_GATE=false
PRODUCTION_ENV_UNCHANGED=YES
PRODUCT_EVENTS_STAGING_TRUST_BOUNDARY_UTC=PENDING

INSTRUMENTATION_TEST_COUNT=4
PRODUCT_EVENT_WRITER_TEST_COUNT=75
PRODUCT_EVENT_QUERY_TEST_COUNT=4
VISITOR_DASHBOARD_TEST_COUNT=28
OTHER_RELEVANT_TEST_COUNT=107
TOTAL_RELEVANT_TEST_COUNT=221

PYTEST_RESULT=PASS
COMPILE=PASS
PIP_CHECK=PASS
DIFF_CHECK=PASS

IMPLEMENTATION_COMMIT_SHA=0dc3db733045c3646d71942bb67d09ed2eb47abd
IMPLEMENTATION_REMOTE_HEAD_VERIFIED=YES
STAGING_RESTART_RESULT=BLOCKED_GLOBAL_ANALYTICS_DISABLED
STAGING_PID=NOT_RESTARTED
STAGING_EXPECTED_HEAD=NOT_RESTARTED
STAGING_SUPPLY_SOURCE=NOT_RESTARTED

TRADES_COLOR=#8F78C6
TRADES_COLOR_CHANGED=NO
VISUAL_VALIDATION=HUMAN_VALIDATION_REQUIRED
PRODUCTION_DATABASE_CHANGED=NO
PRODUCTION_APPLICATION_CHANGED=NO
MAIN_CHANGED=NO

## Implementation summary

The existing implementation commit changed exactly these nine files:

- `sql/create_site_product_events.sql`
- `sql/add_site_product_events_trader_usd_toggle.sql`
- `streamlit_opensea_sales/site_product_events.py`
- `streamlit_opensea_sales/app_opensea_sales.py`
- `streamlit_opensea_sales/ui/sidebar.py`
- `streamlit_opensea_sales/visitor_dashboard.py`
- `tests/test_site_product_events.py`
- `tests/test_site_product_events_schema.py`
- `tests/test_product_event_instrumentation.py`

The product-event contract was extended only for the previously missing
`trader / toggle_change / usd_price / on|off` shape. Public surface opens are
attempted after the canonical session writer, and existing controls emit only
validated categorical state changes. ITEM `item_select` remains exclusively
in `site_item_events`. Wallets, usernames, class names, search text,
autocomplete keystrokes, and other raw identity/user values are never passed
to product-event recording.

The dashboard now loads product aggregates through its separate cached query,
isolates product-query failure, clears both caches on Refresh, and renders the
required Product Usage section after Post Performance and before Item
Interest. It reports aggregate event counts without summing grouped distinct
counts, provides surface-open and feature charts, and provides the exact
privacy-safe interaction detail table.

## Staging safety decision

The staging and production database targets were re-verified as distinct and
all sensitive target details were redacted. The trader-USD migration was
applied only to staging. A rollback-only transaction accepted both `on` and
`off` trader USD events and rejected `banana`; no synthetic rows persisted.

The staging `.env` is ignored/local-only, but the existing global
`OTG_ANALYTICS_WRITES_ENABLED` gate is not true. Per the task safety contract,
the product-events flag was not enabled, no live telemetry was generated, and
staging was not restarted. Therefore this report does not claim live staging
instrumentation validation; the trust boundary remains pending until the
global gate is intentionally enabled through the approved operational path.
Production environment, database, and application were untouched.

## Validation and delivery

Focused tests passed: 4 instrumentation, 75 writer, 4 query, and 3 schema
tests, plus 28 visitor-dashboard tests, for 114 focused tests. The broader
relevant regression suite passed 107 tests. Total relevant tests: 221.
Compileall, pip check, and diff check passed. The implementation was already
present at `0dc3db733045c3646d71942bb67d09ed2eb47abd`, was pushed, and was
independently verified at `origin/develop` before staging migration work.
