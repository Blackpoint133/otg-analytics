[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$BackupManifest,[switch]$Execute,[string]$ApprovalPhrase,[switch]$Simulation,[string]$SimulationRoot='C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110',[int]$SimulationPort=18502,[string]$ReleasePython)
& (Join-Path $PSScriptRoot 'production_update_orchestrator.ps1') -Operation Rollback -Execute:$Execute -ApprovalPhrase $ApprovalPhrase -BackupManifest $BackupManifest -ReleasePython $ReleasePython -Simulation:$Simulation -SimulationRoot $SimulationRoot -SimulationPort $SimulationPort
