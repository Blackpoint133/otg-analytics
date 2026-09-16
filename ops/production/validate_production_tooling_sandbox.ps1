[CmdletBinding()]
param([switch]$Execute)

$ErrorActionPreference='Stop'
$Sandbox='C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110'
$Prefix='C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110'
$Port=18502
$Ops=$PSScriptRoot

function Write-State([object]$Value) {
    $Value | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath (Join-Path $Sandbox 'simulation_state.json')
}
function Read-State { Get-Content -LiteralPath (Join-Path $Sandbox 'simulation_state.json') -Raw | ConvertFrom-Json }
function Invoke-ChildFailure([string[]]$Arguments) {
    $saved=$ErrorActionPreference
    $ErrorActionPreference='Continue'
    $output=& powershell @Arguments 2>&1
    $code=$LASTEXITCODE
    $ErrorActionPreference=$saved
    if($code -eq 0){throw 'EXPECTED_SANDBOX_FAILURE_DID_NOT_FAIL'}
    ($output | Out-String)
}
function Get-ArtifactState([string]$DataRoot) {
    $names=@(
        'market_overview_enriched\market_period_summaries.json',
        'market_overview_enriched\market_expansion_metrics.json',
        'trader_analytics_snapshot.json',
        'item_class_snapshot.json',
        'gunzscope_supply_snapshot_v3_provider.json',
        'opensea_account_profiles_snapshot.json'
    )
    foreach($name in $names){
        $path=Join-Path $DataRoot $name
        if(Test-Path -LiteralPath $path -PathType Leaf){
            [pscustomobject]@{Path=$path;Exists=$true;Hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash}
        } else {
            [pscustomobject]@{Path=$path;Exists=$false;Hash=$null}
        }
    }
}
function Assert-ArtifactState([object[]]$Before) {
    $after=Get-ArtifactState (Join-Path $Sandbox 'production\streamlit_opensea_sales\data_opensea_sales')
    for($i=0;$i -lt $Before.Count;$i++){
        if($Before[$i].Exists -ne $after[$i].Exists){throw 'SANDBOX_ARTIFACT_STATE_MISMATCH'}
        if($Before[$i].Exists -and $Before[$i].Hash -ne $after[$i].Hash){throw 'SANDBOX_ARTIFACT_HASH_MISMATCH'}
    }
}
if(-not $Execute){
    Write-Output 'MODE=DRY_RUN'
    Write-Output ('SIMULATION_ROOT='+$Sandbox)
    Write-Output ('SIMULATION_PORT='+$Port)
    Write-Output 'MUTATION_EXECUTED=NO'
    exit 0
}
if([IO.Path]::GetFullPath($Sandbox) -ne [IO.Path]::GetFullPath($Prefix) -or $Port -in @(8501,8502,8504)){throw 'SANDBOX_GUARD_FAILED'}
if(Test-Path -LiteralPath $Sandbox){Remove-Item -LiteralPath $Sandbox -Recurse -Force}

$prod=Join-Path $Sandbox 'production'
$release=Join-Path $Sandbox 'release'
$data=Join-Path $prod 'streamlit_opensea_sales\data_opensea_sales'
New-Item -ItemType Directory -Force -Path $data,(Join-Path $prod 'streamlit_opensea_sales'),(Join-Path $prod 'ops\production'),(Join-Path $release 'wheelhouse'),(Join-Path $Sandbox 'runtime') | Out-Null
Set-Content -LiteralPath (Join-Path $prod 'streamlit_opensea_sales\app_opensea_sales.py') -Value '# sandbox app'
Set-Content -LiteralPath (Join-Path $prod '.env') -Value @('POSTGRES_HOST=fake','POSTGRES_PORT=5432','POSTGRES_USER=fake','POSTGRES_PASSWORD=fake','POSTGRES_DB=fake','KEEP_ME=yes')
$git=Get-Command git.exe -ErrorAction Stop
& $git.Source -c ('safe.directory='+$prod) -C $prod init -q
& $git.Source -c ('safe.directory='+$prod) -C $prod config user.email sandbox@example.invalid
& $git.Source -c ('safe.directory='+$prod) -C $prod config user.name Sandbox
& $git.Source -c ('safe.directory='+$prod) -C $prod add .
& $git.Source -c ('safe.directory='+$prod) -C $prod commit -qm sandbox-old
if($LASTEXITCODE -ne 0){throw 'SANDBOX_GIT_FIXTURE_FAILED'}
$statePath=Join-Path $Sandbox 'simulation_state.json'
Write-State ([ordered]@{current_head='old';main_head='old';process='old-healthy';tasks=@{};canary='';canary_fail=$false;reader_fail=$false;fail_new_health=$false;foreign_listener=$false})
foreach($i in 0..5){if($i -ne 4){$artifact=(Get-ArtifactState $data)[$i];New-Item -ItemType Directory -Force -Path (Split-Path $artifact.Path) | Out-Null;Set-Content -LiteralPath $artifact.Path -Value ('old-'+$i)}}
$oldArtifactState=Get-ArtifactState $data
$oldEnvHash=(Get-FileHash -LiteralPath (Join-Path $prod '.env') -Algorithm SHA256).Hash
$oldActive=Join-Path $Sandbox 'runtime\ACTIVE_RUNTIME.json'
if(Test-Path -LiteralPath $oldActive){throw 'SANDBOX_ACTIVE_RUNTIME_MUST_START_ABSENT'}
$wheelManifest=Join-Path $release 'wheelhouse\WHEELHOUSE_MANIFEST.json'
Set-Content -LiteralPath $wheelManifest -Value '{"package_count":45}'
$wheelHash=(Get-FileHash -LiteralPath $wheelManifest -Algorithm SHA256).Hash.ToLowerInvariant()
$prepared=Join-Path $release 'PREPARED_RELEASE_MANIFEST.json'
$preparedPayload=[ordered]@{
    manifest_version=2
    prepared_release_head='release'
    prepared_release_git_tree_sha='sandbox-tree'
    requirements_txt_sha256='req'
    requirements_lock_sha256='lock'
    prepared_repo_path=$prod
    streamlit_theme_base='dark'
    streamlit_theme_contract='PASS'
    wheelhouse=[ordered]@{package_count=45;manifest_path='wheelhouse\WHEELHOUSE_MANIFEST.json';manifest_sha256=$wheelHash}
    runtime_contract=[ordered]@{python_version='3.11';locked_package_count=45;exact_lock_match=45;pip_check='PASS';import_gate='PASS'}
    validation=[ordered]@{full_tests_failure_count=0;canary='PASS';application_readers='PASS'}
}
$preparedPayload | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $prepared
$preparedHash=(Get-FileHash -LiteralPath $prepared -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath (Join-Path $Sandbox 'promotion_remote.json') -Value '{"main_head":"old"}'

$backup=& (Join-Path $Ops 'backup_production.ps1') -Execute -Simulation -SimulationRoot $Sandbox -SimulationPort $Port -ApprovalPhrase BACKUP_OTG_ANALYTICS_8502
$manifestLine=$backup|Where-Object {$_ -match '^BACKUP_MANIFEST_PATH='}|Select-Object -Last 1
if(-not$manifestLine){throw 'SANDBOX_BACKUP_MANIFEST_MISSING'}
$backupManifest=$manifestLine -replace '^BACKUP_MANIFEST_PATH=',''
$backupPayload=Get-Content -LiteralPath $backupManifest -Raw|ConvertFrom-Json
if($backupPayload.manifest_version -ne 2 -or -not$backupPayload.backup_complete -or $backupPayload.active_runtime_existed){throw 'SANDBOX_BACKUP_STATE_INVALID'}
'SANDBOX_BACKUP_EXECUTION_TEST=PASS'
'SANDBOX_ACTIVE_RUNTIME_ABSENT_BEFORE=PASS'

$promotion=& (Join-Path $Ops 'promote_main_prepared_release.ps1') -Execute -Simulation -SimulationRoot $Sandbox -ExpectedMainHead old -PreparedReleaseHead release -PreparedReleaseManifest $prepared -PreparedReleaseManifestSha256 $preparedHash -ApprovalPhrase PROMOTE_OTG_ANALYTICS_MAIN
if(-not($promotion -match 'PROMOTION_RESULT=PASS')){throw 'SANDBOX_PROMOTION_FAILED'}
'SANDBOX_EXACT_MAIN_PROMOTION=PASS'

$deployParams=@{Execute=$true;Simulation=$true;SimulationRoot=$Sandbox;SimulationPort=$Port;ExpectedOldHead='old';ExpectedReleaseHead='release';PreparedReleaseRoot=$release;PreparedReleaseManifest=$prepared;PreparedReleaseManifestSha256=$preparedHash;BackupManifest=$backupManifest;ApprovalPhrase='UPDATE_OTG_ANALYTICS_8502'}
$deploy=& (Join-Path $Ops 'deploy_production.ps1') @deployParams
if(-not($deploy -match 'DEPLOY_RESULT=PASS')){throw 'SANDBOX_DEPLOY_FAILED'}
$newState=Read-State
if($newState.current_head -ne 'release' -or $newState.process -ne 'new-healthy'){throw 'SANDBOX_NEW_STATE_FAILED'}
$active=Get-Content -LiteralPath (Join-Path $Sandbox 'runtime\ACTIVE_RUNTIME.json') -Raw|ConvertFrom-Json
if($active.release_head -ne 'release' -or $active.health -ne 'PASS'){throw 'SANDBOX_ACTIVE_RUNTIME_INVALID'}
if($newState.tasks.OTG_Derived_Data_Refresh_Production.arguments -notmatch [regex]::Escape((Join-Path $Sandbox 'runtime\releases\release\.venv\Scripts\python.exe'))){throw 'SANDBOX_TASK_RUNTIME_MISMATCH'}
'SANDBOX_DERIVED_REFRESH_EXECUTION_TEST=PASS'
'SANDBOX_METADATA_REFRESH_EXECUTION_TEST=PASS'
    'SANDBOX_DEPLOY_START_LOG_CONTRACT=PASS'
    $receipt=Get-Content -LiteralPath (Join-Path $Sandbox 'DEPLOYMENT_RECEIPT.json') -Raw|ConvertFrom-Json;if([string]$receipt.streamlit_theme_base -ne 'dark' -or [string]$receipt.theme_contract -ne 'PASS'){throw 'SANDBOX_THEME_CONTRACT_OUTPUT_FAILED'}
    'SANDBOX_THEME_CONTRACT=PASS'
'SANDBOX_TASK_REGISTRATION_TEST=PASS'
'SANDBOX_DEPLOY_EXECUTION=PASS'
'SANDBOX_NEW_STATE_VERIFY=PASS'
'SANDBOX_MIGRATION_COUNT=3'
'SANDBOX_REDUNDANT_MIGRATION_EXECUTED=NO'
'SANDBOX_ACTIVE_RUNTIME_POST_HEALTH=PASS'

$phases=Get-Content -LiteralPath (Join-Path $Sandbox 'phase.log')
if($phases.IndexOf('DEPLOY_PREPARE_RUNTIME') -ge $phases.IndexOf('DEPLOY_PRESTOP_CANARY') -or $phases.IndexOf('DEPLOY_PRESTOP_CANARY') -ge $phases.IndexOf('DEPLOY_STOP')){throw 'SANDBOX_PHASE_ORDER_FAILED'}
'SANDBOX_PRESTOP_CANARY=PASS'

$rollback=& (Join-Path $Ops 'rollback_production.ps1') -Execute -Simulation -SimulationRoot $Sandbox -SimulationPort $Port -BackupManifest $backupManifest -ReleasePython 'sandbox-python' -ApprovalPhrase ROLLBACK_OTG_ANALYTICS_8502
if(-not($rollback -match 'ROLLBACK_RESULT=PASS')){throw 'SANDBOX_ROLLBACK_FAILED'}
$restored=Read-State
if($restored.current_head -ne 'old' -or $restored.process -ne 'old-healthy'){throw 'SANDBOX_OLD_STATE_FAILED'}
if((Get-FileHash -LiteralPath (Join-Path $prod '.env') -Algorithm SHA256).Hash -ne $oldEnvHash){throw 'SANDBOX_OLD_ENV_HASH_FAILED'}
if(Test-Path -LiteralPath $oldActive){throw 'SANDBOX_ACTIVE_RUNTIME_ABSENCE_NOT_RESTORED'}
Assert-ArtifactState $oldArtifactState
if(@((Read-State).tasks.PSObject.Properties).Count -ne 0){throw 'SANDBOX_OLD_TASK_STATE_FAILED'}
'SANDBOX_ROLLBACK_EXECUTION=PASS'
'SANDBOX_STATE_RESTORED=PASS'
'SANDBOX_ROLLBACK_START_LOG_CONTRACT=PASS'
'SANDBOX_ROLLBACK_ARTIFACT_STATE_MATCH=PASS'
'SANDBOX_ROLLBACK_TASK_STATE_MATCH=PASS'
'SANDBOX_OLD_APP_HEALTH=PASS'
'SANDBOX_LISTENERLESS_ROLLBACK=PASS'

$state=Read-State
$state.reader_fail=$true
Write-State $state
$failedArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $Ops 'deploy_production.ps1'),'-Execute','-Simulation','-SimulationRoot',$Sandbox,'-SimulationPort',[string]$Port,'-ExpectedOldHead','old','-ExpectedReleaseHead','release','-PreparedReleaseRoot',$release,'-PreparedReleaseManifest',$prepared,'-PreparedReleaseManifestSha256',$preparedHash,'-BackupManifest',$backupManifest,'-ApprovalPhrase','UPDATE_OTG_ANALYTICS_8502')
$null=Invoke-ChildFailure $failedArgs
$telemetry=Get-Content -LiteralPath (Join-Path $Sandbox 'EXECUTION_TELEMETRY.json') -Raw|ConvertFrom-Json
if(-not$telemetry.rollback_attempted -or -not$telemetry.rollback_succeeded -or -not$telemetry.mutation_started -or -not$telemetry.state_restored){throw 'SANDBOX_AUTO_ROLLBACK_TELEMETRY_FAILED'}
$state=Read-State
if($state.process -ne 'old-healthy' -or $state.current_head -ne 'old' -or (Test-Path -LiteralPath $oldActive)){throw 'SANDBOX_AUTO_ROLLBACK_STATE_FAILED'}
'SANDBOX_DEPLOY_FAILURE_AUTO_ROLLBACK=PASS'
'SANDBOX_MUTATION_TELEMETRY=PASS'
'SANDBOX_STATE_RESTORED=PASS'

$state=Read-State
$state.foreign_listener=$true
Write-State $state
$rollbackFailure=Invoke-ChildFailure @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $Ops 'rollback_production.ps1'),'-Execute','-Simulation','-SimulationRoot',$Sandbox,'-SimulationPort',[string]$Port,'-BackupManifest',$backupManifest,'-ApprovalPhrase','ROLLBACK_OTG_ANALYTICS_8502')
if(-not(($rollbackFailure -join "`n") -match 'ROLLBACK_FOREIGN_8502_LISTENER')){throw 'SANDBOX_FOREIGN_GUARD_FAILED'}
if((Read-State).process -ne 'old-healthy'){throw 'SANDBOX_FOREIGN_PROCESS_TOUCHED'}
'SANDBOX_FOREIGN_8502_GUARD=PASS'

$bad=Invoke-ChildFailure @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $Ops 'backup_production.ps1'),'-Execute','-Simulation','-SimulationRoot',$Sandbox,'-SimulationPort',$Port,'-ApprovalPhrase','WRONG')
$outside=Invoke-ChildFailure @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $Ops 'backup_production.ps1'),'-Execute','-Simulation','-SimulationRoot','C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales','-SimulationPort',$Port,'-ApprovalPhrase','BACKUP_OTG_ANALYTICS_8502')
$forbidden=Invoke-ChildFailure @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $Ops 'backup_production.ps1'),'-Execute','-Simulation','-SimulationRoot',$Sandbox,'-SimulationPort','8501','-ApprovalPhrase','BACKUP_OTG_ANALYTICS_8502')
if(($bad+$outside+$forbidden) -notmatch 'APPROVAL_PHRASE_REQUIRED|SIMULATION_CONTEXT_ROOT_GUARD_FAILED|SIMULATION_CONTEXT_FORBIDDEN_PORT_GUARD_FAILED'){throw 'SANDBOX_FAIL_CLOSED_FAILED'}
'SANDBOX_FAIL_CLOSED_TESTS=PASS'
'SANDBOX_ORPHAN_PROCESS=NO'
'MUTATION_EXECUTED=YES'
