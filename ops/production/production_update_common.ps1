Set-StrictMode -Version Latest
$script:ExpectedRoot = 'C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales'
$script:ExpectedPort = 8502
$script:ExpectedApp = 'app_opensea_sales.py'
$script:ForbiddenPorts = @(8501,8504)
$script:ForbiddenApp = 'app_gaming_marketplace.py'
$script:CaddyMutationAllowed = $false
function Assert-ProductionTarget([string]$Root=$script:ExpectedRoot,[int]$Port=$script:ExpectedPort,[string]$App=$script:ExpectedApp) {
    if($Root -ne $script:ExpectedRoot -or $Port -ne $script:ExpectedPort -or $App -ne $script:ExpectedApp){throw 'PRODUCTION_TARGET_GUARD_FAILED'}
    if($Port -in $script:ForbiddenPorts -or $App -eq $script:ForbiddenApp -or $script:CaddyMutationAllowed){throw 'FORBIDDEN_TARGET_GUARD_FAILED'}
}
function Get-SafeEnv([string]$Path) { $v=@{}; if(Test-Path -LiteralPath $Path){foreach($line in Get-Content -LiteralPath $Path){if($line -match '^\s*([^#=][^=]*)=(.*)$'){$v[$Matches[1].Trim()]=$Matches[2].Trim().Trim('"').Trim("'")}}}; return $v }
function Get-PostgresTools { $names=@('pg_dump','pg_restore','psql'); $out=@{}; foreach($n in $names){$c=Get-Command $n -ErrorAction SilentlyContinue; if(-not $c){foreach($p in @("C:\Program Files\PostgreSQL\18\bin\$n.exe","C:\Program Files\PostgreSQL\17\bin\$n.exe")){if(Test-Path $p){$c=Get-Item $p;break}}}; if($c){$path=if($c.PSObject.Properties.Name -contains 'Source'){$c.Source}else{$c.FullName}; $out[$n]=$path}}; return $out }
function Get-8502Process { $c=Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $script:ExpectedPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; if(-not $c){return $null}; $p=Get-CimInstance Win32_Process -Filter "ProcessId=$($c.OwningProcess)"; if(-not $p -or $p.CommandLine -notmatch 'app_opensea_sales\.py' -or $p.CommandLine -match 'app_gaming_marketplace\.py'){throw '8502_PROCESS_IDENTITY_FAILED'}; return $p }
function Get-Sha256([string]$Path){return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
function Invoke-GuardedAction([scriptblock]$Action,[string]$Name,[switch]$Execute){if(-not $Execute){"PLAN_ONLY=$Name";return}; & $Action}
function Assert-Approval([switch]$Execute,[string]$Actual,[string]$Expected){if($Execute -and $Actual -ne $Expected){throw 'APPROVAL_PHRASE_REQUIRED'}}
function Assert-Simulation([string]$Root,[int]$Port){$prefix='C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_107'; if(-not $Root.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase) -or $Root -eq $script:ExpectedRoot -or $Port -in @($script:ExpectedPort,8501,8504)){throw 'SIMULATION_CONTEXT_GUARD_FAILED'}}
function Assert-AllowedMigrationSet([string[]]$Migrations){$expected=@('sql/add_site_visit_trader_mode.sql','sql/create_site_product_events.sql','sql/create_user_feedback.sql'); if((Compare-Object $expected $Migrations).Count){throw 'MIGRATION_ALLOWLIST_FAILED'}}
function Get-TaskClassification([object]$Task){$s=(($Task.TaskName,$Task.TaskPath,$Task.Actions.Execute,$Task.Actions.Arguments,$Task.Actions.WorkingDirectory)-join ' '); if($s -match '_Staging|\\staging\\'){return 'OTG_STAGING'}; if($s -match 'production|data_streamlit\\opensea_sales'){return 'OTG_PRODUCTION_DERIVED'}; return 'OTHER'}
