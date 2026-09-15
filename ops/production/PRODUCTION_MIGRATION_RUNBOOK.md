# OTG Analytics production migration runbook — Report 106

STATUS=BLOCKED_EXECUTION_SEMANTICS_NOT_COMPLETE

## CURRENT_STATE

Target: `C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales`,
`app_opensea_sales.py`, `127.0.0.1:8502`, current old SHA
`dacee4c675419dea127ceb5e8a70e1a7ffc36a0`. 8501 is a separate gaming
marketplace, 8504 is staging, and Caddy is unchanged/out of scope.

## PRE-GO

Verify the old SHA and clean tree. Discover PostgreSQL 18.3 tools. Run the
backup script in dry-run, then after owner authorization execute it with
`-Execute -ApprovalPhrase BACKUP_OTG_ANALYTICS_8502`. Confirm the resulting
manifest contains the custom dump, environment hash, Git bundle, artifacts,
process metadata, and task state. Promote main fast-forward-only to the
prepared release SHA, then run deploy dry-run.

## DEPLOY

**DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE.** The authorized
deploy performs new-runtime preparation, current-source artifact refresh,
runtime readers, a foreground 8505 canary, backup validation, the three
additive migrations, verified 8502 stop, Git fast-forward, fail-closed env
gates, atomic artifact install, new-runtime 8502 start, local health, DB
verification, and post-health task registration. Caddy, 8501, and 8504 are
never modified.

Example (authorization required):
`deploy_production.ps1 -ExpectedOldHead <old> -ExpectedReleaseHead <release> -ReleaseCandidateRoot <candidate> -ReleasePython <python> -BackupManifest <manifest> -Execute -ApprovalPhrase UPDATE_OTG_ANALYTICS_8502`

## ROLLBACK

**DO NOT RUN UNTIL OWNER AUTHORIZES ROLLBACK.** Execute rollback with the
validated manifest and `ROLLBACK_OTG_ANALYTICS_8502`. It restores the actual
manifest old Git SHA, environment, and artifact presence state, starts the
old app, and checks localhost health. It never uses `git clean`; additive DB
schema remains in place and the dump is retained for manual emergency use.

## TASKS AND OWNER GATES

The two named production refresh tasks are collision-fail-closed, with 15 and
60 minute triggers. Existing staging tasks are never changed. Owner approval
of main promotion, maintenance window, production mutation, and final public
validation is mandatory.

Report 106 does not authorize production deployment. Execute-branch tooling
requires non-production simulation and review before owner authorization.
