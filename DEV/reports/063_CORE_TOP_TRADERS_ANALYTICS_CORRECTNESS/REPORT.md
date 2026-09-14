# Report 063 — Core TOP TRADERS Analytics Correctness

REPORT_SEQUENCE=063
RESULT=PASS

HEAD_BEFORE=48b8f74edaf350cabac5b1f36f0ec5f10794c93d
MAIN_HEAD_BEFORE=dacee4c675419dea127ceb5e8a70e1a7ffc36a0

SOURCE_AUDIT=PASS

SESSION_ANALYTICS_SEMANTICS=ONE_INITIAL_SURFACE_PER_STREAMLIT_SESSION
TRUE_PAGEVIEW_TRACKING=NO
PRODUCT_EVENT_TRACKING_ADDED=NO
SITE_PRODUCT_EVENTS_ADDED=NO

CANONICAL_ANALYTICS_MODES=item,market,top_items,trader
TRADER_PYTHON_ALLOWLIST=YES
TRADER_NORMALIZES_TO_TRADER=YES
TRADER_ITEM_KEY=NULL
UNKNOWN_MODE_FALLBACK=item

CANONICAL_SCHEMA_TRADER_MODE=YES
TRADER_MODE_MIGRATION_FILE=sql/add_site_visit_trader_mode.sql
MIGRATION_IDEMPOTENT=YES
MIGRATION_TRANSACTION_WRAPPED=YES

STAGING_DB_TARGET_VERIFICATION=DISTINCT_FROM_PRODUCTION
DB_TARGET_DETAILS_REDACTED=YES
MIGRATION_APPLICATION_RESULT=APPLIED_TO_DISTINCT_STAGING_DATABASE
STAGING_CONSTRAINT_TRADER_ACCEPTED=YES
TRADER_DB_ROLLBACK_INSERT_TEST=PASS
TRADER_MODE_STAGING_TRUST_BOUNDARY_UTC=2026-09-14T06:28:15Z

DASHBOARD_TRADER_LABEL=Top Traders Analytics
DASHBOARD_MODE_SECTION=Initial Analytics Surface
DASHBOARD_SESSION_SEMANTIC_CAPTION=YES
POST_PERFORMANCE_TRADER_COLUMN=YES
VISITOR_TIMELINE_TRADER_LABEL=YES
ITEM_INTEREST_REMAINS_ITEM_ONLY=YES

ITEM_EVENTS_CHANGED=NO
PUBLIC_NAVIGATION_CHANGED=NO
REPORT_061_NAV_VISUAL_CHANGED=NO
TRADER_FILTER_CHANGED=NO
TRADER_CALCULATIONS_CHANGED=NO
ITEM_COMPONENTS_CHANGED=NO
SHARED_LAYOUT_CHANGED=NO
FEEDBACK_CHANGED=NO
ROADMAP_CHANGED=NO

TRADES_COLOR=#8F78C6
TRADES_COLOR_CHANGED=NO

SITE_ANALYTICS_TEST_COUNT=36
VISITOR_DASHBOARD_TEST_COUNT=28
OTHER_RELEVANT_TEST_COUNT=57
TOTAL_RELEVANT_TEST_COUNT=121

PYTEST_RESULT=PASS
COMPILE=PASS
PIP_CHECK=PASS
DIFF_CHECK=PASS

IMPLEMENTATION_COMMIT_SHA=d756a943d7d93a103f4cf38921d48fde43af6c43

STAGING_RESTART_RESULT=PASS
STAGING_PID=145344
STAGING_EXPECTED_HEAD=d756a943d7d93a103f4cf38921d48fde43af6c43
STAGING_SUPPLY_SOURCE=v3

VISUAL_VALIDATION=NOT_REQUIRED_NO_PUBLIC_UI_CHANGE

PRODUCTION_DATABASE_CHANGED=NO
PRODUCTION_APPLICATION_CHANGED=NO
MAIN_CHANGED=NO

## Audit and implementation record

The source chain was audited before implementation. `mode_switch.py` accepts
the public `trader` canonical mode (including the `top_traders` alias), and
`app_opensea_sales.py` passes it to `record_current_session_once()` before the
trader rendering branch. The former `site_analytics.py` allowlist excluded
`trader` and `build_session_record()` mapped every unknown value to `item`.
The former database CHECK constraint and dashboard mode labels/post columns
also omitted it. This task changed that chain end-to-end without changing the
one-record-per-Streamlit-session semantics.

`VALID_MODES` now contains exactly `item`, `market`, `top_items`, and `trader`.
Known `trader` records remain `trader` and always have `item_key = None`, even
when an unrelated item query parameter is present. Truly unknown values retain
the safe `item` fallback. The fresh-install schema and the new atomic,
conditional `sql/add_site_visit_trader_mode.sql` migration use the same
four-mode contract. The migration inspects the existing constraint and does
not recreate it when `trader` is already allowed.

The dashboard now labels `trader` as `Top Traders Analytics`, calls the mode
chart **Initial Analytics Surface**, and displays the required caption about
one initial surface per recorded Streamlit session. Both bounded and ALL
campaign/post query branches expose the `trader` count, displayed as
**Top Traders**. ITEM interest and ITEM activity remain explicitly
`s.mode = 'item'` / item-event scoped.

The staging database target was verified distinct from production using local
configuration comparison; sensitive target details are intentionally omitted.
The migration was applied only to staging. The constraint accepted all four
modes, and a synthetic minimal trader insert succeeded inside a transaction
and was rolled back. Trust begins at the recorded UTC verification boundary;
historical rows before the correction remain subject to the ambiguity
documented by Report 062. Staging was restarted at the implementation SHA,
on port 8504 with SupplySource v3; no synthetic visit was generated.

The implementation commit changed exactly these files:

- `sql/add_site_visit_trader_mode.sql`
- `sql/create_site_visit_sessions.sql`
- `streamlit_opensea_sales/site_analytics.py`
- `streamlit_opensea_sales/visitor_dashboard.py`
- `streamlit_opensea_sales/visitor_dashboard_queries.py`
- `tests/test_site_analytics.py`
- `tests/test_visitor_dashboard.py`
- `tests/test_site_visit_trader_mode_migration.py`

No public UI, navigation, ITEM events, trader controls/calculations, shared
layout, feedback, roadmap, production database, or production application
was changed.

## Validation notes

The staging virtualenv test runs passed: 36 site-analytics tests, 28 visitor
dashboard tests, and 57 other relevant routing/UI regression tests, for 121
tests total. Compileall, pip check, and diff check passed. The pre-existing
untracked `img/gunz_scope/logo_2.png` was left untouched.
