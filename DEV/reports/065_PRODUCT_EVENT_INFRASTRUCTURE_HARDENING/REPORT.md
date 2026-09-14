# Report 065 — Product Event Infrastructure Hardening

REPORT_SEQUENCE=065
RESULT=PASS

HEAD_BEFORE=68f589bd3eda074df6e829de25050f891689f2d0
MAIN_HEAD_BEFORE=dacee4c675419dea127ceb5e8a70e1a7ffc36a0

SOURCE_AUDIT=PASS

PUBLIC_UI_INSTRUMENTATION_ADDED=NO
PUBLIC_UI_CHANGED=NO
VISITOR_DASHBOARD_UI_CHANGED=NO
PRODUCT_EVENT_SCHEMA_CHANGED=NO
SITE_ITEM_EVENTS_CHANGED=NO
SITE_ANALYTICS_CHANGED=NO

SAFE_PRODUCT_SEQUENCE=YES
SAFE_PRODUCT_CONTROL_STATES=YES
MALFORMED_SEQUENCE_STATE_SAFE=YES
MALFORMED_CONTROL_STATE_SAFE=YES

GLOBAL_ANALYTICS_GATE_TESTED=YES
PRODUCT_EVENTS_GATE_TESTED=YES
MISSING_PARENT_TESTED=YES
INVALID_PARENT_UUID_TESTED=YES

DB_INSERT_SUCCESS_TESTED=YES
DB_DUPLICATE_TESTED=YES
DB_EXECUTE_FAILURE_TESTED=YES
DB_COMMIT_FAILURE_TESTED=YES
DB_DUPLICATE_ADVANCES_STATE=YES
DB_FAILURE_DOES_NOT_ADVANCE_STATE=YES

SURFACE_DEDUP_TESTED=YES
SURFACE_REENTRY_TESTED=YES
CONTROL_DEDUP_TESTED=YES
FILTER_REAPPLY_TESTED=YES
EXHAUSTIVE_VALID_EVENT_SHAPES_TESTED=YES
INVALID_EVENT_SHAPES_TESTED=YES

ITEM_SELECT_DUPLICATED=NO
RAW_REJECTED_INPUT_LOGGED=NO
SESSION_UUID_LOGGED=NO
RAW_EXCEPTION_MESSAGE_LOGGED=NO

QUERY_BEHAVIOR_MOCK_TESTED=YES
QUERY_RANGE_PARAMS_TESTED=YES
QUERY_RESOURCE_CLEANUP_TESTED=YES
QUERY_READ_ONLY_CONTRACT=YES

DATABASE_MIGRATION_REQUIRED=NO
STAGING_DATABASE_CHANGED=NO

PRODUCT_EVENT_WRITER_TEST_COUNT=76
PRODUCT_EVENT_QUERY_TEST_COUNT=4
PRODUCT_EVENT_SCHEMA_TEST_COUNT=2
OTHER_RELEVANT_TEST_COUNT=123
TOTAL_RELEVANT_TEST_COUNT=205

PYTEST_RESULT=PASS
COMPILE=PASS
PIP_CHECK=PASS
DIFF_CHECK=PASS

IMPLEMENTATION_COMMIT_SHA=212e76b0359bbe50894b1a2d79741a739790f70d
IMPLEMENTATION_REMOTE_HEAD_VERIFIED=YES

STAGING_RESTART_RESULT=NOT_REQUIRED_DORMANT_INFRASTRUCTURE

TRADES_COLOR=#8F78C6
TRADES_COLOR_CHANGED=NO

VISUAL_VALIDATION=NOT_REQUIRED_NO_PUBLIC_UI_CHANGE

PRODUCTION_DATABASE_CHANGED=NO
PRODUCTION_APPLICATION_CHANGED=NO
MAIN_CHANGED=NO

## Scope and hardening changes

The implementation commit changed exactly these three files:

- `streamlit_opensea_sales/site_product_events.py`
- `tests/test_site_product_events.py`
- `tests/test_product_event_queries.py`

No SQL, schema, public UI, dashboard UI, ITEM event, or session analytics
files changed. The only production-code change was hardening the dormant
writer: `_safe_product_sequence()` accepts only a non-negative integer and
returns zero for malformed state; `_safe_control_states()` copies only
well-formed categorical state entries. Both are used for deduplication and
post-commit advancement, so malformed Streamlit state cannot escape as a
public exception.

The writer now uses the canonical `site_analytics.RECORDED_KEY` and
`SESSION_ID_KEY`, preserves pre-DB gate/parent validation, and retains the
Report 064 finite vocabulary exactly. Successful inserts and `ON CONFLICT`
duplicates commit and advance sequence/dedupe state. Execute, fetch, and
commit failures roll back where possible, leave state unchanged, and return
False without re-raising. Surface dedupe remains consecutive-state based;
item → market → item is accepted. Control dedupe suppresses identical states
while filter apply → clear → apply remains accepted.

Focused tests exhaustively cover every finite valid categorical value and the
invalid combinations required by the contract, both independent write gates,
missing/invalid parent sessions, insert/duplicate/execute/commit outcomes,
malformed state, dedupe transitions, and log privacy. Rejected raw wallet-
and search-like sentinels, session UUIDs, and raw exception messages are not
logged. Query tests mock aggregate rows, verify exact 7-day half-open params,
column/value preservation, joins, bot/internal filters, V2 conditions, and
resource cleanup on success and failure. The query layer remains an internal
read-only layer and was not changed.

## Validation and delivery

The focused suite passed 82 tests: 76 writer, 4 query, and 2 schema-contract
tests. The broader regression suite passed 123 tests covering site analytics,
visitor dashboard, ITEM contracts, navigation, and trader search. Total
relevant tests: 205.

No migration was required or applied, no product event was generated, and
staging was intentionally not restarted because the infrastructure remains
dormant and is not imported by the public application. The implementation
commit was pushed and independently verified at
`origin/develop = 212e76b0359bbe50894b1a2d79741a739790f70d` with zero
ahead/behind divergence. The pre-existing untracked
`img/gunz_scope/logo_2.png` was left untouched.
