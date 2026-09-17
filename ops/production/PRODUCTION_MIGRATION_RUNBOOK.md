# OTG Analytics Production Cutover Runbook

This is the future owner-authorized sequence for OTG Analytics production only.
It is not an authorization. Use the exact newly frozen prepared release and
freshly audited production state.

8501 / `app_gaming_marketplace.py`: DO NOT TOUCH.

8504 staging: DO NOT TOUCH.

Caddy: DO NOT CHANGE.

## Mandatory Streamlit launch contract

Every new OTG Analytics production supervisor activation must use the single
canonical parameter string returned by `Get-ProductionStreamlitLaunchParameters`:

```text
-m streamlit run app_opensea_sales.py --server.address 127.0.0.1 --server.port 8502 --server.fileWatcherType none --server.headless true --browser.gatherUsageStats false --theme.base="dark"
```

The deployment writes NSSM configuration, reads it back, and validates the
complete launch contract—including `--theme.base=dark`—before starting the
service. The active supervised child is validated against the same contract
after start, and the deployment receipt records `streamlit_theme_base=dark`
and `theme_contract=PASS`. Missing or non-dark theme values fail closed; CSS
does not replace this launch invariant. Rollback restores the exact backed-up
NSSM parameters without rewriting the historical configuration.

### Correction boundary for a known legacy source

Source ownership and target activation are different gates. A correction
preflight may use `-AllowLegacyMissingThemeSource` to prove the existing
`OTG_app_opensea_sales` NSSM service and its child/listener are ours when the
only theme drift is a missing `--theme.base`. It must report that source as
`MISSING` / `KNOWN_LEGACY_DRIFT`, preserve the exact parameters in the backup,
and use ownership validation to stop and restore it. `light`, invalid, or
duplicate/conflicting theme values remain fail-closed. The allowance never
applies to a new activation: the read-back NSSM configuration and the new
supervised child must pass the strict dark launch contract before service start
and before `ACTIVE_RUNTIME.json` is written. Once production is corrected,
ordinary future source validation is strict again.

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
variables, a read-only DB connection, and either the untouched pre-migration
schema or the complete additive schema already present after Report 119. A
partial or unexpected schema state fails closed.

For the one known legacy correction, invoke the same command with
`-AllowLegacyMissingThemeSource`; this enables ownership/backup/stop of only
the missing-theme source while retaining the strict target prepared-release
gate. It is not an ordinary deployment bypass.

## Backup

After fresh owner backup authorization, run:

```powershell
& .\ops\production\backup_production.ps1 -Execute `
  -ApprovalPhrase BACKUP_OTG_ANALYTICS_8502
```

Validate the printed `BACKUP_MANIFEST_PATH`. The schema-v2 manifest must be
complete and hash-valid, including the Git bundle, `.env`, custom PostgreSQL
dump plus `pg_restore --list` validation, six artifact states, active-runtime
state, process evidence, both managed refresh-task states, and the complete
mutable NSSM configuration for `OTG_app_opensea_sales`.

The Git bundle is created and verified through the controlled child-process
runner. It captures stdout and stderr separately and treats only the native
process exit code as authoritative: exit code `0` passes even when Git writes
normal diagnostics to stderr; any non-zero exit fails closed. The bundle must
exist and be non-empty, and `git bundle verify` must actually return `0`.

The incomplete Report 115 backup at
`C:\VAMBAM\Projects\OTG\DEV\production_backups\20260916_004452_dacee4c6`
must not be reused. A new owner-authorized cutover requires a newly completed
backup manifest.

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
final runtime before downtime, runs the 8505 canary, validates the
`OTG_app_opensea_sales` NSSM service and current child, stops the service,
waits for `Stopped` and no 8502 listener, fast-forwards the production
checkout, applies the exact three additive migrations, refreshes derived and
metadata artifacts with the validated final runtime, validates application
readers, configures NSSM for the final runtime and unique activation logs,
starts the service, checks child identity/health/logs, writes
`ACTIVE_RUNTIME.json`, configures the two approved tasks, and writes the
deployment receipt. The active pointer is never written merely to make a
pre-health refresh pass.

The first boot remains fail-closed:

```text
GUNZSCOPE_SUPPLY_SOURCE=v3
OTG_ANALYTICS_WRITES_ENABLED=false
OTG_SITE_ANALYTICS_ENABLED=false
OTG_PRODUCT_EVENTS_ENABLED=false
OTG_FEEDBACK_WRITES_ENABLED=false
OTG_FEEDBACK_TELEGRAM_ENABLED=false
```

Each NSSM activation uses a unique stdout/stderr log pair under the external
runtime logs directory. NSSM/its child owns those files and the wrapper
performs no post-launch append. The service result identifies the exact pair;
current-launch validation reads it with shared-read semantics and therefore
does not inspect stale logs or compete with the running child. Rollback uses
the same service and log contract with temporary rollback paths before the
exact backed-up NSSM paths are restored.

If deploy fails after downtime begins, the same guarded rollback core is
attempted automatically. The output must distinguish mutation, rollback, and
restored-state telemetry. Do not improvise repairs or retry in the same
maintenance window.

Production execution telemetry is kept under the external runtime logs area;
it must not create an untracked file in the production checkout. A failed
pre-cutover attempt still fails closed and must be reviewed before any retry.

After Report 119 recovery, remote `main` and the live production checkout may
legitimately differ: remote `main` is the promoted prior release while the
live checkout is the restored old release. Validate each against its expected
head and require the live old head to be an ancestor of the prepared release;
do not require the two current heads to be equal.

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

Rollback validates the manifest, then handles the supervisor explicitly: an
expected OTG service child causes the NSSM service to stop; no listener is a
valid starting state; a foreign listener fails closed and is not touched. It
restores the old Git head, `.env`, all six artifact presence/hash states,
managed task state, prior active-runtime presence/hash state, and the exact
backed-up NSSM configuration. If the service was running before the cutover,
it then starts and health-checks the old supervised application using a
current rollback-launch log pair. It never runs `git clean`, reverses remote
main, or automatically restores the database.

## Post-deploy validation

Verify production `main` and the prepared head, new 8502 identity and HTTP
health, clean logs, active runtime, `pip check`, the three DB schema changes,
all six dynamic readers and Supply v3, exact refresh-task actions/cadences,
and unchanged 8501, 8504, unrelated tasks, and Caddy. Perform owner/public
visual validation only after these local gates pass. Enabling any write gate is
a separate owner decision.
