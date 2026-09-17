# Report 135 — Production Trader OpenSea Profile Identity Diagnosis

REPORT_SEQUENCE=135
RESULT=DIAGNOSIS_COMPLETE_NO_MUTATION

PRODUCTION_RELEASE=b06482822ca0be95d0184125b15abac3cf8ae290
PRODUCTION_SERVICE=OTG_app_opensea_sales
PRODUCTION_SERVICE_STATE=Running
PRODUCTION_PID=29044
PRODUCTION_WORKTREE=CLEAN
STAGING_PROCESS_ROOT=C:\VAMBAM\Projects\OTG\staging\opensea_sales
STAGING_APPLICATION_ROOT=C:\VAMBAM\Projects\OTG\staging\opensea_sales\streamlit_opensea_sales
STAGING_8504_PID=123544
LIVE_8501_PID=104768
PUBLIC_ROUTE=https://otgos.run.place/analytics
PUBLIC_ROUTE_HEALTH=HTTP_200
INTERNAL_8502_HEALTH=HTTP_200
INTERNAL_8504_HEALTH=HTTP_200

TRADER_WALLET_PARITY=YES

The production and staging trader analytics snapshots both contain 1,343
wallets. Their application EARNED/USD ordering and the corresponding Top 20
wallets are identical. The numeric values below are read-only parity evidence;
the profile names are resolved independently from each profile snapshot.

| rank | wallet | earned_usd | trades | prod_profile | prod_status | prod_username | prod_display_name | prod_updated_at | staging_profile | staging_status | staging_username | staging_display_name | staging_updated_at | effective_prod_name | effective_staging_name | production_fallback_cause |
|---:|---|---:|---:|:---:|---|---|---|---|:---:|---|---|---|---|---|---|---|
| 1 | 0x16a72abfb841395fc70dcc3aad03d552d56fc09c | 2503.834337785884 | 54 | no | MISSING | — | — | — | yes | ok | — | — | 2026-09-07T08:29:55.489464+00:00 | NoName2621 | NoName2621 | PROFILE_MISSING |
| 2 | 0x45b6e9bb078a57565268d870855d3b92313f24c6 | 2136.1958054505267 | 178 | no | MISSING | — | — | — | yes | ok | HXX23 | HXX23 | 2026-09-07T17:55:59.364119+00:00 | NoName2847 | HXX23 | PROFILE_MISSING |
| 3 | 0xdcdcce60596ac5f24aa24de0b27238070f753c55 | 2039.1870030877162 | 179 | no | MISSING | — | — | — | yes | ok | — | — | 2026-09-09T09:55:56.673097+00:00 | NoName4900 | NoName4900 | PROFILE_MISSING |
| 4 | 0x463dedf4b71cd7e94d661c359818f9cd2071991b | 1299.2630210630116 | 549 | no | MISSING | — | — | — | yes | ok | BlackPointAnalytics | BlackPointAnalytics | 2026-09-07T18:55:57.884786+00:00 | NoName5010 | BlackPointAnalytics | PROFILE_MISSING |
| 5 | 0x3f7c5337c481716e61e578238745526d71e955aa | 1146.1939186629106 | 54 | no | MISSING | — | — | — | yes | ok | CowwithSmile | CowwithSmile | 2026-09-07T16:55:58.889128+00:00 | NoName1213 | CowwithSmile | PROFILE_MISSING |
| 6 | 0x4ead255cf3808e488f7b53188f43e93a84789a08 | 1041.9187267933069 | 67 | no | MISSING | — | — | — | yes | ok | furkanware | furkanware | 2026-09-07T20:55:55.515751+00:00 | NoName4002 | furkanware | PROFILE_MISSING |
| 7 | 0x06c8485604bbb06c8ae2e5b8e2f2b649671c0dc5 | 812.4506294330508 | 226 | no | MISSING | — | — | — | yes | ok | SerialPlug | SerialPlug | 2026-09-07T08:29:41.849677+00:00 | NoName1316 | SerialPlug | PROFILE_MISSING |
| 8 | 0xe10bed27bbee9b3f08feb3de95d5bebe6b50cfb6 | 702.275179510288 | 84 | no | MISSING | — | — | — | yes | ok | Dontrust | Dontrust | 2026-09-09T11:55:54.997713+00:00 | NoName9045 | Dontrust | PROFILE_MISSING |
| 9 | 0x0188d63ad3f38842382e9759be75fc911981efee | 421.83025102463785 | 2 | yes | stale | — | — | 2026-09-16T10:44:01.161864+00:00 | yes | ok | kadoka2 | kadoka2 | 2026-09-07T07:22:24.845486+00:00 | NoName6573 | kadoka2 | STALE |
| 10 | 0xa357fe4270bb88a39c099d33f429b4ad76de21cc | 407.46317939316503 | 26 | no | MISSING | — | — | — | yes | ok | Crypt0kingfx | Crypt0kingfx | 2026-09-08T17:56:00.665530+00:00 | NoName8177 | Crypt0kingfx | PROFILE_MISSING |
| 11 | 0xd81180d7f83fdaae549130f7dbe88fede735d1eb | 359.43841571433313 | 111 | no | MISSING | — | — | — | yes | ok | Usertwentyseven | Usertwentyseven | 2026-09-09T08:55:56.723581+00:00 | NoName7615 | Usertwentyseven | PROFILE_MISSING |
| 12 | 0xae418bf1b299039adcaf2db8cf9ccca599965005 | 310.7659842424756 | 516 | no | MISSING | — | — | — | yes | ok | StaySooned | StaySooned | 2026-09-08T21:55:55.083315+00:00 | NoName8181 | StaySooned | PROFILE_MISSING |
| 13 | 0xc5cfbff3e3cabc8d8ea8eab02af17152c57dc64d | 302.5067816922706 | 43 | no | MISSING | — | — | — | yes | ok | — | — | 2026-09-09T03:55:55.983441+00:00 | NoName0062 | NoName0062 | PROFILE_MISSING |
| 14 | 0x1e00b1aa2d0ce669879ef7e40d0985fe19f01329 | 256.0520844859798 | 340 | no | MISSING | — | — | — | yes | ok | 1E00B1 | 1E00B1 | 2026-09-07T08:30:08.982828+00:00 | NoName4489 | 1E00B1 | PROFILE_MISSING |
| 15 | 0xa35ce40317d2b2f8ef97a51564fcd1bccaaf2a33 | 235.14870015899285 | 4 | no | MISSING | — | — | — | yes | ok | OleP | OleP | 2026-09-08T17:56:00.873070+00:00 | NoName2474 | OleP | PROFILE_MISSING |
| 16 | 0x88eeb79b0cce7000142bbb474562663b4ab623db | 230.69394767817775 | 52 | no | MISSING | — | — | — | yes | ok | sufidyanov | sufidyanov | 2026-09-08T11:55:56.845486+00:00 | NoName5894 | sufidyanov | PROFILE_MISSING |
| 17 | 0x6a228f17ce14261095d278c64d036be4208c652a | 201.34712433649136 | 27 | no | MISSING | — | — | — | yes | ok | buyingstuff | buyingstuff | 2026-09-08T04:55:55.347662+00:00 | NoName9404 | buyingstuff | PROFILE_MISSING |
| 18 | 0x2d94ba99c06a6a4a4571f7918e4af161b9255115 | 173.52463748857912 | 57 | no | MISSING | — | — | — | yes | ok | — | — | 2026-09-07T08:30:31.364415+00:00 | NoName5930 | NoName5930 | PROFILE_MISSING |
| 19 | 0xe4a59c196346544a23c7bcc63752edf74f1942d3 | 159.77854953090463 | 74 | no | MISSING | — | — | — | yes | ok | ToonzzGG | ToonzzGG | 2026-09-09T12:55:54.726440+00:00 | NoName5580 | ToonzzGG | PROFILE_MISSING |
| 20 | 0x754d3b1cf7465018824e3fd4e198aca40c1d5f23 | 159.57560743829882 | 2743 | no | MISSING | — | — | — | yes | ok | ScrappyForge | ScrappyForge | 2026-09-08T07:55:57.506051+00:00 | NoName5809 | ScrappyForge | PROFILE_MISSING |

TOP20_PROFILE_DIFF_COUNT=16
TOP20_STAGING_HUMAN_PROD_FALLBACK_COUNT=16

The application exact profile-name order is human display_name, then human
username, then the persisted NoName#### alias. Canonical 0x labels are not
human labels. This is the same profile_name / is_canonical_wallet_label
semantics used by the application.

The requested visible-name spellings were not all present in the current
staging snapshot. Exact current observations are:

| requested spelling | current staging observation | wallet | production cause |
|---|---|---|---|
| HXK23 | exact string absent; current row is HXX23 | 0x45b6e9bb078a57565268d870855d3b92313f24c6 | PROFILE_MISSING |
| BlackPointAnalytics | BlackPointAnalytics | 0x463dedf4b71cd7e94d661c359818f9cd2071991b | PROFILE_MISSING |
| CowwithSmile | CowwithSmile | 0x3f7c5337c481716e61e578238745526d71e955aa | PROFILE_MISSING |
| furkanmore | exact string absent; current row is furkanware | 0x4ead255cf3808e488f7b53188f43e93a84789a08 | PROFILE_MISSING |
| SerialPlug | SerialPlug | 0x06c8485604bbb06c8ae2e5b8e2f2b649671c0dc5 | PROFILE_MISSING |
| Dontrust | Dontrust | 0xe10bed27bbee9b3f08feb3de95d5bebe6b50cfb6 | PROFILE_MISSING |
| kadoka2 | kadoka2 | 0x0188d63ad3f38842382e9759be75fc911981efee | STALE |
| CryptoKingfx | exact string absent; current row is Crypt0kingfx | 0xa357fe4270bb88a39c099d33f429b4ad76de21cc | PROFILE_MISSING |
| Usertwentyseven | Usertwentyseven | 0xd81180d7f83fdaae549130f7dbe88fede735d1eb | PROFILE_MISSING |
| StayGooned | exact string absent; current row is StaySooned | 0xae418bf1b299039adcaf2db8cf9ccca599965005 | PROFILE_MISSING |

## Profile snapshot comparison

PROD_PROFILE_SHA256=d77d031c1d2f30d4356e95811dfc178341cccc7be637bfdd4fd406cac586d9b7
STAGING_PROFILE_SHA256=9a919c32e85248e5f47855c528674d9bdb731c2e4e662880736113db33484d40
PROD_PROFILE_SIZE=96533
STAGING_PROFILE_SIZE=734803
PROD_GENERATED_AT=2026-09-17T11:04:49.972654+00:00
STAGING_GENERATED_AT=2026-09-17T10:55:54.008981+00:00
PROD_SCHEMA_VERSION=1
STAGING_SCHEMA_VERSION=1
PROD_SOURCE=opensea
STAGING_SOURCE=opensea
PROD_PROFILE_COUNT=20
STAGING_PROFILE_COUNT=1343
PROD_FALLBACK_NAMES_COUNT=1343
STAGING_FALLBACK_NAMES_COUNT=1343
PROD_STATUS_COUNTS=ok=0;no_profile=0;not_found=0;stale=20;error=0;other=0
STAGING_STATUS_COUNTS=ok=1330;no_profile=0;not_found=13;stale=0;error=0;other=0
PROD_HUMAN_USERNAME_COUNT=0
STAGING_HUMAN_USERNAME_COUNT=938
PROD_HUMAN_DISPLAY_NAME_COUNT=0
STAGING_HUMAN_DISPLAY_NAME_COUNT=979
PROD_REMOTE_AVATAR_COUNT=0
STAGING_REMOTE_AVATAR_COUNT=628

## Cutover and prepared-artifact lineage

The profile artifact was located from the Report 134 backup manifest dynamic
artifacts entry, not from an assumed backup path. The prepared artifact was
located from the prepared-release tree and its manifest.

PRE134_BACKUP_PROFILE_SHA256=2ff854b021b3f0b6be75abccf23981e271f07cb469164a339df132ed04ca5a0f
PRE134_BACKUP_PROFILE_GENERATED_AT=2026-09-17T10:14:18.540833+00:00
PRE134_BACKUP_PROFILE_COUNT=20
PREPARED133_PROFILE_SHA256=10a8807aee3032b0552e8acace9c6dc2d13c20718387159ce436c6f8b626c965
PREPARED133_PROFILE_GENERATED_AT=2026-09-17T09:14:13.367025+00:00
PREPARED133_PROFILE_COUNT=20
CURRENT_PROD_PROFILE_SHA256=d77d031c1d2f30d4356e95811dfc178341cccc7be637bfdd4fd406cac586d9b7
CURRENT_PROD_PROFILE_GENERATED_AT=2026-09-17T11:04:49.972654+00:00
CURRENT_PROD_PROFILE_COUNT=20
CURRENT_STAGING_PROFILE_SHA256=9a919c32e85248e5f47855c528674d9bdb731c2e4e662880736113db33484d40
CURRENT_STAGING_PROFILE_GENERATED_AT=2026-09-17T10:55:54.008981+00:00
CURRENT_STAGING_PROFILE_COUNT=1343

REPORT_134_PROFILE_TRACE=The Report 134 backup, prepared_release_133, and
current production all contain a bounded 20-record profile snapshot; staging
contains the larger 1,343-record enrichment snapshot. Report 134 recorded
METADATA_REFRESH_RESULT=PASS and its metadata task run rewrote the production
snapshot at 2026-09-17T11:04:49Z, but the resulting file still contains only
the old 20 records and all are stale. No evidence shows that a good staging
snapshot was deployed and then degraded.

PROFILE_LINEAGE_CLASSIFICATION=A_AND_C
PREPARED_PROFILE_SNAPSHOT_BEHIND_STAGING=YES
PROFILE_SNAPSHOT_REPLACED_DURING_CUTOVER=NO_GOOD_TO_BAD_REPLACEMENT_EVIDENCE
STAGING_ONLY_PROFILE_DATA_NOT_INCLUDED_IN_RELEASE=YES

The evidence supports A and C: the prepared/deployed production metadata
already lacked the staging identities, and the cutover preserved the
production-side bounded snapshot rather than importing staging-only profile
records. This is not a trader-ranking divergence and is not evidence that the
profile artifact was replaced from a complete snapshot and then lost names.

Report 134’s dynamic validator only required a structurally readable profile
snapshot and a fallback-name dictionary. It did not require profile coverage
parity, human-label coverage, or staging identity inclusion. Therefore its
profile gate could pass for this 20-record snapshot.

## Profile-sync audit

DEFAULT_REQUEST_LIMIT=20
AUTOSYNC_STALE_HOURS=720
OPENSEA_API_KEY_PRESENT=YES
PROFILE_SYNC_SNAPSHOT_GENERATED_AT=2026-09-17T11:04:49.972654+00:00
PROFILE_SYNC_LAST_ATTEMPT_MIN=2026-09-17T11:04:47.137748+00:00
PROFILE_SYNC_LAST_ATTEMPT_MAX=2026-09-17T11:04:49.972654+00:00
PROFILE_SYNC_ATTEMPT_SPAN_SECONDS=2.834906
PROFILE_SYNC_RECORDS_WITH_LAST_ATTEMPT=20
PROFILE_SYNC_RECORDS_RETAINED_STALE=20
PROFILE_SYNC_RECORDS_PROMOTED_OK=0
PROFILE_SYNC_RECORDS_PROMOTED_NOT_FOUND=0

The persisted snapshot proves a 20-record capped batch was attempted: all 20
records have tightly clustered new last_attempt_at values, all remain stale,
none received a new updated_at, and none became ok or not_found. Because
run_trader_profile_sync.py prints its detailed diagnostics to stdout while
Invoke-RefreshAdapter invokes it without a LogPath and discards the returned
child object, the exact error versus rate-limit fields were not persisted
anywhere inspected.

LAST_PROFILE_SYNC_RESULT=COMPLETED_WITHOUT_PERSISTED_DIAGNOSTICS
LAST_PROFILE_SYNC_REQUESTED=20
LAST_PROFILE_SYNC_ATTEMPTED=20
LAST_PROFILE_SYNC_SUCCESSFUL=0
LAST_PROFILE_SYNC_NOT_FOUND=0
LAST_PROFILE_SYNC_REMAINING_TARGETS=0
LAST_PROFILE_SYNC_ERRORS=NOT_PERSISTED_UNPROVABLE
LAST_PROFILE_SYNC_STOPPED_FOR_RATE_LIMIT=NOT_PERSISTED_UNPROVABLE
LAST_PROFILE_SYNC_STOPPED_FOR_RESERVE=NOT_PERSISTED_UNPROVABLE
LAST_PROFILE_SYNC_RATE_LIMIT_REMAINING=NOT_PERSISTED

This prevents an unsupported claim of a specific OpenSea API error. The
observable result is nevertheless a non-converging first batch: 20 attempts,
zero successful identity records, and no progress to later wallets.

## Scheduled-task behavior

METADATA_TASK_STATE=Ready
METADATA_TASK_LAST_RUN=2026-09-17T04:04:04-07:00
METADATA_TASK_LAST_RESULT=0
METADATA_TASK_NEXT_RUN=2026-09-17T05:04:04-07:00
METADATA_TASK_RELEASE_PYTHON=C:\VAMBAM\Projects\OTG\runtime\opensea_sales\releases\b06482822ca0be95d0184125b15abac3cf8ae290\.venv\Scripts\python.exe
METADATA_TASK_WORKING_DIRECTORY=C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales
METADATA_TASK_COMMAND=PowerShell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales\ops\production\refresh_production_metadata.ps1" -Execute -ApprovalPhrase REFRESH_OTG_METADATA_8502 -ReleasePython "<b064 runtime python>"

DERIVED_TASK_STATE=Ready
DERIVED_TASK_LAST_RUN=2026-09-17T04:49:49-07:00
DERIVED_TASK_LAST_RESULT=0
DERIVED_TASK_NEXT_RUN=2026-09-17T05:04:04-07:00

The task definitions are the owned production definitions: PowerShell action,
the exact production working directory and refresh scripts, the expected
approval phrases, SYSTEM principal, Highest run level, IgnoreNew, and
StartWhenAvailable. An hourly metadata cycle is therefore scheduled. It can
eventually advance by 20 wallets per successful cycle, but the current
snapshot shows no progress beyond its first 20-record batch. Waiting alone
does not guarantee convergence while that batch continues to fail or
rate-limit.

AUTOSYNC_RECENT_NEGATIVE_POLICY=The current production snapshot has no
not_found or no_profile records; it has 20 stale records. The code’s
720-hour threshold would also prevent recent negative records from being
selected merely because they are recent. Staging currently has 13 not_found
records, but those are staging evidence and are not current production records.

## Root-cause classification

ROOT_CAUSE_CLASSIFICATION=
PREPARED_PROFILE_SNAPSHOT_BEHIND_STAGING;
PROFILE_SYNC_LIMIT_NOT_YET_CONVERGED;
STAGING_ONLY_PROFILE_DATA_NOT_INCLUDED_IN_RELEASE;
RECENT_NEGATIVE_PROFILE_CACHE_BLOCKING_REFRESH=NO_FOR_CURRENT_PRODUCTION;
PRODUCTION_PROFILE_SYNC_API_ERROR=UNCONFIRMED_BECAUSE_DIAGNOSTICS_WERE_NOT_PERSISTED;
PROFILE_SNAPSHOT_REPLACED_DURING_CUTOVER=NOT_SUPPORTED_BY_HASH/COUNT_LINEAGE

The primary diagnosis is profile enrichment divergence, not ranking
calculation divergence. Production has only the 20-record bounded snapshot
and a failed/non-progressing current sync batch; staging has the broader
successful enrichment set.

## Recommended repair — not executed

SAFE_REPAIR_METHOD=NO_APPLICATION_REDEPLOY; perform a controlled,
canonical-wallet metadata repair. Prefer an official OpenSea refresh for
missing/stale production records with quota reserve and persisted diagnostics.
If a staging-to-production merge is approved, preserve existing production
records and import only strictly better, valid staging profile records for
the same canonical wallet, followed by artifact/schema/reader validation.
Do not blindly copy the entire staging file or overwrite better production
records.

SERVICE_RESTART_REQUIRED=NO

The defect is in dynamic profile metadata. A guarded data refresh or
canonical-wallet merge should be sufficient; no application code, service
restart, production redeploy, task change, or Caddy change is indicated by
this evidence.

PRODUCTION_MUTATION_COUNT=0
STAGING_MUTATION_COUNT=0
FINAL_STATUS=DIAGNOSIS_COMPLETE_NO_MUTATION
