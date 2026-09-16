[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ExpectedMainHead,
    [Parameter(Mandatory=$true)][string]$PreparedReleaseHead,
    [Parameter(Mandatory=$true)][string]$PreparedReleaseManifest,
    [Parameter(Mandatory=$true)][string]$PreparedReleaseManifestSha256,
    [switch]$Execute,
    [string]$ApprovalPhrase,
    [switch]$Simulation,
    [string]$SimulationRoot='C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110'
)
$ErrorActionPreference='Stop'
$mutated=$false
. (Join-Path $PSScriptRoot 'production_update_common.ps1')
function Hash([string]$Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
function KV([string]$Name,[object]$Value){Write-Output ($Name+'='+[string]$Value)}
try {
    if($Execute -and $ApprovalPhrase -ne 'PROMOTE_OTG_ANALYTICS_MAIN'){throw 'APPROVAL_PHRASE_REQUIRED'}
    if($Simulation){
        $root=[IO.Path]::GetFullPath($SimulationRoot);$prefix='C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110';if(-not $root.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'SIMULATION_CONTEXT_ROOT_GUARD_FAILED'}
        $remote=Join-Path $root 'promotion_remote.json';$state=Get-Content $remote -Raw|ConvertFrom-Json
        $manifest=Get-Content $PreparedReleaseManifest -Raw|ConvertFrom-Json;if((Hash $PreparedReleaseManifest) -ne $PreparedReleaseManifestSha256.ToLowerInvariant()){throw 'PREPARED_RELEASE_MANIFEST_HASH_MISMATCH'};if($manifest.prepared_release_head -ne $PreparedReleaseHead){throw 'PREPARED_RELEASE_HEAD_MISMATCH'};Assert-PreparedReleaseThemeContract $manifest;if($state.main_head -ne $ExpectedMainHead){throw 'EXPECTED_MAIN_HEAD_MISMATCH'}
        if(-not$Execute){KV 'MODE' 'DRY_RUN';KV 'PROMOTION_PLAN' 'PASS';KV 'EXACT_PUSH_REF' ($PreparedReleaseHead+':refs/heads/main');KV 'DEVELOP_BRANCH_PROMOTION_FORBIDDEN' 'YES';KV 'MUTATION_EXECUTED' 'NO';exit 0}
        $mutated=$true;$state.main_head=$PreparedReleaseHead;Set-Content $remote ($state|ConvertTo-Json -Depth 10);$simStatePath=Join-Path $root 'simulation_state.json';if(Test-Path $simStatePath){$simState=Get-Content $simStatePath -Raw|ConvertFrom-Json;$simState.main_head=$PreparedReleaseHead;Set-Content $simStatePath ($simState|ConvertTo-Json -Depth 20)};Add-Content (Join-Path $root 'promotion.push.log') ($PreparedReleaseHead+':refs/heads/main');$state=Get-Content $remote -Raw|ConvertFrom-Json;if($state.main_head -ne $PreparedReleaseHead){throw 'PROMOTION_VERIFY_FAILED'};KV 'PROMOTION_RESULT' 'PASS';KV 'EXACT_PREPARED_HEAD_PROMOTION_CONTRACT' 'PASS';KV 'DEVELOP_BRANCH_PROMOTION_FORBIDDEN' 'YES';exit 0
    }
    $repo=Resolve-Path (Join-Path $PSScriptRoot '..\..')
    & git -C $repo fetch origin main;if($LASTEXITCODE -ne 0){throw 'GIT_FETCH_FAILED'}
    $main=(& git -C $repo rev-parse origin/main).Trim();if($main -ne $ExpectedMainHead){throw 'EXPECTED_MAIN_HEAD_MISMATCH'};& git -C $repo cat-file -e ($PreparedReleaseHead+'^{commit}');if($LASTEXITCODE -ne 0){throw 'PREPARED_RELEASE_HEAD_MISSING'}
    if((Hash $PreparedReleaseManifest) -ne $PreparedReleaseManifestSha256.ToLowerInvariant()){throw 'PREPARED_RELEASE_MANIFEST_HASH_MISMATCH'};$manifest=Get-Content $PreparedReleaseManifest -Raw|ConvertFrom-Json;if($manifest.prepared_release_head -ne $PreparedReleaseHead){throw 'PREPARED_RELEASE_HEAD_MISMATCH'};Assert-PreparedReleaseThemeContract $manifest;& git -C $repo merge-base --is-ancestor $ExpectedMainHead $PreparedReleaseHead;if($LASTEXITCODE -ne 0){throw 'PROMOTION_NOT_FAST_FORWARD'}
    if(-not$Execute){KV 'MODE' 'DRY_RUN';KV 'PROMOTION_PLAN' 'PASS';KV 'EXACT_PUSH_REF' ($PreparedReleaseHead+':refs/heads/main');KV 'DEVELOP_BRANCH_PROMOTION_FORBIDDEN' 'YES';KV 'MUTATION_EXECUTED' 'NO';exit 0}
    $mutated=$true;& git -C $repo push origin ($PreparedReleaseHead+':refs/heads/main');if($LASTEXITCODE -ne 0){throw 'PROMOTION_PUSH_FAILED'};& git -C $repo fetch origin main;$main=(& git -C $repo rev-parse origin/main).Trim();if($main -ne $PreparedReleaseHead){throw 'PROMOTION_VERIFY_FAILED'};KV 'PROMOTION_RESULT' 'PASS';KV 'EXACT_PREPARED_HEAD_PROMOTION_CONTRACT' 'PASS';KV 'DEVELOP_BRANCH_PROMOTION_FORBIDDEN' 'YES'
}
catch {KV 'MUTATION_EXECUTED' ($(if($mutated){'YES'}else{'NO'}));throw}
finally {if(-not$mutated){KV 'MUTATION_EXECUTED' 'NO'}}
