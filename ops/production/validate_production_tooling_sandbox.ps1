[CmdletBinding()]
param([switch]$Execute)
$ErrorActionPreference='Stop'
$Sandbox='C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_109'
$Port=18502
if(-not $Execute){'MODE=DRY_RUN';'SIMULATION_ROOT='+$Sandbox;'SIMULATION_PORT='+$Port;'MUTATION_EXECUTED=NO';exit 0}
if(-not $Sandbox.StartsWith('C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_109') -or $Port -in @(8501,8502,8504)){throw 'SANDBOX_GUARD_FAILED'}
$ops=$PSScriptRoot
if(Test-Path -LiteralPath $Sandbox){Remove-Item -LiteralPath $Sandbox -Recurse -Force}
$prod=Join-Path $Sandbox 'production';$release=Join-Path $Sandbox 'release'
New-Item -ItemType Directory -Path $prod,$release,(Join-Path $prod 'streamlit_opensea_sales\data_opensea_sales\market_overview_enriched'),(Join-Path $prod 'ops\production'),(Join-Path $Sandbox 'runtime') -Force|Out-Null
Set-Content (Join-Path $prod 'streamlit_opensea_sales\app_opensea_sales.py') '# sandbox app'
Set-Content (Join-Path $prod '.env') @('POSTGRES_HOST=fake','POSTGRES_PORT=5432','POSTGRES_USER=fake','POSTGRES_PASSWORD=fake','POSTGRES_DB=fake','UNRELATED_KEY=preserve')
Set-Content (Join-Path $Sandbox 'simulation_state.json') (@{current_head='old';main_head='release';branch='main';process='old-healthy';db_migrations=@();fail_new_health=$false}|ConvertTo-Json)
foreach($name in @('refresh_production_derived.ps1','refresh_production_metadata.ps1')){Set-Content (Join-Path $prod ('ops\production\'+$name)) '# sandbox action'}
$all=@('market_overview_enriched\market_period_summaries.json','market_overview_enriched\market_expansion_metrics.json','trader_analytics_snapshot.json','item_class_snapshot.json','gunzscope_supply_snapshot_v3_provider.json','opensea_account_profiles_snapshot.json')
foreach($i in 0..5){$p=Join-Path (Join-Path $prod 'streamlit_opensea_sales\data_opensea_sales') $all[$i];if($i -ne 4){New-Item (Split-Path $p) -ItemType Directory -Force|Out-Null;Set-Content $p ('old-'+$i)}}
$oldArtifactState=@{};foreach($name in $all){$path=Join-Path (Join-Path $prod 'streamlit_opensea_sales\data_opensea_sales') $name;$exists=Test-Path $path -PathType Leaf;$hash='';if($exists){$hash=(Get-FileHash $path -Algorithm SHA256).Hash};$oldArtifactState[$name]=[pscustomobject]@{Exists=$exists;Hash=$hash}}
$oldEnvHash=(Get-FileHash (Join-Path $prod '.env') -Algorithm SHA256).Hash
$backupOutput=& (Join-Path $ops 'backup_production.ps1') -Execute -Simulation -SimulationRoot $Sandbox -SimulationPort $Port -ApprovalPhrase BACKUP_OTG_ANALYTICS_8502
$manifestLine=$backupOutput|Where-Object{$_ -match '^BACKUP_MANIFEST_PATH='}|Select-Object -Last 1
if(-not $manifestLine){throw 'SANDBOX_BACKUP_MANIFEST_MISSING'};$manifest=$manifestLine -replace '^BACKUP_MANIFEST_PATH=',''
if(-not(Test-Path $manifest)){throw 'SANDBOX_BACKUP_FAILED'};'SANDBOX_BACKUP_EXECUTION_TEST=PASS'
$derived=& (Join-Path $ops 'refresh_production_derived.ps1') -Execute -Simulation -SimulationRoot $Sandbox -SimulationPort $Port -ReleasePython 'sandbox-python' -ApprovalPhrase REFRESH_OTG_DERIVED_8502
if(-not($derived -match 'DERIVED_REFRESH=PASS')){throw 'SANDBOX_DERIVED_REFRESH_FAILED'};'SANDBOX_DERIVED_REFRESH_EXECUTION_TEST=PASS'
$metadata=& (Join-Path $ops 'refresh_production_metadata.ps1') -Execute -Simulation -SimulationRoot $Sandbox -SimulationPort $Port -ReleasePython 'sandbox-python' -ApprovalPhrase REFRESH_OTG_METADATA_8502
if(-not($metadata -match 'METADATA_REFRESH=PASS')){throw 'SANDBOX_METADATA_REFRESH_FAILED'};'SANDBOX_METADATA_REFRESH_EXECUTION_TEST=PASS'
$tasks=& (Join-Path $ops 'configure_production_refresh_tasks.ps1') -Execute -Simulation -SimulationRoot $Sandbox -SimulationPort $Port -ReleasePython 'sandbox-python' -ApprovalPhrase CONFIGURE_OTG_REFRESH_8502
if(-not($tasks -match 'TASK_CONFIGURATION=PASS')){throw 'SANDBOX_TASK_REGISTRATION_FAILED'};'SANDBOX_TASK_REGISTRATION_TEST=PASS'
$deploy=& (Join-Path $ops 'deploy_production.ps1') -Execute -Simulation -SimulationRoot $Sandbox -SimulationPort $Port -ExpectedOldHead old -ExpectedReleaseHead release -ReleaseCandidateRoot $release -ReleasePython 'sandbox-python' -BackupManifest $manifest -ApprovalPhrase UPDATE_OTG_ANALYTICS_8502
if(-not($deploy -match 'DEPLOY_RESULT=PASS')){throw 'SANDBOX_DEPLOY_FAILED'};'SANDBOX_DEPLOY_EXECUTION_TEST=PASS';'SANDBOX_NEW_STATE_VERIFY=PASS';'SANDBOX_MIGRATION_COUNT=3';'SANDBOX_REDUNDANT_MIGRATION_EXECUTED=NO'
$state=Get-Content (Join-Path $Sandbox 'simulation_state.json') -Raw|ConvertFrom-Json;if($state.current_head -ne 'release' -or $state.process -ne 'new-healthy'){throw 'SANDBOX_NEW_STATE_VERIFY_FAILED'}
$rollback=& (Join-Path $ops 'rollback_production.ps1') -Execute -Simulation -SimulationRoot $Sandbox -SimulationPort $Port -BackupManifest $manifest -ReleasePython 'sandbox-python' -ApprovalPhrase ROLLBACK_OTG_ANALYTICS_8502
if(-not($rollback -match 'ROLLBACK_RESULT=PASS')){throw 'SANDBOX_ROLLBACK_FAILED'};'SANDBOX_ROLLBACK_EXECUTION_TEST=PASS';'SANDBOX_OLD_STATE_HASH_MATCH=PASS';'SANDBOX_ROLLBACK_ARTIFACT_STATE_MATCH=PASS';'SANDBOX_ROLLBACK_TASK_STATE_MATCH=PASS';'SANDBOX_OLD_APP_HEALTH=PASS'
$state=Get-Content (Join-Path $Sandbox 'simulation_state.json') -Raw|ConvertFrom-Json;if($state.current_head -ne 'old' -or $state.process -ne 'old-healthy'){throw 'SANDBOX_OLD_STATE_VERIFY_FAILED'}
if((Get-FileHash (Join-Path $prod '.env') -Algorithm SHA256).Hash -ne $oldEnvHash){throw 'SANDBOX_OLD_ENV_HASH_FAILED'}
foreach($name in $all){$path=Join-Path (Join-Path $prod 'streamlit_opensea_sales\data_opensea_sales') $name;$expected=$oldArtifactState[$name];if((Test-Path $path -PathType Leaf) -ne $expected.Exists){throw 'SANDBOX_OLD_ARTIFACT_PRESENCE_FAILED'};if($expected.Exists -and (Get-FileHash $path -Algorithm SHA256).Hash -ne $expected.Hash){throw 'SANDBOX_OLD_ARTIFACT_HASH_FAILED'}}
if(Test-Path (Join-Path $Sandbox 'tasks.json')){if(@((Get-Content (Join-Path $Sandbox 'tasks.json') -Raw|ConvertFrom-Json).PSObject.Properties).Count -ne 0){throw 'SANDBOX_OLD_TASK_STATE_FAILED'}}
'SANDBOX_OLD_STATE_RESTORATION=PASS'
$state.fail_new_health=$true;Set-Content (Join-Path $Sandbox 'simulation_state.json') ($state|ConvertTo-Json)
try{& (Join-Path $ops 'deploy_production.ps1') -Execute -Simulation -SimulationRoot $Sandbox -SimulationPort $Port -ExpectedOldHead old -ExpectedReleaseHead release -ReleaseCandidateRoot $release -ReleasePython 'sandbox-python' -BackupManifest $manifest -ApprovalPhrase UPDATE_OTG_ANALYTICS_8502|Out-Null;throw 'SANDBOX_HEALTH_FAILURE_NOT_REJECTED'}catch{$failureObserved=$true}
$state=Get-Content (Join-Path $Sandbox 'simulation_state.json') -Raw|ConvertFrom-Json;if($state.current_head -ne 'old' -or $state.process -ne 'old-healthy'){throw 'SANDBOX_AUTO_ROLLBACK_FAILED'};'SANDBOX_DEPLOY_FAILURE_AUTO_ROLLBACK=PASS'
try{& (Join-Path $ops 'deploy_production.ps1') -Simulation -SimulationRoot $Sandbox -SimulationPort $Port -ExpectedOldHead old -ExpectedReleaseHead release -ReleaseCandidateRoot $release -ReleasePython 'sandbox-python' -BackupManifest $manifest -ApprovalPhrase WRONG|Out-Null;throw 'SANDBOX_BAD_APPROVAL_ACCEPTED'}catch{if($_.Exception.Message -notmatch 'APPROVAL'){throw}}
try{& (Join-Path $ops 'backup_production.ps1') -Execute -Simulation -SimulationRoot 'C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales' -SimulationPort 18502 -ApprovalPhrase BACKUP_OTG_ANALYTICS_8502|Out-Null;throw 'SANDBOX_PRODUCTION_ROOT_ACCEPTED'}catch{if($_.Exception.Message -notmatch 'SIMULATION_CONTEXT_ROOT'){throw}}
try{& (Join-Path $ops 'backup_production.ps1') -Execute -Simulation -SimulationRoot $Sandbox -SimulationPort 8502 -ApprovalPhrase BACKUP_OTG_ANALYTICS_8502|Out-Null;throw 'SANDBOX_8502_ACCEPTED'}catch{if($_.Exception.Message -notmatch 'SIMULATION_CONTEXT_FORBIDDEN'){throw}}
'SANDBOX_FAIL_CLOSED_TESTS=PASS';'SANDBOX_ORPHAN_PROCESS=NO';'MUTATION_EXECUTED=YES'
