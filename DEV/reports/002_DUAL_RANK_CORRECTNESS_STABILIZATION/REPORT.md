# DUAL RANK CORRECTNESS STABILIZATION

REPORT_SEQUENCE=002
TASK_DIRECTORY=DEV/reports/002_DUAL_RANK_CORRECTNESS_STABILIZATION
RESULT=PASS

## Git baseline

HEAD_BEFORE=73cf9840986cef90dffb024cafd9169923723099
MAIN_HEAD_BEFORE=dacee4c675419dea127ceb5e8a70e1a7ffc36a0

## Implementation

IMPLEMENTATION_COMMIT_SHA=ab437d7c17626bc0a849ccca681ffdfe9634f9f5
IMPLEMENTATION_PARENT_SHA=abea36c03c31a5eaae6b513e30c34c4ac61605ea
IMPLEMENTATION_FILES_CHANGED=streamlit_opensea_sales/ui/top_items_overview.py; tests/test_top_items_multiclass_filter.py

## Audit and fix

DESKTOP_NAMEERROR=FIXED
TOTAL_SUPPLY_FILTER_RANK_ELIGIBILITY_BEFORE=numeric _supply only
TOTAL_SUPPLY_FILTER_RANK_ELIGIBILITY_AFTER=non-null centralized _supply_rank
SUPPLY_FILTER_RANK_VALUE_SOURCE=_supply
SUPPLY_EXCLUSION_POLICY_DUPLICATED_IN_UI=NO
EXCLUDED_ANOMALIES=visible Supply; Supply Rank, Global Rank, and Filter Rank remain -
ITEM_PROFILE_CARD_VISUAL_GEOMETRY_CHANGED=NO

## Semantics

FILTER_RANK_FIELD=_filter_rank
GLOBAL_RANK_FIELD=_global_rank
FILTER_RANK_ASSIGNMENT_STAGE=after class filtering / before pagination
MARKET_FILTER_RANK=sequential within filtered subset following global order
SUPPLY_FILTER_RANK=dense ascending Supply among rows with eligible _supply_rank
DESKTOP_RANK_LAYOUT=stacked red Filter Rank over light-gray Global Rank

## Validation

TESTS=66 focused tests passed
COMPILE=PASS
PIP_CHECK=PASS
DIFF_CHECK=PASS
STAGING_RESTART_RESULT=PASS
RUNTIME_RESULT=staging started at expected HEAD; desktop/runtime smoke path validated by application startup
VISUAL_VALIDATION=HUMAN_VALIDATION_REQUIRED

## Runtime

FINAL_RUNTIME_HEAD=ab437d7c17626bc0a849ccca681ffdfe9634f9f5
STAGING_SUPPLY_SOURCE=v3
STAGING_PID=50936

## Git after implementation

REMOTE_DEVELOP_AFTER_IMPLEMENTATION=ab437d7c17626bc0a849ccca681ffdfe9634f9f5
MAIN_HEAD_AFTER_IMPLEMENTATION=dacee4c675419dea127ceb5e8a70e1a7ffc36a0

## Report commit

REPORT_COMMIT_SHA=RECORDED IN GIT HISTORY
REMOTE_DEVELOP_AFTER_REPORT=RECORDED AFTER PUSH

## Safety

PRODUCTION_CHANGED=NO
BACKEND_CHANGED=NO
DATABASE_CHANGED=NO
PARSERS_CHANGED=NO
SCHEDULER_CHANGED=NO
CADDY_CHANGED=NO
MAIN_CHANGED=NO

## Notes

The desktop table regression was caused by interpolating `filter_rank` without assigning it in the table-row loop. The fix formats the row’s prepared `_filter_rank` locally. TOTAL SUPPLY now masks dense filtered ranking with the authoritative `_supply_rank` eligibility state, so excluded rows cannot shift eligible ranks. No card CSS, geometry, Trader code, or Supply exclusion policy was changed.
