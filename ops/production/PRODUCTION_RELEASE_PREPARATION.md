# OTG Analytics Production Release Preparation

STATUS=TECHNICALLY_PREPARED_AWAITING_NEW_OWNER_AUTHORIZATION
OWNER_PRODUCTION_DEPLOYMENT_AUTHORIZATION=NO

This document describes the corrected production tooling after Report 115.
Report 113 was blocked before its first mutation because the live production
target had no `ACTIVE_RUNTIME.json`. The deploy core would have stopped 8502
before its refresh cores could obtain a runtime, and its rollback path did not
accept an intentionally absent listener. No production mutation occurred.

## Authoritative target

- Root: `C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales`
- App: `streamlit_opensea_sales\app_opensea_sales.py`
- Port: `8502`
- Branch: `main`
- Current production SHA at preparation: `dacee4c675419dea1277ceb5e8a70e1a7ffc36a0`
- 8501 / `app_gaming_marketplace.py`: DO NOT TOUCH
- 8504 staging: DO NOT TOUCH
- Caddy: DO NOT CHANGE

The production source-ingestion pipeline remains the existing private
`parser_opensea_sales.py` / `run_indexer.py` pipeline. The production refresh
wrappers operate downstream of that pipeline and do not replace it.

## Corrected runtime contract

Future release runtimes are created outside the Git checkout at:

`C:\VAMBAM\Projects\OTG\runtime\opensea_sales\releases\<release_sha>\.venv`

Deployment prepares and validates the exact final-runtime Python before any
downtime. During the cutover refresh cores use that validated final-runtime
Python through an in-memory deployment-only override. This override is
required to pass the exact release runtime path guard and does not write an
active pointer.

Normal scheduled/manual refreshes still require:

`C:\VAMBAM\Projects\OTG\runtime\opensea_sales\ACTIVE_RUNTIME.json`

The active pointer is written only after the new 8502 process starts and passes
health and process-identity validation. It therefore always denotes a live,
validated runtime.

## Process and log contract

Each application start creates a unique stdout/stderr pair under the external
runtime log directory, for example
`production_<launch-id>.out.log` and `production_<launch-id>.err.log`.
The child owns those redirected streams; the start wrapper never appends
metadata to either file after launch. The returned process/start object carries
the PID and both exact paths. The deploy and rollback log gates read only that
launch pair using an explicit shared-read handle, so a live child may continue
writing while it is inspected and stale logs cannot satisfy or fail the current
launch gate. Previous launch logs are retained as audit evidence and are not
used for the current-launch gate.

## Corrected rollback contract

Rollback resolves 8502 into exactly one of these states:

- expected OTG Analytics process present: validate and stop only that process;
- no listener present: continue restoration without stopping anything;
- foreign listener present: fail closed and leave it untouched.

Rollback restores Git, `.env`, all six managed artifact presence/hash states,
managed refresh task state, the prior active-runtime presence/hash state, and
the old application health. Database rollback is `NOT_AUTOMATIC`; the approved
schema changes are additive and old-app compatible. Remote main is never moved
back automatically.

## Database plan

The post-Report-119 read-only preflight expectation is stable browser identity
`READY` with the three additive objects already `PRESENT` in the live database.
The pre-migration state with all three objects `ABSENT` remains an accepted
initial state for an untouched target; a partial or otherwise different state
fails closed. The only approved future migrations, in order, are:

1. `sql/add_site_visit_trader_mode.sql`
2. `sql/create_site_product_events.sql`
3. `sql/create_user_feedback.sql`

`sql/add_site_product_events_trader_usd_toggle.sql` is redundant and excluded.

Production backup uses PostgreSQL 18.3 `pg_dump --format=custom` and validates
the dump with `pg_restore --list`. The schema-v2 backup manifest is written
last and must validate all hashes and rollback-critical state before deploy.

## Read-only preflight

Before any future owner-authorized cutover, run:

```powershell
& .\ops\production\validate_production_cutover_preflight.ps1 `
  -ExpectedOldHead <current-production-main-sha> `
  -ExpectedReleaseHead <prepared-release-sha> `
  -PreparedReleaseRoot <prepared-release-root> `
  -PreparedReleaseManifest <prepared-release-root>\PREPARED_RELEASE_MANIFEST.json `
  -PreparedReleaseManifestSha256 <manifest-sha256> `
  -ExpectedMainHead <current-origin-main-sha>
```

This is strictly read-only and uses the same guarded 8502 process identity
predicate as backup, deploy, and rollback. Relative `app_opensea_sales.py`
launches are accepted only with the strict listener, Python, Streamlit, port,
address, repository, branch, and clean-worktree gates. Unrelated absolute app
paths, 8501, 8504, gaming, and Caddy are rejected.

## Validation state

Report 112 prepared release: invalidated by the Report 113 tooling finding.
Report 113: blocked before mutation; production mutation count `0`.
Report 115 was blocked before cutover because the backup wrapper used direct
native Git with merged stderr. The valid bundle emitted Git's normal
successful verification diagnostic on stderr, which PowerShell surfaced as a
terminating error. The corrected implementation invokes Git through the
controlled child-process helper: stdout and stderr are captured separately,
only exit code zero is success, and all non-zero exits fail closed. Bundle
creation, non-empty-file validation, and bundle verification remain required
before the v2 manifest can be finalized. The Report 115 backup directory is
audit evidence only and is not reusable as a future backup because it has no
complete manifest, environment copy, or database dump.

Execution failure telemetry for production is written under the external
runtime logs directory, not the production Git checkout. Simulation telemetry
remains inside the isolated sandbox. This prevents a failed attempt from
dirtying the production worktree or becoming release content.

The corrected implementation must be committed and refrozen as a new prepared
release before any owner authorization can be reused. The Report 115
authorization is consumed and a future cutover requires fresh owner
authorization.

The corrected sandbox proves the shared core can deploy from an absent active
runtime, use the final runtime for both refresh classes, activate the pointer
only after new-process health, and automatically restore old state after a
failure with no 8502 listener. Real production calls remain dry-run/read-only
until a fresh owner authorization is supplied.

The post-Report-119 recovery baseline is intentionally split: remote `main`
may be at the promoted release while the live production checkout remains at
the restored old release. Future preparation validates ancestry from both
baselines independently; it does not require them to be identical.

## Final authorization boundary

This preparation does not authorize production deployment. A future owner
must authorize the exact newly prepared release separately. No production
backup, promotion, migration, process restart, environment/data write,
scheduled-task change, or proxy change was performed by this preparation.
