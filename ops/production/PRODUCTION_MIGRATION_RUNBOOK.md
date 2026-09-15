# OTG Analytics future production update runbook

This is a future owner-authorized runbook. Report 109 did not update
production.

## Scope and invariants

Production is C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales,
streamlit_opensea_sales\app_opensea_sales.py, port 8502, branch main.

DO_NOT_TOUCH_8501_GAMING_MARKETPLACE
DO_NOT_TOUCH_8504_STAGING
DO_NOT_CHANGE_CADDY

The prepared release is PREPARED_RELEASE_HEAD. ANY NON-REPORT CHANGE AFTER
PREPARED_RELEASE_HEAD INVALIDATES THE PREPARED RELEASE.

## Pre-go

1. Verify the current develop SHA still equals PREPARED_RELEASE_HEAD, the
   application/requirements/SQL content is unchanged, and production is at
   the expected old SHA with a clean worktree.
2. Obtain a maintenance window and owner authorization.
3. Owner authorizes the production backup.
4. From an elevated PowerShell session, run only after authorization:

    .\ops\production\backup_production.ps1 -Execute -ApprovalPhrase BACKUP_OTG_ANALYTICS_8502

DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE.

5. Verify BACKUP_MANIFEST.json is schema version 2, complete, hash-valid,
   target-bound to 8502, and has a valid custom dump.
6. Owner explicitly authorizes main promotion. Promote only by fast-forward to
   the prepared SHA. Do not run this during preparation:

    git fetch origin main
    git -C C:\VAMBAM\Projects\OTG\staging\opensea_sales checkout develop
    git -C C:\VAMBAM\Projects\OTG\staging\opensea_sales push origin develop:main

## Deploy

After origin/main equals PREPARED_RELEASE_HEAD, perform a final DRY_RUN and
review its output. Then, only with separate owner deployment authorization:

    .\ops\production\deploy_production.ps1 -ExpectedOldHead <old-production-sha> -ExpectedReleaseHead <PREPARED_RELEASE_HEAD> -ReleaseCandidateRoot C:\VAMBAM\Projects\OTG\DEV\prepared_release_109 -ReleasePython C:\VAMBAM\Projects\OTG\runtime\opensea_sales\releases\<PREPARED_RELEASE_HEAD>\.venv\Scripts\python.exe -BackupManifest <validated-backup-manifest> -Execute -ApprovalPhrase UPDATE_OTG_ANALYTICS_8502

DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE.

The script validates the runtime and current source artifacts, runs the
foreground candidate canary, stops only the verified 8502 OTG process, fast
forwards production, applies the three additive migrations, installs fresh
validated dynamic artifacts, starts the new app with fail-closed gates, and
registers refresh tasks only after local health passes.

## Refresh tasks

After new 8502 health succeeds, verify:

- OTG_Derived_Data_Refresh_Production is every 15 minutes;
- OTG_Metadata_Refresh_Production is every 60 minutes;
- both invoke production refresh scripts with prepared Python;
- IgnoreNew, StartWhenAvailable, SYSTEM/highest privilege, and production
  working directory are correct;
- all staging task definitions are unchanged.

Raw sales ingestion remains the existing private parser/indexer pipeline.
These tasks are downstream and must not duplicate raw ingestion.

## Rollback

If rollback is separately authorized:

    .\ops\production\rollback_production.ps1 -BackupManifest <validated-backup-manifest> -Execute -ApprovalPhrase ROLLBACK_OTG_ANALYTICS_8502

DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE.

Rollback restores the manifest old Git SHA, exact .env, six artifact
presence/hash states, active runtime pointer, and exact production refresh
task state, then starts the old app and verifies local HTTP health. It never
runs git clean, changes remote main, touches 8501/8504/Caddy, or automatically
reverses the three additive migrations.

## Final owner validation

After local health, the owner must perform public/manual visual validation.
Write-capable analytics, product-event, feedback, and Telegram gates remain
disabled until a later explicit decision.

FINAL_PRODUCTION_DEPLOYMENT_AUTHORIZED=NO
