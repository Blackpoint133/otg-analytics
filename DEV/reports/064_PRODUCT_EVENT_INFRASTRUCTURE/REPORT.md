# Report 064 — Product Event Infrastructure

REPORT_SEQUENCE=064
RESULT=PASS

HEAD_BEFORE=f200afe0a8777740574e0df2098cdf7c4d7a01cb
MAIN_HEAD_BEFORE=dacee4c675419dea127ceb5e8a70e1a7ffc36a0

SOURCE_AUDIT=PASS

ARCHITECTURE=session_acquisition+specialized_item_events+general_product_events
PUBLIC_UI_INSTRUMENTATION_ADDED=NO
PUBLIC_UI_CHANGED=NO
VISITOR_DASHBOARD_UI_CHANGED=NO
SITE_ITEM_EVENTS_CHANGED=NO
SITE_ANALYTICS_CHANGED=NO

PRODUCT_EVENT_TABLE=public.site_product_events
PRODUCT_EVENT_WRITER=streamlit_opensea_sales/site_product_events.py
PRODUCT_EVENT_QUERY_LAYER=streamlit_opensea_sales/product_event_queries.py
PRODUCT_EVENT_SURFACES=item,market,top_items,trader
PRODUCT_EVENT_TYPES=surface_open,filter_apply,filter_clear,sort_change,period_change,view_change,toggle_change
ITEM_SELECT_DUPLICATED=NO

PARENT_SESSION_REQUIRED=YES
PARENT_SESSION_FK=YES
PARENT_SESSION_ON_DELETE_CASCADE=YES
IDENTITY_FIELDS_DUPLICATED_IN_PRODUCT_EVENTS=NO
RAW_WALLET_STORED=NO
RAW_USERNAME_STORED=NO
RAW_SEARCH_TEXT_STORED=NO
RAW_ITEM_SEARCH_STORED=NO
RAW_IP_STORED=NO
RAW_BROWSER_ID_STORED=NO
GENERIC_JSON_PAYLOAD=NO

OTG_PRODUCT_EVENTS_ENABLED_REQUIRED=YES
SESSION_STATE_DEDUPLICATION=YES
DATABASE_SEQUENCE_IDEMPOTENCY=YES
PRODUCT_EVENT_SEQUENCE_KEY=site_product_event_sequence
PRODUCT_EVENT_LAST_SURFACE_KEY=site_product_event_last_surface
PRODUCT_EVENT_CONTROL_STATES_KEY=site_product_event_control_states

STAGING_DB_TARGET_VERIFICATION=DISTINCT_FROM_PRODUCTION
DB_TARGET_DETAILS_REDACTED=YES
MIGRATION_APPLICATION_RESULT=APPLIED_TO_DISTINCT_STAGING_DATABASE
STAGING_PRODUCT_EVENT_TABLE_VERIFIED=YES
PRODUCT_EVENT_DB_ROLLBACK_TEST=PASS
INVALID_SHAPE_DB_REJECTION_TEST=PASS
PRODUCT_EVENT_QUERY_SMOKE_TEST=PASS

PRODUCT_EVENT_WRITER_TEST_COUNT=5
PRODUCT_EVENT_QUERY_TEST_COUNT=2
PRODUCT_EVENT_SCHEMA_TEST_COUNT=2
OTHER_RELEVANT_TEST_COUNT=123
TOTAL_RELEVANT_TEST_COUNT=132

PYTEST_RESULT=PASS
COMPILE=PASS
PIP_CHECK=PASS
DIFF_CHECK=PASS

IMPLEMENTATION_COMMIT_SHA=00f7db731e21a05015a8b6d999d48802d73209bf
IMPLEMENTATION_REMOTE_HEAD_VERIFIED=YES

STAGING_RESTART_RESULT=NOT_REQUIRED_INFRASTRUCTURE_NOT_WIRED

TRADES_COLOR=#8F78C6
TRADES_COLOR_CHANGED=NO

VISUAL_VALIDATION=NOT_REQUIRED_NO_PUBLIC_UI_CHANGE

PRODUCTION_DATABASE_CHANGED=NO
PRODUCTION_APPLICATION_CHANGED=NO
MAIN_CHANGED=NO

## Implementation scope

The implementation commit changed exactly these six files:

- `sql/create_site_product_events.sql`
- `streamlit_opensea_sales/site_product_events.py`
- `streamlit_opensea_sales/product_event_queries.py`
- `tests/test_site_product_events.py`
- `tests/test_product_event_queries.py`
- `tests/test_site_product_events_schema.py`

No existing application/UI file was changed. `site_item_events.py`,
`site_analytics.py`, the visitor dashboard, public navigation, custom
components, and all frozen analytics surfaces remain unchanged. The new
infrastructure is dormant: no public code imports or calls the writer, and no
dashboard UI was added.

## Event contract

The finite surfaces are `item`, `market`, `top_items`, and `trader`. The finite
event types are `surface_open`, `filter_apply`, `filter_clear`, `sort_change`,
`period_change`, `view_change`, and `toggle_change`. Python and PostgreSQL
both enforce the exact supported shapes: surface opens have no control/value;
ITEM wallet filters use `wallet_filter`; TOP ITEMS filters use
`item_class_filter`; TOP TRADERS filters use `trader_filter`; sort, period,
view, and toggle controls use only their specified allowlisted categorical
values. `item_select` and all free-form wallet, username, search, click,
hover, focus, and keypress payloads are rejected.

The table has a required foreign key to
`site_visit_sessions(session_id)` with `ON DELETE CASCADE`, a unique
`(parent_session_id, sequence_no)` idempotency key, positive sequence check,
surface/event allowlists, a defense-in-depth event-shape check, and the
time/surface/event index. It stores no duplicated identity or acquisition
fields and has no JSON/metadata payload.

The writer requires both the existing global analytics write guard and
`OTG_PRODUCT_EVENTS_ENABLED=true`, plus a recorded valid parent session. It
normalizes only categorical values, validates before connecting, uses a short
database timeout, catches failures, and logs only safe categorical/context
fields. Session state suppresses consecutive duplicate surface opens and
duplicate control states; filter apply → clear → apply remains valid. The
sequence advances and dedupe state changes only after an insert or confirmed
database duplicate; failures leave state unchanged.

The query layer reuses the dashboard `24H`, `7D`, `30D`, and `ALL` boundaries,
joins events to sessions, filters bots/internal traffic, counts events,
distinct sessions, and V2 browser visitors, and returns only the stable
aggregate columns. Its connection inherits read-only transaction mode and a
bounded statement timeout. No raw identity is exposed.

## Database and validation record

Staging and production targets were re-verified as distinct using local
configuration comparison; sensitive target details are intentionally omitted.
The schema was applied only to staging after the implementation commit was
remotely verified. The table, required columns, foreign key/cascade, unique
constraint, checks, and index were verified from PostgreSQL.

A rollback-only transaction inserted a synthetic parent session and valid
representatives for all event families. A SAVEPOINT test demonstrated that a
trader sort value resembling a wallet is rejected by PostgreSQL; the savepoint
and outer transaction were rolled back, leaving no synthetic rows. The
read-only 24H query smoke test passed with zero rows, as expected because
public UI instrumentation is explicitly deferred.

The staging application was intentionally not restarted: this is dormant
infrastructure only, with no public imports or calls. Production was not
connected for mutation, no production schema/application change occurred,
and no synthetic live product event was committed.

## Test and delivery record

Focused infrastructure tests passed: 5 writer, 2 query, and 2 schema tests.
The broader relevant suite passed 123 tests, covering site analytics, visitor
dashboard, ITEM search/event contracts, navigation, and trader search. Total
relevant tests: 132. Compileall, pip check, and diff check passed.

The implementation commit was pushed and independently verified at
`origin/develop = 00f7db731e21a05015a8b6d999d48802d73209bf`; the report-only
commit is the only subsequent commit for this report.
