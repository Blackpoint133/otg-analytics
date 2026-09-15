# OTG Analytics production migration runbook

STATUS=BLOCKED_PG_DUMP_UNAVAILABLE

## Target

Production is `C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales`,
`app_opensea_sales.py`, port `8502`, branch `main`. Port 8501 is the separate
gaming marketplace; port 8504 is staging. Do not touch either. Do not change
Caddy.

## Future authorized sequence

1. Verify the old production SHA and clean worktree.
2. Run `backup_production.ps1 -Execute -ApprovalPhrase BACKUP_OTG_ANALYTICS_8502`.
3. Owner promotes main to the prepared release SHA.
4. Run deploy dry-run, then only with explicit authorization:
   `deploy_production.ps1 -Execute -ApprovalPhrase UPDATE_OTG_ANALYTICS_8502`.
5. Prepare the new runtime, refresh dynamic artifacts, run the 8505 canary,
   stop only verified 8502, fast-forward Git, apply the three additive SQL
   migrations, and start the new app.
6. Verify local health, database schema, write gates, and owner-facing UI.

All mutation examples are **DO NOT RUN UNTIL OWNER AUTHORIZES PRODUCTION UPDATE**.

## Rollback

Use `rollback_production.ps1` with the validated backup manifest and exact
approval phrase. Restore app, environment, and artifacts; leave additive DB
schema intact by default (`DB_SCHEMA_ROLLBACK=NOT_AUTOMATIC`). Never use
`git clean`, and never touch 8501, 8504, or Caddy.

`pg_dump`/`psql` discovery is currently blocked; no deployment is ready until
a valid full database backup path is available.

REPORT 105 DOES NOT AUTHORIZE PRODUCTION DEPLOYMENT.
NO PRODUCTION UPDATE WAS EXECUTED BY REPORT 105.
