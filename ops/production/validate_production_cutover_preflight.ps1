[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ExpectedOldHead,
    [Parameter(Mandatory=$true)][string]$ExpectedReleaseHead,
    [Parameter(Mandatory=$true)][string]$PreparedReleaseRoot,
    [Parameter(Mandatory=$true)][string]$PreparedReleaseManifest,
    [Parameter(Mandatory=$true)][string]$PreparedReleaseManifestSha256,
    [Parameter(Mandatory=$true)][string]$ExpectedMainHead
)
$ErrorActionPreference='Stop'
$context=$null
function Read-GitValue([string[]]$Arguments) {
    $value=& git -c ('safe.directory='+$script:ExpectedRoot) -C $script:ExpectedRoot @Arguments 2>&1
    if($LASTEXITCODE -ne 0){throw 'GIT_READ_FAILED'}
    ($value -join "`n").Trim()
}
function Read-SchemaState([hashtable]$Environment,[string]$PsqlPath) {
    $query=@"
SELECT current_setting('transaction_read_only') || '|' ||
CASE WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='site_visit_sessions' AND column_name='browser_visitor_hash')
 AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='site_visit_sessions' AND column_name='identity_version')
 AND EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE connamespace='public'::regnamespace AND conname='site_visit_sessions_identity_version_chk')
 AND EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE connamespace='public'::regnamespace AND conname='site_visit_sessions_browser_visitor_hash_hex_chk')
 AND EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE connamespace='public'::regnamespace AND conname='site_visit_sessions_identity_v2_hash_chk')
 AND EXISTS (SELECT 1 FROM pg_catalog.pg_indexes WHERE schemaname='public' AND indexname='site_visit_sessions_browser_visitor_started_idx')
 THEN 'READY' ELSE 'NOT_READY' END || '|' ||
CASE WHEN NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE connamespace='public'::regnamespace AND conname='site_visit_sessions_mode_chk' AND lower(pg_get_constraintdef(oid)) LIKE '%trader%') THEN 'ABSENT' ELSE 'PRESENT' END || '|' ||
CASE WHEN NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='site_product_events') THEN 'ABSENT' ELSE 'PRESENT' END || '|' ||
CASE WHEN NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='user_feedback') THEN 'ABSENT' ELSE 'PRESENT' END;
"@
    $Environment['PGOPTIONS']='-c default_transaction_read_only=on -c statement_timeout=5000'
    $result=Invoke-ChildProcess $PsqlPath @('-X','-A','-t','-q','-v','ON_ERROR_STOP=1','-c',$query) $script:ExpectedRoot 30 $Environment
    $line=(@($result.StdOut -split "`r?`n"|Where-Object { -not [string]::IsNullOrWhiteSpace($_) })|Select-Object -Last 1).Trim()
    $parts=$line -split '\|';if($parts.Count -ne 5){throw 'DB_SCHEMA_RESULT_INVALID'}
    [pscustomobject]@{ReadOnly=$parts[0];StableBrowserIdentity=$parts[1];TraderMode=$parts[2];ProductEvents=$parts[3];UserFeedback=$parts[4]}
}
try {
    . (Join-Path $PSScriptRoot 'production_update_common.ps1')
    Assert-ProductionTarget
    if(-not(Test-Path $script:ExpectedRoot -PathType Container)){throw 'PRODUCTION_ROOT_MISSING'}
    if(-not(Test-Path $script:ExpectedApp -PathType Leaf)){throw 'PRODUCTION_APP_MISSING'}
    $context=New-ProductionExecutionContext @{ExpectedOldHead=$ExpectedOldHead;ExpectedReleaseHead=$ExpectedReleaseHead;PreparedReleaseRoot=$PreparedReleaseRoot;PreparedReleaseManifest=$PreparedReleaseManifest;PreparedReleaseManifestSha256=$PreparedReleaseManifestSha256;BackupManifest='';BackupRoot=''}
    $head=Read-GitValue @('rev-parse','HEAD');$branch=Read-GitValue @('branch','--show-current');$status=Read-GitValue @('status','--porcelain')
    if($branch -ne 'main'){throw 'PRODUCTION_BRANCH_MISMATCH'};if($status){throw 'PRODUCTION_WORKTREE_NOT_CLEAN'};if($head -ne $ExpectedOldHead){throw 'EXPECTED_OLD_HEAD_MISMATCH'}
    $process=Get-8502Process
    $appMatch=[regex]::Match([string]$process.CommandLine,'(?i)(?:"(?<quoted>[^"\r\n]*app_opensea_sales\.py)"|(?<bare>[^\s"\r\n]*app_opensea_sales\.py))');$appToken=if($appMatch.Groups['quoted'].Success){$appMatch.Groups['quoted'].Value}else{$appMatch.Groups['bare'].Value};$entryMode=if([IO.Path]::IsPathRooted($appToken)){'ABSOLUTE_ENTRYPOINT'}else{'RELATIVE_ENTRYPOINT'}
    $tools=Get-PostgresTools;foreach($name in @('pg_dump','pg_restore','psql')){if(-not$tools.ContainsKey($name)){throw ('POSTGRES_TOOL_MISSING:'+ $name)}}
    if(-not(Test-Path $context.EnvPath -PathType Leaf)){throw 'PRODUCTION_ENV_MISSING'};$dbEnvironment=Get-DatabaseEnvironment $context.EnvPath -Required
    $versions=@{};foreach($name in @('pg_dump','pg_restore','psql')){$versions[$name]=(Invoke-ChildProcess $tools[$name] @('--version') $script:ExpectedRoot 30 @{}).StdOut.Trim()}
    $schema=Read-SchemaState $dbEnvironment $tools.psql;if($schema.ReadOnly -ne 'on'){throw 'DB_NOT_READ_ONLY'};$preMigration=($schema.TraderMode -eq 'ABSENT' -and $schema.ProductEvents -eq 'ABSENT' -and $schema.UserFeedback -eq 'ABSENT');$postMigration=($schema.TraderMode -eq 'PRESENT' -and $schema.ProductEvents -eq 'PRESENT' -and $schema.UserFeedback -eq 'PRESENT');if($schema.StableBrowserIdentity -ne 'READY' -or (-not$preMigration -and -not$postMigration)){throw 'DB_SCHEMA_DRIFT'}
    $prepared=Read-PreparedReleaseManifest $PreparedReleaseManifest $PreparedReleaseManifestSha256 $ExpectedReleaseHead $context
    $main=Read-GitValue @('rev-parse','origin/main');if($main -ne $ExpectedMainHead){throw 'MAIN_BASELINE_MISMATCH'}
    Write-KV 'MODE' 'READ_ONLY_PREFLIGHT';Write-KV 'PRODUCTION_PROCESS_IDENTITY' 'PASS';Write-KV 'LIVE_8502_PID' $process.ProcessId;Write-KV 'LIVE_8502_ENTRYPOINT_MODE' $entryMode;Write-KV 'LIVE_8502_COMMAND_LINE_SANITIZED' $process.CommandLine;Write-KV 'POSTGRES_PG_DUMP_PATH' $tools.pg_dump;Write-KV 'POSTGRES_PG_RESTORE_PATH' $tools.pg_restore;Write-KV 'POSTGRES_PSQL_PATH' $tools.psql;Write-KV 'POSTGRES_PG_DUMP_VERSION' $versions.pg_dump;Write-KV 'POSTGRES_PG_RESTORE_VERSION' $versions.pg_restore;Write-KV 'POSTGRES_PSQL_VERSION' $versions.psql;Write-KV 'POSTGRES_TOOL_DISCOVERY' 'PASS';Write-KV 'DB_READ_ONLY_GATE' 'PASS';Write-KV 'DB_SCHEMA_GATE' 'PASS';Write-KV 'PREPARED_RELEASE_GATE' 'PASS';Write-KV 'MAIN_BASELINE_GATE' 'PASS';Write-KV 'MUTATION_EXECUTED' 'NO';Write-KV 'CUTOVER_PREFLIGHT' 'PASS'
}
catch {Write-KV 'MUTATION_EXECUTED' 'NO';Write-KV 'CUTOVER_PREFLIGHT' 'FAIL';throw}
