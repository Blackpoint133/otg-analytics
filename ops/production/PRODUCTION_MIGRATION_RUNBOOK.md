# OTG Analytics Production Cutover Runbook

This is the future owner-authorized sequence for OTG Analytics production only.
It is not an authorization. Use the exact newly frozen prepared release and
freshly audited production state.

8501 / `app_gaming_marketplace.py`: DO NOT TOUCH.

8504 staging: DO NOT TOUCH.

Caddy: DO NOT CHANGE.

## Release identity

`PREPARED_RELEASE_HEAD` is the exact prepared implementation commit, not the
current `develop` tip. Report-only descendants under `DEV/reports/` do not
change it. Any non-report tracked change after that commit invalidates the
prepared release and requires a new preparation cycle.

Main promotion is performed only by the guarded promotion script. Never use a
branch-to-branch shortcut such as `git push origin develop:main`.

## Preflight and authorization

1. Confirm the maintenance window and fresh owner authorization.
2. Fetch `origin/develop` and `origin/main`; verify the frozen release and the
   old production main SHA have not been invalidated.
3. Verify production is the exact `main` checkout, clean, and at the expected
   old SHA. Verify the strict 127.0.0.1:8502 OTG Analytics process identity.
4. Run the read-only preflight:

```powershell
& .\ops\production\validate_production_cutover_preflight.ps1 `
  -ExpectedOldHead <old-production-sha> `
  -ExpectedReleaseHead <PREPARED_RELEASE_HEAD> `
  -PreparedReleaseRoot <prepared-release-root> `
  -PreparedReleaseManifest <prepared-release-root>\PREPARED_RELEASE_MANIFEST.json `
  -PreparedReleaseManifestSha256 <manifest-sha256> `
  -ExpectedMainHead <old-origin-main-sha>
```

The preflight verifies PostgreSQL tool discovery, required production `.env`
variables, a read-only DB connection, and the exact pre-migration schema.

## Backup

After fresh owner backup authorization, run:

```powershell
& .\ops\production\backup_production.ps1 -Execute `
  -ApprovalPhrase BACKUP_OTG_ANALYTICS_8502
```

Validate the printed `BACKUP_MANIFEST_PATH`. The schema-v2 manifest must be
complete and hash-valid, including the Git bundle, `.env`, custom PostgreSQL
dump plus `pg_restore --list` validation, six artifact states, active-runtime
state, process evidence, and both managed refresh-task states.

## Exact main promotion

After owner authorization specifically for main promotion, run the guarded
script with the exact prepared head and manifest:

```powershell
& .\ops\production\promote_main_prepared_release.ps1 `
  -ExpectedMainHead <old-origin-main-sha> `
  -PreparedReleaseHead <PREPARED_RELEASE_HEAD> `
  -PreparedReleaseManifest <prepared-release-root>\PREPARED_RELEASE_MANIFEST.json `
  -PreparedReleaseManifestSha256 <manifest-sha256> `
  -Execute -ApprovalPhrase PROMOTE_OTG_ANALYTICS_MAIN
```

The script pushes exactly `<PREPARED_RELEASE_HEAD>:refs/heads/main`, verifies
the resulting `origin/main`, and never promotes `develop`.

## Deploy

First run the deploy script once without `-Execute` using the exact backup
manifest. After owner deploy authorization, run:

```powershell
& .\ops\production\deploy_production.ps1 `
  -ExpectedOldHead <old-production-sha> `
  -ExpectedReleaseHead <PREPARED_RELEASE_HEAD> `
  -PreparedReleaseRoot <prepared-release-root> `
  -PreparedReleaseManifest <prepared-release-root>\PREPARED_RELEASE_MANIFEST.json `
  -PreparedReleaseManifestSha256 <manifest-sha256> `
  -BackupManifest <validated-backup-manifest> `
  -Execute -ApprovalPhrase UPDATE_OTG_ANALYTICS_8502
```

The shared deploy core validates both manifests, prepares the deterministic
final runtime before downtime, runs the 8505 canary, stops only the verified
8502 process, fast-forwards the production checkout, applies the exact three
additive migrations, refreshes derived and metadata artifacts with the
validated final runtime, validates application readers, starts 8502, checks
health/logs/process identity, writes `ACTIVE_RUNTIME.json`, configures the two
approved tasks, and writes the deployment receipt. The active pointer is never
written merely to make a pre-health refresh pass.

The first boot remains fail-closed:

```text
GUNZSCOPE_SUPPLY_SOURCE=v3
OTG_ANALYTICS_WRITES_ENABLED=false
OTG_SITE_ANALYTICS_ENABLED=false
OTG_PRODUCT_EVENTS_ENABLED=false
OTG_FEEDBACK_WRITES_ENABLED=false
OTG_FEEDBACK_TELEGRAM_ENABLED=false
```

If deploy fails after downtime begins, the same guarded rollback core is
attempted automatically. The output must distinguish mutation, rollback, and
restored-state telemetry. Do not improvise repairs or retry in the same
maintenance window.

## Database

Only these migrations may run, in this order:

1. `sql/add_site_visit_trader_mode.sql`
2. `sql/create_site_product_events.sql`
3. `sql/create_user_feedback.sql`

Do not run `sql/add_site_product_events_trader_usd_toggle.sql`. Database
rollback is `NOT_AUTOMATIC`; retain the custom dump for separately authorized
manual recovery because the approved changes are additive and old-app
compatible.

## Rollback

With separate owner rollback authorization, use the validated backup manifest:

```powershell
& .\ops\production\rollback_production.ps1 `
  -BackupManifest <validated-backup-manifest> `
  -Execute -ApprovalPhrase ROLLBACK_OTG_ANALYTICS_8502
```

Rollback validates the manifest, then handles 8502 explicitly: an expected OTG
process is stopped; no listener is a valid starting state; a foreign listener
fails closed and is not touched. It restores the old Git head, `.env`, all six
artifact presence/hash states, managed task state, and prior active-runtime
presence/hash state, then starts and health-checks the old application. It never
runs `git clean`, reverses remote main, or automatically restores the database.

## Post-deploy validation

Verify production `main` and the prepared head, new 8502 identity and HTTP
health, clean logs, active runtime, `pip check`, the three DB schema changes,
all six dynamic readers and Supply v3, exact refresh-task actions/cadences,
and unchanged 8501, 8504, unrelated tasks, and Caddy. Perform owner/public
visual validation only after these local gates pass. Enabling any write gate is
a separate owner decision.
