# OTG Analytics production preparation

STATUS=TECHNICALLY_PREPARED_AWAITING_OWNER_AUTHORIZATION

## AUTHORITATIVE_TARGET

OTG Analytics production is:
C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales

The application is streamlit_opensea_sales\app_opensea_sales.py on
127.0.0.1:8502, branch main. Port 8501 is the separate gaming marketplace
service and port 8504 is staging.

DO_NOT_TOUCH_8501_GAMING_MARKETPLACE
DO_NOT_TOUCH_8504_STAGING
DO_NOT_CHANGE_CADDY

## VALIDATED_RELEASE

Report 109 uses one shared production/simulation orchestration core. The
future release is identified by PREPARED_RELEASE_HEAD; any non-report tracked
commit after that SHA invalidates the prepared release and requires
revalidation.

The application, builder scripts, SQL migrations, and requirements were
unchanged from the validated application baseline. The prepared runtime is
the exact 45-package offline lock contract with pip check and import gates
passing.

## VALIDATED_DYNAMIC_ARTIFACT_PIPELINE

The six outputs are dynamic and must be regenerated from current production
source data during cutover:

1. market period summaries;
2. market expansion metrics;
3. trader analytics;
4. item-class snapshot;
5. GUNZscope v3 provider snapshot;
6. OpenSea account-profile fallback snapshot.

Runtime readers, market build identity, Supply v3 selection, profile fallback,
secret checks, and the foreground candidate canary are mandatory gates.
Fallback profile generation uses zero HTTP requests.

## DATABASE_CURRENT_STATE

The current database is preserved during preparation. PostgreSQL 18.3
pg_dump.exe, pg_restore.exe, and psql.exe are available. Report 109 does not
execute SQL or create a backup against production.

## DATABASE_MIGRATION_PLAN

The exact additive migration set, in order, is:

1. sql/add_site_visit_trader_mode.sql
2. sql/create_site_product_events.sql
3. sql/create_user_feedback.sql

sql/add_site_product_events_trader_usd_toggle.sql is redundant and excluded.
Database rollback is NOT_AUTOMATIC; the full custom dump remains available
for a separately authorized emergency restoration.

## BACKUP_CONTRACT

backup_production.ps1 is DRY_RUN by default and requires
BACKUP_OTG_ANALYTICS_8502 for future execution. It creates a version-2
manifest outside the production checkout containing the verified Git bundle,
exact .env copy/hash, custom-format database dump validated by pg_restore
--list, all six artifact presence/hash states, the old 8502 process identity,
old active runtime state, and both managed production task states.
The manifest is marked complete only after all hashes and validations pass.

## DEPLOY_CONTRACT

deploy_production.ps1 is DRY_RUN by default and requires
UPDATE_OTG_ANALYTICS_8502. It never promotes main; remote origin/main must
already equal the prepared release SHA. The shared execution order is:

1. validate the complete backup manifest and prepared runtime;
2. validate candidate artifacts and the canary;
3. stop only the verified OTG Analytics 8502 process;
4. fast-forward production main;
5. atomically apply fail-closed environment keys;
6. apply the exact three migrations;
7. refresh and validate all six dynamic artifacts;
8. start and health-check the new 8502 process;
9. register or confirm the two refresh tasks only after health passes.

Failure after downtime begins invokes the same rollback core. Caddy, 8501,
8504, and remote main are never changed by deployment tooling.

## ROLLBACK_CONTRACT

rollback_production.ps1 is DRY_RUN by default and requires
ROLLBACK_OTG_ANALYTICS_8502. It consumes the actual old SHA and all restore
state from the version-2 backup manifest. It restores old tracked code, .env,
six artifact presence/hash states, active runtime pointer, and exact
production task states, then starts and health-checks the old app.
It never runs git clean, never reverses remote main, and does not
automatically restore additive database schema.

## REFRESH_AUTOMATION

After a successful future 8502 health gate, register only:

- OTG_Derived_Data_Refresh_Production, every 15 minutes, running
  refresh_production_derived.ps1;
- OTG_Metadata_Refresh_Production, every 60 minutes, running
  refresh_production_metadata.ps1.

Both use the prepared release Python, production root as working directory,
SYSTEM/highest-privilege task settings, StartWhenAvailable=true, and
MultipleInstances=IgnoreNew. Existing unexpected task definitions fail
closed. Existing private raw source ingestion remains the owner of raw
sales/source files; these tasks are downstream derived/metadata refresh only.

## ENVIRONMENT_FIRST_BOOT_POLICY

The future first boot preserves every unrelated .env line and sets only
known fail-closed gates, including GUNZSCOPE_SUPPLY_SOURCE=v3 and analytics,
site analytics, product events, feedback, and Telegram writes to false.
Secrets are loaded into child process environments in memory and never appear
in arguments, logs, manifests, or reports.

## OWNER_AUTHORIZATION_STILL_REQUIRED

NO PRODUCTION UPDATE WAS EXECUTED BY REPORT 109.
FINAL_PRODUCTION_DEPLOYMENT_AUTHORIZED=NO
