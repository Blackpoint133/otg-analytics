# OTG Analytics production release preparation

STATUS=TECHNICALLY_PREPARED_AWAITING_OWNER_AUTHORIZATION

## Authoritative target

- Production root: `C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales`
- Application: `streamlit_opensea_sales\app_opensea_sales.py`
- Production branch: `main`
- Production port: `8502`
- Final runtime family: `C:\VAMBAM\Projects\OTG\runtime\opensea_sales\releases\<PREPARED_RELEASE_HEAD>`
- 8501 is the separate gaming marketplace: DO NOT TOUCH.
- 8504 is staging: DO NOT TOUCH.
- Caddy is outside scope: DO NOT CHANGE.

## Frozen release model

`PREPARED_RELEASE_HEAD` is the implementation commit, not the current develop
tip. Report-only descendants under `DEV/reports/` do not change it. Any
non-report tracked commit after the prepared head invalidates this preparation.

`promote_main_prepared_release.ps1` is the only promotion mechanism. It checks
the expected current main, prepared manifest hash/head, local ancestry, and
pushes exactly `<PREPARED_RELEASE_HEAD>:refs/heads/main`. No script pushes
develop to main.

## Execution gates

The six operational entrypoints call the shared cores in
`production_update_common.ps1`. Production and simulation use the same ordered
orchestration; simulation substitutes only external adapters.

Before production downtime, deploy validates both the prepared-release
manifest and the production backup manifest, prepares the deterministic final
runtime, runs the foreground-owned 8505 canary, and validates all six refreshed
artifacts through current application readers. The canary precedes stopping
8502. Runtime reuse is accepted only when its release, lock, wheelhouse, and
pip gates match exactly; an unexpected runtime is rejected.

After a successful new 8502 health check, deploy writes
`ACTIVE_RUNTIME.json` atomically. The two refresh tasks use the same runtime
Python recorded by that active pointer. Mutation telemetry reports whether a
mutation occurred even when automatic rollback restores the old state.

## Database

The only migrations are:

1. `sql/add_site_visit_trader_mode.sql`
2. `sql/create_site_product_events.sql`
3. `sql/create_user_feedback.sql`

`sql/add_site_product_events_trader_usd_toggle.sql` is redundant and excluded.
Database rollback is `NOT_AUTOMATIC`; the additive schema remains in place and
the custom-format dump is retained for separately authorized recovery.

## Backup and rollback

`backup_production.ps1` is DRY_RUN by default and requires its exact approval
phrase for future execution. It creates schema-version-2 state containing the
Git bundle, exact `.env`, custom PostgreSQL dump validated by `pg_restore`, all
six artifact presence/hashes, active runtime state, and the two managed task
definitions.

`rollback_production.ps1` consumes that backup manifest, restores only the
recorded application/env/artifact/task/runtime state, restarts the old app,
and leaves database schema and remote main unchanged.

## Refresh automation

- `OTG_Derived_Data_Refresh_Production`: every 15 minutes; market period,
  market expansion, trader analytics.
- `OTG_Metadata_Refresh_Production`: every 60 minutes; item class, GUNZscope
  v3, quota-safe trader profile sync.

Both use `MultipleInstances=IgnoreNew`, `StartWhenAvailable=true`, the exact
production root, and the active release runtime. Registration occurs only
after new 8502 health passes. Existing staging tasks are never modified.

## Owner-authorized future sequence

1. Verify the frozen release and unchanged production baseline.
2. Obtain maintenance-window approval.
3. Obtain backup approval and execute `backup_production.ps1 -Execute`.
4. Validate the schema-version-2 backup manifest.
5. Obtain exact-main-promotion approval.
6. Execute `promote_main_prepared_release.ps1` with the exact prepared head
   and manifest hash.
7. Verify `origin/main == PREPARED_RELEASE_HEAD`.
8. Run deploy DRY_RUN.
9. Obtain deploy approval.
10. Execute deploy, then verify local health and refresh-task definitions.
11. Owner performs public/manual visual validation.

Report 110 performs no production update, main promotion, backup execution,
process stop/start, SQL, environment write, data write, or task registration.

FINAL_PRODUCTION_DEPLOYMENT_AUTHORIZED=NO
