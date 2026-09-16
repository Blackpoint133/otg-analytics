# OTG Analytics guarded production cutover runbook

This is the exact future operator sequence. Every mutation command below is
labeled `DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE`. Report 112 is
preparation only.

## Fixed scope

Production root:
`C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales`

Application: `streamlit_opensea_sales\app_opensea_sales.py` on loopback port
8502, branch `main`.

8501 / `app_gaming_marketplace.py`: DO NOT TOUCH.

8504 staging: DO NOT TOUCH.

Caddy: DO NOT CHANGE.

The prepared release is a frozen implementation SHA, not the current develop
tip. Report-only descendants on develop are allowed. Any non-report tracked
descendant invalidates the prepared release. Promotion must target the exact
prepared SHA through the guarded promotion script and never the develop tip.

## Required sequence

1. Perform a fresh unchanged-baseline and invalidation check. Confirm the
   prepared manifest hash/head, current production SHA, clean main worktree,
   live relative/absolute 8502 identity, PostgreSQL tools, read-only DB schema,
   and current main ref.
2. Obtain owner maintenance-window approval.
3. Obtain owner backup approval.
4. **DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE:** create the backup:

   ```powershell
   .\ops\production\backup_production.ps1 -Execute `
     -ApprovalPhrase BACKUP_OTG_ANALYTICS_8502
   ```

5. Validate the emitted schema-version-2 backup manifest, including Git bundle
   verification, exact environment hash, custom `pg_dump`/`pg_restore --list`
   validation, six artifact states, active-runtime state, and both managed
   task states.
6. Obtain owner exact-main-promotion approval.
7. **DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE:** promote exactly the
   frozen prepared head:

   ```powershell
   .\ops\production\promote_main_prepared_release.ps1 -Execute `
     -ApprovalPhrase PROMOTE_OTG_ANALYTICS_MAIN `
     -ExpectedMainHead <current-valid-main-sha> `
     -PreparedReleaseHead <PREPARED_RELEASE_HEAD> `
     -PreparedReleaseManifest <prepared-manifest-path> `
     -PreparedReleaseManifestSha256 <prepared-manifest-sha256>
   ```

   This pushes exactly `<PREPARED_RELEASE_HEAD>:refs/heads/main`, never
   develop, and uses fast-forward-only ancestry checks.
8. Verify `origin/main == PREPARED_RELEASE_HEAD`.
9. **DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE:** run deploy in
   DRY_RUN with the exact prepared and backup manifest inputs.
10. Obtain owner deployment approval.
11. **DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE:** execute the
    guarded deployment:

    ```powershell
    .\ops\production\deploy_production.ps1 -Execute `
      -ApprovalPhrase UPDATE_OTG_ANALYTICS_8502 `
      -ExpectedOldHead <current-production-sha> `
      -ExpectedReleaseHead <PREPARED_RELEASE_HEAD> `
      -PreparedReleaseRoot <prepared-release-root> `
      -PreparedReleaseManifest <prepared-manifest-path> `
      -PreparedReleaseManifestSha256 <prepared-manifest-sha256> `
      -BackupManifest <backup-manifest-path>
    ```

    The guarded core validates both manifests, prepares the release runtime,
    runs the pre-stop canary and artifact gates, then performs only the
    verified 8502 cutover. If a post-stop phase fails it attempts the same
    guarded rollback core automatically; database schema and remote main are
    not automatically reversed.
12. Verify local 8502 health, logs, final runtime, DB schema, six application
    readers, Supply v3, and the two managed refresh task definitions.
13. Owner performs external/public manual visual validation.

## Exact migrations

Only these three files may be applied, in this order:

1. `sql/add_site_visit_trader_mode.sql`
2. `sql/create_site_product_events.sql`
3. `sql/create_user_feedback.sql`

The trader-USD alter migration is redundant and must never execute. Database
schema rollback is NOT AUTOMATIC because this set is additive and old-app
compatible. Keep the full custom-format dump for separately authorized manual
recovery.

## Rollback command

Rollback is separate from deployment and requires the exact backup manifest.

**DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE:**

```powershell
.\ops\production\rollback_production.ps1 -Execute `
  -ApprovalPhrase ROLLBACK_OTG_ANALYTICS_8502 `
  -BackupManifest <exact-backup-manifest-path>
```

It restores only the recorded OTG application, environment, six managed
artifact presence states, refresh-task states, and active-runtime state. It
never uses `git clean`, never touches 8501/8504/Caddy, never moves remote main
backward, and does not automatically restore the additive database schema.

FINAL_PRODUCTION_DEPLOYMENT_AUTHORIZED=NO
