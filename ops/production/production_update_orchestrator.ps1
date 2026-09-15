[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('Backup','Deploy','Rollback','DerivedRefresh','MetadataRefresh','ConfigureTasks')][string]$Operation,
    [switch]$Execute,[switch]$Simulation,[string]$ApprovalPhrase,
    [string]$SimulationRoot='C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110',[int]$SimulationPort=18502,
    [string]$ExpectedOldHead,[string]$ExpectedReleaseHead,[string]$PreparedReleaseRoot,[string]$PreparedReleaseManifest,[string]$PreparedReleaseManifestSha256,
    [string]$BackupManifest,[string]$BackupRoot='C:\VAMBAM\Projects\OTG\DEV\production_backups',[string]$ReleasePython
)
$ErrorActionPreference='Stop'
$context=$null
try {
    . (Join-Path $PSScriptRoot 'production_update_common.ps1')
    if($Simulation){$context=New-SimulationExecutionContext @{SimulationRoot=$SimulationRoot;SimulationPort=$SimulationPort;ExpectedOldHead=$ExpectedOldHead;ExpectedReleaseHead=$ExpectedReleaseHead;PreparedReleaseRoot=$PreparedReleaseRoot;PreparedReleaseManifest=$PreparedReleaseManifest;PreparedReleaseManifestSha256=$PreparedReleaseManifestSha256;BackupManifest=$BackupManifest;ReleasePython=$ReleasePython}}
    else{$context=New-ProductionExecutionContext @{ExpectedOldHead=$ExpectedOldHead;ExpectedReleaseHead=$ExpectedReleaseHead;PreparedReleaseRoot=$PreparedReleaseRoot;PreparedReleaseManifest=$PreparedReleaseManifest;PreparedReleaseManifestSha256=$PreparedReleaseManifestSha256;BackupManifest=$BackupManifest;BackupRoot=$BackupRoot}}
    $expected=switch($Operation){'Backup'{'BACKUP_OTG_ANALYTICS_8502'}'Deploy'{'UPDATE_OTG_ANALYTICS_8502'}'Rollback'{'ROLLBACK_OTG_ANALYTICS_8502'}'DerivedRefresh'{'REFRESH_OTG_DERIVED_8502'}'MetadataRefresh'{'REFRESH_OTG_METADATA_8502'}'ConfigureTasks'{'CONFIGURE_OTG_REFRESH_8502'}}
    Assert-Approval $Execute $ApprovalPhrase $expected
    switch($Operation){'Backup'{Invoke-BackupCore $context -Execute:$Execute}'Deploy'{Invoke-DeployCore $context -Execute:$Execute}'Rollback'{Invoke-RollbackCore $context -Execute:$Execute}'DerivedRefresh'{Invoke-DerivedRefreshCore $context -Execute:$Execute}'MetadataRefresh'{Invoke-MetadataRefreshCore $context -Execute:$Execute}'ConfigureTasks'{Invoke-TaskConfigurationCore $context -Execute:$Execute}}
}
catch {
    if($context -and $context.MutationStarted){Write-AtomicJson (Join-Path $context.Root 'EXECUTION_TELEMETRY.json') ([ordered]@{mutation_started=$context.MutationStarted;mutation_phases=@($context.MutationPhases);rollback_attempted=$context.RollbackAttempted;rollback_succeeded=$context.RollbackSucceeded;state_restored=$context.StateRestored})}
    if($context -and $context.MutationStarted){Write-KV 'MUTATION_EXECUTED' 'YES'}else{Write-KV 'MUTATION_EXECUTED' 'NO'}
    if($context){Write-KV 'AUTO_ROLLBACK_ATTEMPTED' ($(if($context.RollbackAttempted){'YES'}else{'NO'}));if($context.RollbackAttempted){Write-KV 'AUTO_ROLLBACK_RESULT' ($(if($context.RollbackSucceeded){'PASS'}else{'FAIL'}))};Write-KV 'STATE_RESTORED' ($(if($context.StateRestored){'YES'}else{'NO'}))}
    throw
}
finally {if($context -and $context.MutationStarted){Write-KV 'MUTATION_EXECUTED' 'YES'}else{Write-KV 'MUTATION_EXECUTED' 'NO'}}
