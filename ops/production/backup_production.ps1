[CmdletBinding()]
param([switch]$Execute,[string]$ApprovalPhrase,[string]$BackupRoot='C:\VAMBAM\Projects\OTG\DEV\production_backups',[switch]$Simulation,[string]$SimulationRoot='C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_109',[int]$SimulationPort=18502)
& (Join-Path $PSScriptRoot 'production_update_orchestrator.ps1') -Operation Backup -Execute:$Execute -ApprovalPhrase $ApprovalPhrase -BackupRoot $BackupRoot -Simulation:$Simulation -SimulationRoot $SimulationRoot -SimulationPort $SimulationPort
