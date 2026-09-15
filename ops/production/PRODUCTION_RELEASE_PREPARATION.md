# Report 105 production update preparation

STATUS=BLOCKED_PG_DUMP_UNAVAILABLE

AUTHORITATIVE_TARGET

- Root: `C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales`
- App: `streamlit_opensea_sales\app_opensea_sales.py`
- Port: `8502`
- 8501 gaming marketplace and 8504 staging are out of scope.
- Caddy mutation is prohibited.

DATABASE_MIGRATION_PLAN

The exact future migrations are `sql/add_site_visit_trader_mode.sql`,
`sql/create_site_product_events.sql`, and `sql/create_user_feedback.sql`.
The trader-USD alter migration is excluded. A full database backup is a
mandatory precondition, but `pg_dump` was not discoverable during Report 105.

SCRIPTS

`backup_production.ps1`, `deploy_production.ps1`, and
`rollback_production.ps1` default to DRY_RUN, require exact approval phrases
for execution, guard the 8502 target, reject 8501/8504/gaming/Caddy targets,
and do not authorize deployment by themselves.

OWNER_AUTHORIZATION_STILL_REQUIRED

Owner authorization, main promotion, maintenance window, backup capability,
and final production GO/NO-GO remain required. Report 105 did not execute a
production update.

ANY NEW DEVELOP COMMIT AFTER REPORT 105 INVALIDATES THE PREPARED RELEASE SHA.
NO PRODUCTION UPDATE WAS EXECUTED BY REPORT 105.
