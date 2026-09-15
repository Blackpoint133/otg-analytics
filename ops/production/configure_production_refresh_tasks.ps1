[CmdletBinding()]
param([string]$ReleasePython,[switch]$Execute,[string]$ApprovalPhrase,[switch]$Simulation,[string]$SimulationRoot='C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110',[int]$SimulationPort=18502)
& (Join-Path $PSScriptRoot 'production_update_orchestrator.ps1') -Operation ConfigureTasks -Execute:$Execute -ApprovalPhrase $ApprovalPhrase -ReleasePython $ReleasePython -Simulation:$Simulation -SimulationRoot $SimulationRoot -SimulationPort $SimulationPort
