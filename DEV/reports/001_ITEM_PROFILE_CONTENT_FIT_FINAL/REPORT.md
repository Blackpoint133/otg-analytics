# ITEM PROFILE CONTENT FIT FINAL

REPORT_SEQUENCE=001
TASK_DIRECTORY=DEV/reports/001_ITEM_PROFILE_CONTENT_FIT_FINAL
RESULT=PARTIAL

## Git baseline

HEAD_BEFORE=7d21ee7f8ccbd93c4233e7f572eb0443cf3bd3ad
MAIN_HEAD_BEFORE=dacee4c675419dea127ceb5e8a70e1a7ffc36a0

## Implementation

IMPLEMENTATION_COMMIT_SHA=7d21ee7f8ccbd93c4233e7f572eb0443cf3bd3ad
IMPLEMENTATION_PARENT_SHA=9aacdfb4d7d9d81d4c1ec133ed3614cf546428f1
IMPLEMENTATION_FILES_CHANGED=streamlit_opensea_sales/ui/top_items_overview.py; tests/test_item_profile_card.py

## Validation

TESTS=49 relevant tests passed
COMPILE=PASS
PIP_CHECK=PASS
DIFF_CHECK=PASS
VISUAL_VALIDATION=HUMAN_VALIDATION_REQUIRED

## Runtime

STAGING_RESTART_RESULT=PASS
FINAL_RUNTIME_HEAD=7d21ee7f8ccbd93c4233e7f572eb0443cf3bd3ad

## Git after implementation

REMOTE_DEVELOP_AFTER_IMPLEMENTATION=7d21ee7f8ccbd93c4233e7f572eb0443cf3bd3ad
MAIN_HEAD_AFTER_IMPLEMENTATION=dacee4c675419dea127ceb5e8a70e1a7ffc36a0

## Provenance

SUBSEQUENT_APPLICATION_COMMIT_BEFORE_REPORT=2adba6b1e4668002f8bec6b2e790563806eecf55
SUBSEQUENT_APPLICATION_COMMIT_DESCRIPTION=Add filtered and global item ranks
APPLICATION_SOURCE_CHANGED_BY_REPORT_COMMIT=NO

## Safety

PRODUCTION_CHANGED=NO
BACKEND_CHANGED=NO
DATABASE_CHANGED=NO
PARSERS_CHANGED=NO
SCHEDULER_CHANGED=NO
CADDY_CHANGED=NO

## Notes

The legacy report recorded: outer-card height was auto; the Item Profile square was 350px; meta spacing was reduced from `8px 0 14px` to `8px 0 10px`; non-last section spacing was reduced from `12px` to `9px`; Supply retained `margin-top:auto`; no overflow-hidden workaround was used; mobile and Trader layouts were unchanged. The legacy result remains PARTIAL because computed visual validation was not available.

This report is an archival import of the legacy report. The current checkout was already beyond the historical implementation commit; no application changes were made while establishing tracked reporting.
