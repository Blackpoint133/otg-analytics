[CmdletBinding()]
param([switch]$Execute,[string]$ApprovalPhrase,[string]$BackupRoot='C:\VAMBAM\Projects\OTG\DEV\production_backups')
$ErrorActionPreference='Stop'
$ExpectedRoot='C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales'; $ExpectedPort=8502; $ExpectedApp='app_opensea_sales.py'; $ForbiddenPorts=@(8501,8504); $ForbiddenApp='app_gaming_marketplace.py'; $CaddyMutationAllowed=$false
function Assert-Target { if($ExpectedRoot -ne 'C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales' -or $ExpectedPort -ne 8502){throw 'TARGET_GUARD_FAILED'}; if($ExpectedPort -in $ForbiddenPorts -or $ExpectedApp -eq $ForbiddenApp -or $CaddyMutationAllowed){throw 'FORBIDDEN_TARGET'} }
function Invoke-GuardedAction([scriptblock]$Action,[string]$Name){ if(-not $Execute){ "PLAN_ONLY=$Name"; return }; & $Action }
Assert-Target
if($Execute -and $ApprovalPhrase -ne 'BACKUP_OTG_ANALYTICS_8502'){throw 'APPROVAL_PHRASE_REQUIRED'}
$gitHead=(git -c "safe.directory=$ExpectedRoot" -C $ExpectedRoot rev-parse HEAD); $gitStatus=(git -c "safe.directory=$ExpectedRoot" -C $ExpectedRoot status --porcelain)
$pg=Get-Command pg_dump -ErrorAction SilentlyContinue; if(-not $pg -and (Test-Path 'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe')){$pg=Get-Item 'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe'}
"MODE=$(if($Execute){'EXECUTE'}else{'DRY_RUN'})"; "TARGET_ROOT=$ExpectedRoot"; "TARGET_PORT=$ExpectedPort"; "GIT_HEAD=$gitHead"; "GIT_CLEAN=$(if([string]::IsNullOrEmpty($gitStatus)){'YES'}else{'NO'})"; "DB_BACKUP_TOOL=$(if($pg){$pg.Source}else{'MISSING'})"; "BACKUP_SET_VALID=$(if($pg){'YES'}else{'NO'})"
if(-not $pg){throw 'PG_DUMP_REQUIRED'}
Invoke-GuardedAction { $stamp=Get-Date -Format yyyyMMdd_HHmmss; $out=Join-Path $BackupRoot $stamp; New-Item -ItemType Directory -Path $out -Force | Out-Null; git -C $ExpectedRoot bundle create (Join-Path $out 'production.bundle') HEAD; Copy-Item (Join-Path $ExpectedRoot '.env') (Join-Path $out '.env'); & $pg.Source '--format=custom' '--file' (Join-Path $out 'production.dump') $env:POSTGRES_DB } 'CREATE_BACKUP'
"MUTATION_EXECUTED=$(if($Execute){'YES'}else{'NO'})"
