# OTG Analytics Production Release Preparation

STATUS=TECHNICALLY_PREPARED_AWAITING_PRODUCTION_THEME_CORRECTION_CUTOVER
OWNER_PRODUCTION_DEPLOYMENT_AUTHORIZATION=NO

This document describes the corrected production tooling after Report 123.
Report 121 reached deployment start, but the live NSSM supervisor respawned its
old child after the child PID was stopped. The new NSSM ownership contract
stops and configures the supervisor itself, so the child cannot race the
cutover or rollback. No production correction is performed by this document.

## Authoritative target

- Root: `C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales`
- App: `streamlit_opensea_sales\app_opensea_sales.py`
- Port: `8502`
- Branch: `main`
- Current production SHA at preparation: `05d9e99b6e22be7a64155dc136019a55ec1f5ad4`
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

## NSSM process and log contract

`OTG_app_opensea_sales` is the production lifecycle owner. It is an NSSM
Windows service; the Python/Streamlit process listening on 8502 is its
supervised child. Production stop/start therefore operates on the service,
waits for the service to be stopped and 8502 to have no listener, then starts
the service and proves the new listener is a descendant of the service. A
foreign listener or foreign service configuration fails closed.

Before each production service start, the orchestrator sets a unique stdout /
stderr pair under the external runtime log directory in NSSM `AppStdout` and
`AppStderr`. The child owns those files. The start wrapper does not append
metadata to either file after launch; the returned start result carries the
service child PID and exact paths. Deploy and rollback read only those paths
using an explicit shared-read handle, so a live child can be inspected without
a sharing violation and stale logs cannot satisfy or fail the current-launch
gate. Prior launch logs remain audit evidence. The v2 backup manifest records
the complete mutable NSSM configuration and its fingerprint for rollback.

## Source ownership versus target activation

The current supervised process is evaluated in two deliberately separate
ways. The source/ownership predicate proves that `OTG_app_opensea_sales` is
our NSSM service, that its Python/Streamlit child launches
`app_opensea_sales.py` on `127.0.0.1:8502`, and that the service owns the
listener. It does not silently accept a foreign app, port, service, or
supervisor. For the one documented correction boundary, passing
`-AllowLegacyMissingThemeSource` allows only `--theme.base` being absent and
reports `SourceThemeContract=KNOWN_LEGACY_DRIFT`; it does not allow `light`, an
invalid value, or duplicate/conflicting values. The allowance is used only for
read-only correction preflight, backup, stopping the known legacy source, and
restoring that exact source during guarded rollback.

The target/activation predicate remains strict. It calls the complete launch
contract and requires exactly one effective `--theme.base=dark` before a new
NSSM service start, on the new supervised child, and in the prepared-release
gate. After the correction deployment makes production dark, ordinary future
cutovers use the strict source predicate again; missing theme is not a
permanent production allowance.

## Managed refresh task reconciliation

`OTG_Derived_Data_Refresh_Production` and
`OTG_Metadata_Refresh_Production` are deployment-owned tasks. Their ownership
predicate checks the exact task name, PowerShell action, production working
directory, expected refresh script and approval phrase, one unchained action,
SYSTEM/Highest execution, `IgnoreNew`, `StartWhenAvailable`, enabled state,
and the canonical 15/60-minute repetition. An owned task may therefore be
reconciled in place when only the release-specific `-ReleasePython` changes;
the task is read back and the complete desired definition is checked after the
write. A same-name task that fails any ownership check remains a hard
`TASK_COLLISION` and is never deleted or overwritten.

Rollback restores task XML/state from the cutover backup. For an NSSM
supervised service, the historical rollback Python is the backed-up
`supervisor.application`. The Windows-reported child executable remains
audit-only evidence and is never used as the NSSM restore launcher authority.
Fresh rollback stdout/stderr paths are explicit activation overrides; all
other supervisor configuration is restored exactly.

## Mandatory Streamlit launch contract

`Get-ProductionStreamlitLaunchParameters` is the single source of truth for a
new production activation. It emits:

```text
-m streamlit run app_opensea_sales.py --server.address 127.0.0.1 --server.port 8502 --server.fileWatcherType none --server.headless true --browser.gatherUsageStats false --theme.base="dark"
```

The supervisor configuration is read back and validated before NSSM is
started. The same contract validator checks the active supervised child and
the prepared-release manifest. Missing, non-dark, duplicate, or otherwise
invalid `--theme.base` values fail closed with
`SUPERVISOR_THEME_BASE_DARK_REQUIRED` (or the prepared-manifest equivalent).
This is a launch contract; CSS is not a substitute.

## Corrected rollback contract

Rollback resolves 8502 through the supervisor into exactly one of these states:

- expected OTG Analytics service child present: validate ownership and stop the
  NSSM service;
- no listener present: continue restoration without stopping anything;
- foreign listener present: fail closed and leave it untouched.

Rollback restores Git, `.env`, all six managed artifact presence/hash states,
managed refresh task state, the prior active-runtime presence/hash state, and
the backed-up NSSM configuration before starting the old supervised child and
checking its health/current-launch logs. Database rollback is `NOT_AUTOMATIC`;
the approved schema changes are additive and old-app compatible. Remote main is
never moved back automatically.

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
address, required Streamlit flags, dark-theme, repository, branch, and
clean-worktree gates. For the documented legacy theme correction only, add
`-AllowLegacyMissingThemeSource` to distinguish a safe legacy source
(`SOURCE_OWNERSHIP_IDENTITY=PASS`, `SOURCE_THEME_BASE=MISSING`,
`SOURCE_THEME_CONTRACT=KNOWN_LEGACY_DRIFT`) from the strict prepared target
(`TARGET_PREPARED_THEME_BASE=dark`, `TARGET_THEME_CONTRACT=PASS`). The switch
does not weaken the listener, Python, Streamlit, app, port, address,
repository, branch, or clean-worktree gates, and it rejects light, invalid,
and duplicate theme values. Without the switch, the source predicate is
strict. Unrelated absolute app paths, 8501, 8504, gaming, and Caddy are
rejected.

## Validation state

Report 112 prepared release: invalidated by the Report 113 tooling finding.
Report 113: blocked before mutation; production mutation count `0`.
Report 123 successfully deployed release `05d9e99b...`, but its generated NSSM
parameters omitted the mandatory dark theme. The live service remains an audit
finding until a separately authorized correction cutover; this preparation does
not modify it.
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
release before a future owner authorization can be used. This task does not
authorize production deployment and performs no production mutation.

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
