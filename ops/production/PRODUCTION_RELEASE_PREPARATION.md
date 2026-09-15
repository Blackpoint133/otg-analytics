# OTG Analytics production update preparation — Report 106

STATUS=BLOCKED_PRODUCTION_EXECUTION_SEQUENCE_REQUIRES_COMPLETION

## AUTHORITATIVE_TARGET

Production is `C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales`,
`streamlit_opensea_sales\app_opensea_sales.py`, port `8502`, branch `main`.
Port 8501 is the separate gaming marketplace and port 8504 is staging.
Neither may be touched. Caddy is out of scope and must not change.

## DATABASE

PostgreSQL tools are available at `C:\Program Files\PostgreSQL\18\bin`,
version 18.3. The backup is a full custom-format `pg_dump`, validated with
`pg_restore --list`, and is mandatory before deployment. The exact additive
migrations are:

1. `sql/add_site_visit_trader_mode.sql`
2. `sql/create_site_product_events.sql`
3. `sql/create_user_feedback.sql`

The trader-USD alter migration is excluded. Database rollback is
`NOT_AUTOMATIC`.

## AUTOMATION

`OTG_Derived_Data_Refresh_Production` runs every 15 minutes and sequences
market period summaries, expansion metrics, and trader analytics.
`OTG_Metadata_Refresh_Production` runs every 60 minutes and sequences item
class, GUNZscope v3, and quota-safe trader profile refresh. Registration is
guarded, collision-fail-closed, and dry-run by default.

## SCRIPTS

The scripts default to DRY_RUN and require exact approval phrases. Their
simulation branches passed in the isolated Report 107 sandbox, but the
production-context Execute sequence still requires completion and review.

## OWNER_AUTHORIZATION_STILL_REQUIRED

Owner must authorize the maintenance window, main fast-forward, backup,
production stop/start, and final GO/NO-GO. Public visual/domain validation
remains owner work.

ANY NEW DEVELOP COMMIT AFTER REPORT 106 INVALIDATES THE PREPARED RELEASE SHA.
NO PRODUCTION UPDATE WAS EXECUTED BY REPORT 107.
