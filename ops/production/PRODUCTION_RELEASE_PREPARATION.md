# OTG Analytics production preparation

STATUS=TECHNICALLY_PREPARED_AWAITING_NEW_OWNER_AUTHORIZATION
REPORT_112_DOES_NOT_AUTHORIZE_PRODUCTION_DEPLOYMENT

## Authoritative target

Production is only:

- Root: `C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales`
- Application: `streamlit_opensea_sales\app_opensea_sales.py`
- Branch: `main`
- Port: `8502`

Port 8501 and `app_gaming_marketplace.py` are a separate service: DO NOT
TOUCH. Port 8504 is staging: DO NOT TOUCH. Caddy is outside scope: DO NOT
CHANGE.

The current valid Git SHA is read from the server and remote refs. The
operator-supplied 39-character spelling `dacee4c675419dea127ceb5e8a70e1a7ffc36a0`
is not a complete Git SHA; the valid fetched SHA is
`dacee4c675419dea1277ceb5e8a70e1a7ffc36a0`.

## Report 111 outcome and release invalidation

Report 111 was correctly blocked before its first mutation because the live
8502 command uses the relative `app_opensea_sales.py` entrypoint. No backup,
pg_dump, main promotion, process stop, migration, data, environment, task,
or Caddy mutation occurred, and no rollback was required.

The Report 111 owner authorization was consumed by that blocked attempt. A
fresh owner authorization is required for any later cutover.

The old prepared release `d173a818ee8a36f66cbd032784317359e5de3d76` is
superseded by the Report 112 implementation release. The new prepared head,
workspace, manifest, and manifest SHA are recorded in Report 112 after the
implementation commit. Any non-report tracked commit after that prepared head
invalidates it and requires revalidation.

## Corrected 8502 identity gate

`production_update_common.ps1` accepts the current relative entrypoint only
when the listener is loopback `8502`, the owner is the inspected `python.exe`,
the command is Streamlit `run`, the app is exactly OTG Analytics, the command
targets port 8502, and it does not mention gaming or ports 8501/8504. An
absolute app path must be the authoritative production app or an explicitly
validated release-runtime app. The separate production Git root/branch/clean
baseline gate remains required; app-name-only matching is not used.

## PostgreSQL and read-only preflight

The tool discovery is read-only and does not alter PATH. It selects a complete
same-bin installation from command resolution, PostgreSQL installation
registry entries, or the standard 64-bit/32-bit Program Files locations. The
current server resolves:

`C:\Program Files\PostgreSQL\18\bin\pg_dump.exe`

`C:\Program Files\PostgreSQL\18\bin\pg_restore.exe`

`C:\Program Files\PostgreSQL\18\bin\psql.exe`

All three report PostgreSQL 18.3. The strictly read-only preflight is:

```powershell
.\ops\production\validate_production_cutover_preflight.ps1 `
  -ExpectedOldHead <current-valid-production-sha> `
  -ExpectedReleaseHead <new-prepared-release-sha> `
  -PreparedReleaseRoot C:\VAMBAM\Projects\OTG\DEV\prepared_release_112 `
  -PreparedReleaseManifest C:\VAMBAM\Projects\OTG\DEV\prepared_release_112\PREPARED_RELEASE_MANIFEST.json `
  -PreparedReleaseManifestSha256 <manifest-sha256> `
  -ExpectedMainHead <current-valid-main-sha>
```

It verifies the exact production repository, current 8502 identity, complete
PostgreSQL toolset, required DB environment, `transaction_read_only=on`, the
pre-migration schema, prepared release gate, and current main baseline. It
has no mutation switch and reports `MUTATION_EXECUTED=NO`.

## Database contract

The read-only pre-migration state is stable browser identity READY, trader mode
absent, `site_product_events` absent, and `user_feedback` absent. The future
migration set remains exactly, in order:

1. `sql/add_site_visit_trader_mode.sql`
2. `sql/create_site_product_events.sql`
3. `sql/create_user_feedback.sql`

`sql/add_site_product_events_trader_usd_toggle.sql` is redundant and excluded.
The three migrations are additive; database rollback is NOT AUTOMATIC. The
custom-format database backup remains available for separately authorized
manual recovery.

## Future authorization boundary

The future cutover requires a fresh owner authorization and must use the new
prepared-release manifest plus a newly created complete backup manifest. The
Report 112 implementation changed operational tooling, so the old prepared
workspace must not be reused.

No write gate is enabled automatically. The initial production values remain:

`GUNZSCOPE_SUPPLY_SOURCE=v3`

`OTG_ANALYTICS_WRITES_ENABLED=false`

`OTG_SITE_ANALYTICS_ENABLED=false`

`OTG_PRODUCT_EVENTS_ENABLED=false`

`OTG_FEEDBACK_WRITES_ENABLED=false`

`OTG_FEEDBACK_TELEGRAM_ENABLED=false`

No production update was executed by Report 112.

FINAL_PRODUCTION_DEPLOYMENT_AUTHORIZED=NO
