# OTG Analytics guarded production update runbook

This runbook is for a future owner-authorized maintenance window. Every
mutation example below is labeled DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION
UPDATE. Report 110 does not execute any mutation.

## Scope and immutable safety rules

Production is `C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales`,
`app_opensea_sales.py`, port `8502`, branch `main`. The prepared release is an
exact implementation SHA. Develop may have report-only descendants; it does
not need to equal the prepared SHA. Any non-report tracked descendant
invalidates the release.

8501 gaming marketplace: DO NOT TOUCH.

8504 staging: DO NOT TOUCH.

Caddy: DO NOT CHANGE.

## Pre-go verification

Read-only checks must confirm the prepared head, prepared manifest SHA,
production old SHA, clean production worktree, unchanged `.env`, unchanged
8501/8502/8504 PIDs, and unchanged main baseline. Confirm the prepared runtime
workspace, 45-wheel contract, and validation logs are still present.

## Future authorized sequence

1. Owner approves a maintenance window.
2. Owner approves the backup.
3. **DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE:**

   ```powershell
   .\ops\production\backup_production.ps1 -Execute `
     -ApprovalPhrase BACKUP_OTG_ANALYTICS_8502
   ```

4. Validate the emitted schema-version-2 `BACKUP_MANIFEST.json`, including
   Git bundle, environment, custom `pg_dump`, six artifact states, active
   runtime, and task hashes.
5. Owner approves exact main promotion.
6. **DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE:**

   ```powershell
   .\ops\production\promote_main_prepared_release.ps1 -Execute `
     -ApprovalPhrase PROMOTE_OTG_ANALYTICS_MAIN `
     -ExpectedMainHead <current-main-sha> `
     -PreparedReleaseHead <PREPARED_RELEASE_HEAD> `
     -PreparedReleaseManifest <prepared-manifest-path> `
     -PreparedReleaseManifestSha256 <prepared-manifest-sha256>
   ```

   This pushes only `<PREPARED_RELEASE_HEAD>:refs/heads/main`. It never
   promotes develop and never creates a merge commit.
7. Verify `origin/main` equals the exact prepared head.
8. **DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE:** run deploy DRY_RUN
   with the exact old/release heads, prepared root/manifest/hash, and backup
   manifest.
9. Owner authorizes deployment.
10. **DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE:** execute deploy:

    ```powershell
    .\ops\production\deploy_production.ps1 -Execute `
      -ApprovalPhrase UPDATE_OTG_ANALYTICS_8502 `
      -ExpectedOldHead <production-old-sha> `
      -ExpectedReleaseHead <PREPARED_RELEASE_HEAD> `
      -PreparedReleaseRoot <prepared-release-root> `
      -PreparedReleaseManifest <prepared-manifest-path> `
      -PreparedReleaseManifestSha256 <prepared-manifest-sha256> `
      -BackupManifest <backup-manifest-path>
    ```

    Deploy prepares the deterministic final runtime, validates the fresh
    artifacts/readers, runs the 8505 canary, then performs the guarded 8502
    cutover. It registers refresh tasks only after local health passes.
11. Verify local HTTP health, Supply v3, active runtime, database schema, and
    exact task definitions.
12. Owner performs public/manual visual validation.
13. Keep the backup manifest and custom database dump available. Rollback is a
    separately authorized action and does not reverse remote main or database
    schema automatically.

## Explicit rollback command

**DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE:**

```powershell
.\ops\production\rollback_production.ps1 -Execute `
  -ApprovalPhrase ROLLBACK_OTG_ANALYTICS_8502 `
  -BackupManifest <exact-backup-manifest-path>
```

Rollback restores only the recorded old application, environment, dynamic
artifact, task, and active-runtime state. It never uses a broad cleanup,
changes 8501/8504/Caddy, moves remote main backward, or automatically restores
the additive database schema.

## Exact migrations

Only these files may be applied, in order:

1. `sql/add_site_visit_trader_mode.sql`
2. `sql/create_site_product_events.sql`
3. `sql/create_user_feedback.sql`

The trader-USD alter migration is redundant and must not execute.
