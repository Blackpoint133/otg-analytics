# Report 097 Production Release Preparation

## CURRENT_STATE

The public Caddy route currently targets `localhost:8501`, which is the separate gaming marketplace process. OTG Analytics is the OpenSea application on local port 8502 at `C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales`; staging is 8504. This distinction must be resolved by the owner before any cutover.

## PREPARED_RELEASE_CANDIDATE

Candidate workspace: `C:\VAMBAM\Projects\OTG\DEV\release_candidate_097`. Candidate virtualenv must be built from `requirements.lock.txt`; no candidate snapshot is generated in this report.

## DATABASE_MIGRATION_PLAN

Read-only schema facts: stable identity columns/checks/index are present; trader mode is not currently accepted; product events and user feedback are absent. Candidate migrations are `sql/add_site_visit_trader_mode.sql`, `sql/create_site_product_events.sql`, and `sql/create_user_feedback.sql`. The product-events trader-USD alter migration is excluded when the table is created from the current create script.

## DATA_ARTIFACT_PLAN

Production sales and enriched sales each contain 1,941 files and have max sale date `2026-09-14T23:59:54`. Missing trader, item-class, supply-v3 and profile snapshots are deferred until topology is confirmed. Market derived artifacts are read-only inputs and must be regenerated only in the candidate workspace if stale.

## ENVIRONMENT_PLAN

Keep analytics/product-event/feedback writes disabled on first boot. Secrets remain outside Git. The live 8502 process uses system Python 3.11.0; its existing venv is separate.

## FUTURE_BACKUP_PLAN

Back up the target checkout SHA/status, `.env`, replaceable data artifacts, database, process command line, Python environment, Caddy configuration, and relevant task definitions before authorization.

## FUTURE_CUTOVER_SEQUENCE

Owner confirms the target route and maintenance window; validate candidate artifacts; back up; apply approved migrations; stop/start only the authorized OTG Analytics target; update routing only if explicitly approved; validate local and public endpoints; enable write gates gradually.

## ROLLBACK_PLAN

Restore the prior application SHA/environment/data backup and reverse any approved database change using the approved backup procedure. Do not remove the prior state until validation completes.

## OWNER_AUTHORIZATION_GATES

Owner must confirm which process is the OTG Analytics public target, authorize backup/migrations/process changes, supply missing credentials, validate desktop/mobile UI and public routing, and make the final GO/NO-GO decision.

SNAPSHOT_GENERATION_DEFERRED_UNTIL_TOPOLOGY_CONFIRMED=YES
NO PRODUCTION UPDATE WAS EXECUTED BY REPORT 097
REPORT_097_DOES_NOT_AUTHORIZE_PRODUCTION_DEPLOYMENT=YES
