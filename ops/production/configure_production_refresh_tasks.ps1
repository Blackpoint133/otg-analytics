[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ReleasePython,[switch]$Execute,[string]$ApprovalPhrase,[switch]$Simulation,[string]$SimulationRoot='C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_109',[int]$SimulationPort=18502)
& (Join-Path $PSScriptRoot 'production_update_orchestrator.ps1') -Operation ConfigureTasks -Execute:$Execute -ApprovalPhrase $ApprovalPhrase -ReleasePython $ReleasePython -Simulation:$Simulation -SimulationRoot $SimulationRoot -SimulationPort $SimulationPort
