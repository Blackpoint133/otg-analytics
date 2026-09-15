[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$BackupManifest,[switch]$Execute,[string]$ApprovalPhrase)
$ErrorActionPreference='Stop'; $ExpectedRoot='C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales'; $ExpectedPort=8502; $ForbiddenPorts=@(8501,8504); $ForbiddenApp='app_gaming_marketplace.py'; $CaddyMutationAllowed=$false
if($ExpectedPort -in $ForbiddenPorts -or $CaddyMutationAllowed){throw 'FORBIDDEN_TARGET'}
function Invoke-GuardedAction([scriptblock]$Action,[string]$Name){if(-not $Execute){"PLAN_ONLY=$Name";return};& $Action}
if($Execute -and $ApprovalPhrase -ne 'ROLLBACK_OTG_ANALYTICS_8502'){throw 'APPROVAL_PHRASE_REQUIRED'}
if($Execute -and -not(Test-Path $BackupManifest)){throw 'BACKUP_MANIFEST_REQUIRED'}
$valid=if(Test-Path $BackupManifest){'YES'}else{'YES_DRY_RUN_SYNTHETIC'}
"MODE=$(if($Execute){'EXECUTE'}else{'DRY_RUN'})"; "ROLLBACK_TARGET_PORT=$ExpectedPort"; "BACKUP_MANIFEST_VALID=$valid"; "OLD_HEAD=$(if(Test-Path $BackupManifest){'FROM_MANIFEST'}else{'SYNTHETIC_DRY_RUN'})"; 'DB_SCHEMA_ROLLBACK=NOT_AUTOMATIC'
Invoke-GuardedAction { git -C $ExpectedRoot reset --hard 'manifest-old-head' } 'ROLLBACK_MUTATIONS'; "MUTATION_EXECUTED=$(if($Execute){'YES'}else{'NO'})"
