[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('Backup','Deploy','Rollback','DerivedRefresh','MetadataRefresh','ConfigureTasks')][string]$Operation,
    [switch]$Execute,[switch]$Simulation,[string]$ApprovalPhrase,
    [string]$SimulationRoot='C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_109',[int]$SimulationPort=18502,
    [string]$ExpectedOldHead,[string]$ExpectedReleaseHead,[string]$ReleaseRoot,[string]$ReleasePython,
    [string]$BackupManifest,[string]$BackupRoot='C:\VAMBAM\Projects\OTG\DEV\production_backups'
)
$ErrorActionPreference='Stop'
try {
    . (Join-Path $PSScriptRoot 'production_update_common.ps1')
    if($Simulation){
        $context=New-SimulationExecutionContext @{SimulationRoot=$SimulationRoot;SimulationPort=$SimulationPort;ExpectedOldHead=$ExpectedOldHead;ExpectedReleaseHead=$ExpectedReleaseHead;ReleaseRoot=$ReleaseRoot;ReleasePython=$ReleasePython;PreparedReleaseManifest=$BackupManifest}
    } else {
        $context=New-ProductionExecutionContext @{ExpectedOldHead=$ExpectedOldHead;ExpectedReleaseHead=$ExpectedReleaseHead;ReleaseRoot=$ReleaseRoot;ReleasePython=$ReleasePython;PreparedReleaseManifest=$BackupManifest;BackupRoot=$BackupRoot}
    }
    $expected=switch($Operation){
        'Backup'{'BACKUP_OTG_ANALYTICS_8502'} 'Deploy'{'UPDATE_OTG_ANALYTICS_8502'}
        'Rollback'{'ROLLBACK_OTG_ANALYTICS_8502'} 'DerivedRefresh'{'REFRESH_OTG_DERIVED_8502'}
        'MetadataRefresh'{'REFRESH_OTG_METADATA_8502'} 'ConfigureTasks'{'CONFIGURE_OTG_REFRESH_8502'}
    }
    Assert-Approval $Execute $ApprovalPhrase $expected
    switch($Operation){
        'Backup'{Invoke-BackupCore $context -Execute:$Execute}
        'Deploy'{Invoke-DeployCore $context -Execute:$Execute}
        'Rollback'{Invoke-RollbackCore $context -Execute:$Execute}
        'DerivedRefresh'{Invoke-DerivedRefreshCore $context -Execute:$Execute}
        'MetadataRefresh'{Invoke-MetadataRefreshCore $context -Execute:$Execute}
        'ConfigureTasks'{Invoke-TaskConfigurationCore $context -Execute:$Execute}
    }
    $mutation='NO'
    if($Execute){$mutation='YES'}
    Write-KV 'MUTATION_EXECUTED' $mutation
} catch {
    Write-Error $_.Exception.Message
    Write-KV 'MUTATION_EXECUTED' 'NO'
    throw
}
