# Production Migration Runbook

## Observed baseline

- Production root: `C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales`
- Runtime root: `C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales\streamlit_opensea_sales`
- Production port: `8502`, bound to `127.0.0.1`
- Production Git: branch `main`, SHA `dacee4c675419dea127ceb5e8a70e1a7ffc36a0`, clean at audit time.
- Audit baseline develop SHA: `5985620cbbd6ea3dd497cbe9a247df2514dcac3f`.
- `main` is the merge base; develop is 321 commits ahead and 0 behind at the Report 095 baseline.
- The process is Python 3.11 launching `streamlit run app_opensea_sales.py --server.port 8502 --server.address 127.0.0.1`; the command uses the application filename but does not expose an absolute root path.
- The production `.venv` exists, but the live process uses the system Python executable. Observed versions: Streamlit 1.31.1, pandas 2.2.0, Plotly 5.18.0, NumPy 1.26.4, psycopg2 2.9.12.
- Caddy service is running from `C:\caddy\caddy.exe`; the observed active Caddyfile reverse-proxies `localhost:8501`, so it does not point to production port 8502. This is a technical NO-GO blocker.
- Relevant scheduled tasks observed: `OTG_Common_Data_Sync_Staging`, `OTG_GUNZscope_Supply_Sync_Staging`, `OTG_Item_Class_Sync_Staging`, `OTG_Item_Metadata_Current_Sync_Staging`, and `OTG_Trader_Profile_Sync_Staging`, all Ready. No task was changed or run.

## Environment and data readiness

The production `.env` has database and API credentials present, but supply-source, analytics-write, product-event, and feedback-write gates are not fully explicit. Secrets are intentionally omitted from this document. The repository `.env.example` now documents `OTG_PRODUCT_EVENTS_ENABLED=false` and `GUNZSCOPE_SUPPLY_SOURCE=v3`.

The nested runtime data directories `sales`, `sales_enriched`, `market_overview`, and `market_overview_enriched` exist. `items_index.json`, `current_price.csv`, and the enriched market manifest were present and fresh on the audit date. Several requested trader/profile/class/supply snapshot filenames were absent at the audited path and must be confirmed before deployment.

## Database state

A bounded read-only PostgreSQL connection with `default_transaction_read_only=on` succeeded. Existing inspected tables were `public.site_visit_sessions` and `public.site_item_events`. `site_product_events` and `user_feedback` were absent. Required migration candidates for a future authorized migration are:

1. `sql/add_site_visit_stable_browser_identity.sql`
2. `sql/add_site_visit_trader_mode.sql`
3. `sql/create_site_product_events.sql`
4. `sql/create_user_feedback.sql`

`sql/add_site_product_events_trader_usd_toggle.sql` is excluded because the current create script already includes the trader USD shape; no migration was applied by Reports 093-095.

## Future authorized deployment sequence

1. Confirm maintenance window, backups, credentials, proxy mapping, task ownership, and the exact candidate SHA.
2. Prepare a disposable or separately provisioned virtual environment from `requirements.lock.txt`; do not modify the production environment in place.
3. Generate and validate required snapshots/data before cutover.
4. Keep `OTG_ANALYTICS_WRITES_ENABLED=false`, `OTG_PRODUCT_EVENTS_ENABLED=false`, and feedback/Telegram gates disabled on first boot.
5. Deploy only after explicit authorization, apply approved SQL in a transaction/read-only rehearsal first, then enable analytics/product events/feedback in staged steps.
6. Validate local port 8502, proxy routing, desktop/mobile UI, chart overlays, supply attribution, and feedback behavior.

## Backup and rollback

- Capture verified database backup before any authorized schema migration.
- Preserve the current production tree, environment backup, data manifests, process command line, proxy configuration, and task export.
- Roll back application files/process to the prior verified SHA and restore the database only according to the approved backup plan.
- Do not remove the prior data or environment until post-cutover validation is complete.

## OWNER_MANUAL_ACTIONS_REQUIRED

- Final staging visual validation, including Report 092 mobile Trader Profile Card top visibility, close/reopen top position, internal scroll, and no orphan after navigation.
- Final desktop/mobile public smoke test.
- Provide missing secrets/API credentials if required.
- Confirm maintenance window and explicitly authorize database backup/migrations.
- Explicitly authorize main fast-forward and production stop/start.
- Verify the public domain externally after deployment.
- Verify a real Telegram feedback notification if Telegram is later enabled.
- Make the final GO / NO-GO decision.

## Technical decision

Technical readiness is **NO-GO pending owner review** because production runs the current `main` SHA rather than the candidate develop SHA, the live command does not identify the expected root absolutely, required snapshot files and DB tables are incomplete at the audited paths, and proxy/upstream details require confirmation. **PRODUCTION DEPLOYMENT IS NOT AUTHORIZED BY REPORT 093.**

No production mutation command was executed by this audit.

## Report 095 current audit facts

- The live listener owner was PID `124284`; its interpreter was the system Python 3.11.0, while the separate production `.venv` is Python 3.11.0 with an independent package set and clean pip check. These environments must not be conflated.
- Read-only task discovery found five relevant tasks, all classified as staging: `OTG_Common_Data_Sync_Staging`, `OTG_GUNZscope_Supply_Sync_Staging`, `OTG_Item_Class_Sync_Staging`, `OTG_Item_Metadata_Current_Sync_Staging`, and `OTG_Trader_Profile_Sync_Staging`.
- The Caddy Windows service is running from `C:\caddy\caddy.exe`; its live command uses `Caddyfile`. No active config file was exposed at the repository-relative candidate paths, so upstream confirmation remains a technical blocker, not an owner-assigned inspection task.
- Current database inspection used a bounded read-only connection. `site_product_events` and `user_feedback` were absent; site visit identity/trader-mode constraint details require the future migration rehearsal query before authorization.
- Exact future migration candidates are the two site-visit alterations, `create_site_product_events.sql`, and `create_user_feedback.sql`. `add_site_product_events_trader_usd_toggle.sql` is explicitly excluded because the table is absent and the current create migration already contains the trader USD shape.
- The candidate snapshot workspace is `C:\VAMBAM\Projects\OTG\DEV\release_candidate_093`; it is disposable and was not copied into production. Production deployment is not authorized by Report 094.
