REPORT_SEQUENCE=139
RESULT=DIAGNOSIS_COMPLETE

OPENSEA_KEY_PRESENT=YES
OPENSEA_KEY_LENGTH=32
OPENSEA_KEY_FINGERPRINT12=017c54946327
KEY_FORMAT_GATE=PASS; canonical parsers/.env definition is singular, non-empty after parser normalization, has no surrounding whitespace or embedded line breaks, and is not a placeholder or quoted-empty value.

OTHER_KEY_SOURCES_FOUND=YES; C:\VAMBAM\Projects\OTG\parsers\.env:OPENSEA_API_KEY:length=32:fingerprint12=017c54946327; C:\VAMBAM\Projects\OTG\parsers\parser_opensea_listings_v2\.env:OPENSEA_API_KEY:length=32:fingerprint12=2323880368a5
PROFILE_SYNC_USES_SAME_KEY_AS_OTHER_OPENSEA_PARSERS=NO_FOR_LISTINGS_V2; refresh_opensea_account_profiles.py and parser_opensea_sales.py use the canonical parsers/.env key, while the approved listings_v2 parser has a distinct key source. No values were exposed.

ACCOUNT_ENDPOINT_HTTP_STATUS=401; supported by the Report 138 account probe and the bounded account request in this diagnosis.
ACCOUNT_ENDPOINT_RESPONSE_CLASS=HTTP_ERROR_AUTH
CHAINS_ENDPOINT_HTTP_STATUS=200
CHAINS_ENDPOINT_RESPONSE_CLASS=SUCCESS
CHAINS_ENDPOINT_RATE_LIMIT=120
CHAINS_ENDPOINT_RATE_LIMIT_REMAINING=101
CHAINS_ENDPOINT_RATE_LIMIT_RESET=1789654300
RESOLVE_ENDPOINT_HTTP_STATUS=NOT_RUN_REQUEST_CAP_REACHED; the account-vs-global distinction was established by the account 401 and chains 200; no fourth request was made.

SAME_KEY_RECENT_REST_SUCCESS=UNKNOWN
LAST_KNOWN_SUCCESS_TIME=2026-09-16T05:55:18.2275796Z; successful REST collection-event evidence belongs to parser_opensea_listings_v2 and its different key fingerprint, so it is not same-key evidence.
LAST_KNOWN_SUCCESS_ENDPOINT_CLASS=REST_COLLECTION_EVENTS_BACKFILL_DIFFERENT_KEY

ROOT_CAUSE_CLASSIFICATION=ACCOUNT_ENDPOINT_ONLY_AUTH_FAILURE
ROOT_CAUSE_EVIDENCE=The canonical 32-byte-key source passes format checks; the same key receives HTTP 200 from /api/v2/chains but HTTP 401 from /api/v2/accounts/{address}. This isolates the observed failure to account-endpoint authorization/entitlement or account-endpoint credential validity, without evidence of a profile-code endpoint/source defect.
KEY_REPLACEMENT_REQUIRED=UNKNOWN; credential replacement or account-endpoint permission correction may be required, but this read-only task does not distinguish those remediations and performed neither.
CODE_CHANGE_REQUIRED=NO

PRODUCTION_PROFILE_COUNT=1343
PRODUCTION_OK_COUNT=1330
PRODUCTION_HUMAN_USERNAME_COUNT=938
PRODUCTION_HUMAN_DISPLAY_NAME_COUNT=979
PRODUCTION_SERVICE_HEALTH=PASS; OTG_app_opensea_sales Running, 127.0.0.1:8502 HTTP 200, listener PID 29044 observed read-only.
PUBLIC_ROUTE_GATE=PASS; https://otgos.run.place/analytics HTTP 200 via the repository Python TLS client.
PRODUCTION_MUTATION_COUNT=0

PRODUCTION_RELEASE=b06482822ca0be95d0184125b15abac3cf8ae290
PRODUCTION_GIT_MUTATED=NO
PRODUCTION_ENV_MUTATED=NO
PRODUCTION_PROFILE_SNAPSHOT_MUTATED=NO
PRODUCTION_SERVICE_RESTARTED=NO
PRODUCTION_TASKS_MUTATED=NO
PRODUCTION_DATABASE_MUTATED=NO
PRODUCTION_CADDY_MUTATED=NO
STAGING_MUTATED=NO

FINAL_STATUS=DIAGNOSIS_COMPLETE_NO_MUTATION
