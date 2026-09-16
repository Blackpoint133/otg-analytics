Set-StrictMode -Version Latest

$script:ExpectedRoot = 'C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales'
$script:ExpectedApp = Join-Path $script:ExpectedRoot 'streamlit_opensea_sales\app_opensea_sales.py'
$script:ExpectedPort = 8502
$script:ExpectedRuntimeRoot = 'C:\VAMBAM\Projects\OTG\runtime\opensea_sales'
$script:SimulationPrefix = 'C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110'
$script:ForbiddenPorts = @(8501,8504)
$script:ForbiddenApp = 'app_gaming_marketplace.py'
$script:ManagedTasks = @('OTG_Derived_Data_Refresh_Production','OTG_Metadata_Refresh_Production')
$script:AllowedMigrations = @('sql/add_site_visit_trader_mode.sql','sql/create_site_product_events.sql','sql/create_user_feedback.sql')

function Write-KV([string]$Name,[object]$Value) { Write-Output ($Name + '=' + [string]$Value) }
function Get-Sha256([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant() }
function Write-AtomicText([string]$Path,[string]$Text) {
    $parent=Split-Path -Parent $Path
    if(-not(Test-Path -LiteralPath $parent)){New-Item -ItemType Directory -Path $parent -Force|Out-Null}
    $tmp=$Path+'.tmp.'+[guid]::NewGuid().ToString('N')
    [IO.File]::WriteAllText($tmp,$Text,(New-Object Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}
function Write-AtomicJson([string]$Path,[object]$Value) { Write-AtomicText $Path ($Value|ConvertTo-Json -Depth 60) }
function Add-Mutation([object]$Context,[string]$Phase) { $Context.MutationStarted=$true; if($Phase){[void]$Context.MutationPhases.Add($Phase)} }
function Set-Phase([object]$Context,[string]$Phase) { [void]$Context.MutationPhases.Add($Phase); if($Context.Mode -eq 'SIMULATION'){Add-Content -LiteralPath (Join-Path $Context.Root 'phase.log') -Value $Phase}; Write-KV 'PHASE' $Phase }

function Assert-ProductionTarget {
    param([string]$Root=$script:ExpectedRoot,[int]$Port=$script:ExpectedPort,[string]$App=$script:ExpectedApp)
    if($Root -ne $script:ExpectedRoot -or $Port -ne $script:ExpectedPort -or $App -ne $script:ExpectedApp){throw 'PRODUCTION_TARGET_GUARD_FAILED'}
    if($Port -in $script:ForbiddenPorts -or $App -match [regex]::Escape($script:ForbiddenApp)){throw 'FORBIDDEN_TARGET_GUARD_FAILED'}
}
function Assert-SimulationTarget {
    param([string]$Root,[int]$Port,[string]$App)
    $full=[IO.Path]::GetFullPath($Root);$prefix=([IO.Path]::GetFullPath($script:SimulationPrefix)).TrimEnd('\')+'\'
    if($full -ne $prefix.TrimEnd('\') -and -not $full.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'SIMULATION_CONTEXT_ROOT_GUARD_FAILED'}
    if($full -match '(?i)gaming_marketplace|\\staging(?:\\|$)' -or $full -eq $script:ExpectedRoot){throw 'SIMULATION_CONTEXT_PRODUCTION_PATH_GUARD_FAILED'}
    if($Port -in @($script:ExpectedPort,8501,8504) -or $Port -lt 1024 -or $Port -gt 65535){throw 'SIMULATION_CONTEXT_FORBIDDEN_PORT_GUARD_FAILED'}
    if($App -match '(?i)app_gaming_marketplace|caddy'){throw 'SIMULATION_CONTEXT_APP_GUARD_FAILED'}
}
function Assert-Context([object]$Context) {
    if($Context.Mode -eq 'PRODUCTION'){Assert-ProductionTarget $Context.Root $Context.Port $Context.AppPath}
    elseif($Context.Mode -eq 'SIMULATION'){Assert-SimulationTarget $Context.Root $Context.Port $Context.AppPath}
    else{throw 'UNKNOWN_EXECUTION_CONTEXT'}
    if($Context.Port -in $script:ForbiddenPorts -or $Context.AppPath -match [regex]::Escape($script:ForbiddenApp)){throw 'FORBIDDEN_TARGET_GUARD_FAILED'}
}
function Assert-Approval([switch]$Execute,[string]$Actual,[string]$Expected){if($Execute -and $Actual -ne $Expected){throw 'APPROVAL_PHRASE_REQUIRED'}}

function Get-SafeEnv([string]$Path) {
    $out=@{}
    if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){return $out}
    foreach($line in Get-Content -LiteralPath $Path){
        if($line -match '^\s*export\s+'){$line=$line -replace '^\s*export\s+',''}
        if($line -match '^\s*([^#=][^=]*)=(.*)$'){$key=$Matches[1].Trim();$value=$Matches[2].Trim();if(($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))){$value=$value.Substring(1,$value.Length-2)};$out[$key]=$value}
    }
    $out
}
function Get-DatabaseEnvironment([string]$EnvPath,[switch]$Required) {
    $raw=Get-SafeEnv $EnvPath;$map=@{PGHOST='POSTGRES_HOST';PGPORT='POSTGRES_PORT';PGUSER='POSTGRES_USER';PGPASSWORD='POSTGRES_PASSWORD';PGDATABASE='POSTGRES_DB'};$out=@{}
    foreach($key in $map.Keys){$source=$map[$key];if($raw.ContainsKey($source) -and [string]$raw[$source] -ne ''){$out[$key]=[string]$raw[$source]}elseif($Required){throw ('REQUIRED_DB_ENV_MISSING:'+ $source)}}
    $out
}
function Select-PostgresToolSet {
    param([string[]]$Directories)
    $toolNames=@('pg_dump','pg_restore','psql')
    $candidateDirectories=@{}
    foreach($directory in $Directories){if(-not[string]::IsNullOrWhiteSpace($directory)){$candidateDirectories[[IO.Path]::GetFullPath($directory).TrimEnd('\')]= $true}}
    $valid=@()
    foreach($directory in $candidateDirectories.Keys){
        $paths=@{};$complete=$true
        foreach($name in $toolNames){$path=Join-Path $directory ($name+'.exe');if(-not(Test-Path -LiteralPath $path -PathType Leaf)){$complete=$false;break};$paths[$name]=$path}
        if($complete){$versionText=Split-Path -Leaf (Split-Path -Parent $directory);$version=[version]::new(0,0);try{$version=[version]($versionText+'.0')}catch{};$valid+=,[pscustomobject]@{Directory=$directory;Version=$version;Paths=$paths}}
    }
    $selected=$valid|Sort-Object -Property @{Expression='Version';Descending=$true},@{Expression='Directory';Descending=$false}|Select-Object -First 1
    $out=@{}
    if($selected){foreach($name in $toolNames){$out[$name]=$selected.Paths[$name]}}
    $out
}
function Get-PostgresTools {
    $toolNames=@('pg_dump','pg_restore','psql')
    $candidateDirectories=@{}
    foreach($name in $toolNames){
        $command=Get-Command ($name+'.exe') -ErrorAction SilentlyContinue
        if(-not$command){$command=Get-Command $name -ErrorAction SilentlyContinue}
        if($command){$source=if($command.Source){$command.Source}else{$command.FullName};if($source){$candidateDirectories[(Split-Path -Parent $source)]=$true}}
    }
    foreach($base in @('C:\Program Files\PostgreSQL','C:\Program Files (x86)\PostgreSQL')){
        if(Test-Path -LiteralPath $base -PathType Container){foreach($version in Get-ChildItem -LiteralPath $base -Directory -ErrorAction SilentlyContinue){$candidateDirectories[(Join-Path $version.FullName 'bin')]=$true}}
    }
    foreach($registryPath in @('HKLM:\SOFTWARE\PostgreSQL\Installations','HKLM:\SOFTWARE\WOW6432Node\PostgreSQL\Installations')){
        foreach($install in Get-ChildItem -Path $registryPath -ErrorAction SilentlyContinue){$baseProperty=Get-ItemProperty -LiteralPath $install.PSPath -Name 'Base Directory' -ErrorAction SilentlyContinue;if($baseProperty.'Base Directory'){$candidateDirectories[(Join-Path ([string]$baseProperty.'Base Directory') 'bin')]=$true}}
    }
    Select-PostgresToolSet @($candidateDirectories.Keys)
}

function Get-FinalRuntimeRoot([string]$ReleaseHead,[object]$Context) { if(-not$ReleaseHead){throw 'RELEASE_HEAD_REQUIRED'};if($Context.Mode -eq 'PRODUCTION'){Join-Path $script:ExpectedRuntimeRoot ('releases\'+$ReleaseHead)}else{Join-Path $Context.RuntimeRoot ('releases\'+$ReleaseHead)} }
function Get-FinalRuntimePython([string]$ReleaseHead,[object]$Context) { Join-Path (Get-FinalRuntimeRoot $ReleaseHead $Context) '.venv\Scripts\python.exe' }
function Assert-FinalRuntimePath([string]$Python,[string]$ReleaseHead,[object]$Context) { if([IO.Path]::GetFullPath($Python) -ne [IO.Path]::GetFullPath((Get-FinalRuntimePython $ReleaseHead $Context))){throw 'FINAL_RUNTIME_PATH_GUARD_FAILED'} }

function New-ProductionExecutionContext {
    param([hashtable]$Arguments)
    Assert-ProductionTarget
    $head=[string]$Arguments.ExpectedReleaseHead;$python='';if($head){$python=Get-FinalRuntimePython $head ([pscustomobject]@{Mode='PRODUCTION'})}
    [pscustomobject]@{Mode='PRODUCTION';Root=$script:ExpectedRoot;RuntimeRoot=$script:ExpectedRuntimeRoot;AppPath=$script:ExpectedApp;Port=8502;EnvPath=(Join-Path $script:ExpectedRoot '.env');DataRoot=(Join-Path $script:ExpectedRoot 'streamlit_opensea_sales\data_opensea_sales');RepoRoot=$script:ExpectedRoot;PreparedReleaseRoot=$Arguments.PreparedReleaseRoot;ReleaseRoot=$Arguments.PreparedReleaseRoot;ReleasePython=$python;DeploymentRefreshPython='';BackupRoot=$Arguments.BackupRoot;PreparedReleaseManifest=$Arguments.PreparedReleaseManifest;PreparedReleaseManifestSha256=$Arguments.PreparedReleaseManifestSha256;BackupManifest=$Arguments.BackupManifest;ExpectedOldHead=$Arguments.ExpectedOldHead;ExpectedReleaseHead=$head;SimulationStatePath='';MutationStarted=$false;MutationPhases=(New-Object Collections.ArrayList);RollbackAttempted=$false;RollbackSucceeded=$false;StateRestored=$false}
}
function New-SimulationExecutionContext {
    param([hashtable]$Arguments)
    $root=[IO.Path]::GetFullPath($Arguments.SimulationRoot);$app=Join-Path $root 'production\streamlit_opensea_sales\app_opensea_sales.py';Assert-SimulationTarget $root ([int]$Arguments.SimulationPort) $app
    $old=if($Arguments.ExpectedOldHead){$Arguments.ExpectedOldHead}else{'old'};$release=if($Arguments.ExpectedReleaseHead){$Arguments.ExpectedReleaseHead}else{'release'};$python=if($Arguments.ReleasePython){$Arguments.ReleasePython}else{Get-FinalRuntimePython $release ([pscustomobject]@{Mode='SIMULATION';RuntimeRoot=(Join-Path $root 'runtime')})}
    [pscustomobject]@{Mode='SIMULATION';Root=$root;RuntimeRoot=(Join-Path $root 'runtime');AppPath=$app;Port=([int]$Arguments.SimulationPort);EnvPath=(Join-Path $root 'production\.env');DataRoot=(Join-Path $root 'production\streamlit_opensea_sales\data_opensea_sales');RepoRoot=(Join-Path $root 'production');PreparedReleaseRoot=(Join-Path $root 'release');ReleaseRoot=(Join-Path $root 'release');ReleasePython=$python;DeploymentRefreshPython='';BackupRoot=(Join-Path $root 'backups');PreparedReleaseManifest=$Arguments.PreparedReleaseManifest;PreparedReleaseManifestSha256=$Arguments.PreparedReleaseManifestSha256;BackupManifest=$Arguments.BackupManifest;ExpectedOldHead=$old;ExpectedReleaseHead=$release;SimulationStatePath=(Join-Path $root 'simulation_state.json');MutationStarted=$false;MutationPhases=(New-Object Collections.ArrayList);RollbackAttempted=$false;RollbackSucceeded=$false;StateRestored=$false}
}

function Invoke-ChildProcess {
    param([string]$FilePath,[string[]]$Arguments,[string]$WorkingDirectory,[int]$TimeoutSeconds=900,[hashtable]$Environment=@{},[string]$LogPath)
    $psi=New-Object Diagnostics.ProcessStartInfo;$psi.FileName=$FilePath;$psi.WorkingDirectory=$WorkingDirectory;$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true;$psi.Arguments=(($Arguments|ForEach-Object{if($_ -match '[\s"]'){'"'+$_+'"'}else{$_}})-join ' ');foreach($key in $Environment.Keys){$psi.EnvironmentVariables[$key]=[string]$Environment[$key]};$process=New-Object Diagnostics.Process;$process.StartInfo=$psi;if(-not$process.Start()){throw ('CHILD_START_FAILED:'+ $FilePath)};$stdout=$process.StandardOutput.ReadToEndAsync();$stderr=$process.StandardError.ReadToEndAsync();if(-not$process.WaitForExit($TimeoutSeconds*1000)){try{$process.Kill()}catch{};throw ('CHILD_TIMEOUT:'+ $FilePath)};$process.WaitForExit();$out=$stdout.Result;$err=$stderr.Result;if($LogPath){Write-AtomicText $LogPath ($out+[Environment]::NewLine+$err)};if($process.ExitCode -ne 0){throw ('CHILD_COMMAND_FAILED:'+ $FilePath+':'+$process.ExitCode)};[pscustomobject]@{ExitCode=$process.ExitCode;StdOut=$out;StdErr=$err}
}
function Read-SharedText {
    param([Parameter(Mandatory=$true)][string]$Path)
    if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){throw ('PROCESS_LOG_MISSING:'+ $Path)}
    $stream=$null;$reader=$null
    try {
        $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
        $reader=New-Object IO.StreamReader($stream)
        return $reader.ReadToEnd()
    } catch {
        throw ('PROCESS_LOG_READ_FAILED:'+ $Path)
    } finally {
        if($reader){$reader.Dispose()}
        elseif($stream){$stream.Dispose()}
    }
}
function Start-RedirectedProcess {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [Parameter(Mandatory=$true)][string[]]$ArgumentList,
        [Parameter(Mandatory=$true)][string]$WorkingDirectory,
        [Parameter(Mandatory=$true)][string]$StdOutLogPath,
        [Parameter(Mandatory=$true)][string]$StdErrLogPath
    )
    $stdoutParent=Split-Path -Parent $StdOutLogPath;$stderrParent=Split-Path -Parent $StdErrLogPath
    if(-not(Test-Path -LiteralPath $stdoutParent -PathType Container)){New-Item -ItemType Directory -Path $stdoutParent -Force|Out-Null}
    if(-not(Test-Path -LiteralPath $stderrParent -PathType Container)){New-Item -ItemType Directory -Path $stderrParent -Force|Out-Null}
    $process=Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -WorkingDirectory $WorkingDirectory -RedirectStandardOutput $StdOutLogPath -RedirectStandardError $StdErrLogPath -PassThru -WindowStyle Hidden
    [pscustomobject]@{Process=$process;Id=$process.Id;Pid=$process.Id;StdOutLogPath=$StdOutLogPath;StdErrLogPath=$StdErrLogPath;StartedAt=(Get-Date).ToUniversalTime().ToString('o')}
}
function Assert-CurrentLaunchLogs {
    param([Parameter(Mandatory=$true)][object]$Launch)
    foreach($path in @($Launch.StdOutLogPath,$Launch.StdErrLogPath)){
        $content=Read-SharedText $path
        if($content -match 'Traceback|ModuleNotFoundError|ImportError|Uncaught app exception'){throw 'CURRENT_LAUNCH_LOG_FAILED'}
    }
    Write-KV 'CURRENT_LAUNCH_LOG_GATE' 'PASS'
}
function Invoke-GitBundleBackup {
    param([object]$Context,[string]$BackupDirectory)
    $gitCommand=Get-Command git.exe -ErrorAction SilentlyContinue
    if(-not$gitCommand){$gitCommand=Get-Command git -ErrorAction SilentlyContinue}
    if(-not$gitCommand){throw 'GIT_MISSING'}
    $gitPath=if($gitCommand.Source){$gitCommand.Source}else{$gitCommand.FullName}
    $bundlePath=Join-Path $BackupDirectory 'production.bundle'
    $gitRoot=if($Context.Mode -eq 'SIMULATION'){$Context.RepoRoot}else{$Context.Root}
    $gitPrefix=@('-c',('safe.directory='+$gitRoot),'-C',$gitRoot)
    $createArgs=@($gitPrefix+'bundle','create',$bundlePath,'HEAD')
    $createResult=Invoke-ChildProcess $gitPath $createArgs $gitRoot 300 @{} (Join-Path $BackupDirectory 'git_bundle_create.log')
    if(-not(Test-Path $bundlePath -PathType Leaf) -or (Get-Item $bundlePath).Length -le 0){throw 'GIT_BUNDLE_CREATE_FAILED'}
    $verifyArgs=@($gitPrefix+'bundle','verify',$bundlePath)
    $verifyResult=Invoke-ChildProcess $gitPath $verifyArgs $gitRoot 300 @{} (Join-Path $BackupDirectory 'git_bundle_verify.log')
    [pscustomobject]@{Create=$createResult;Verify=$verifyResult;Path=$bundlePath}
}
function Get-ContextState([object]$Context) { Get-Content $Context.SimulationStatePath -Raw|ConvertFrom-Json }
function Save-ContextState([object]$Context,[object]$State) { Add-Mutation $Context 'STATE_WRITE';Write-AtomicJson $Context.SimulationStatePath $State }
function Get-DynamicArtifactDefinitions([object]$Context) {$d=$Context.DataRoot;@([pscustomobject]@{RelativePath='streamlit_opensea_sales\data_opensea_sales\market_overview_enriched\market_period_summaries.json';Path=(Join-Path $d 'market_overview_enriched\market_period_summaries.json')},[pscustomobject]@{RelativePath='streamlit_opensea_sales\data_opensea_sales\market_overview_enriched\market_expansion_metrics.json';Path=(Join-Path $d 'market_overview_enriched\market_expansion_metrics.json')},[pscustomobject]@{RelativePath='streamlit_opensea_sales\data_opensea_sales\trader_analytics_snapshot.json';Path=(Join-Path $d 'trader_analytics_snapshot.json')},[pscustomobject]@{RelativePath='streamlit_opensea_sales\data_opensea_sales\item_class_snapshot.json';Path=(Join-Path $d 'item_class_snapshot.json')},[pscustomobject]@{RelativePath='streamlit_opensea_sales\data_opensea_sales\gunzscope_supply_snapshot_v3_provider.json';Path=(Join-Path $d 'gunzscope_supply_snapshot_v3_provider.json')},[pscustomobject]@{RelativePath='streamlit_opensea_sales\data_opensea_sales\opensea_account_profiles_snapshot.json';Path=(Join-Path $d 'opensea_account_profiles_snapshot.json')})}
function Test-8502ProcessIdentity {
    param([object]$Listener,[object]$Process,[string]$ExpectedAppPath=$script:ExpectedApp,[string]$ExpectedRuntimeAppPath='')
    if(-not$Listener -or $Listener.LocalAddress -ne '127.0.0.1' -or [int]$Listener.LocalPort -ne 8502 -or $Listener.State -ne 'Listen'){throw '8502_PROCESS_LISTENER_MISMATCH'}
    if(-not$Process -or $Listener.OwningProcess -and [int]$Listener.OwningProcess -ne [int]$Process.ProcessId){throw '8502_PROCESS_OWNER_MISMATCH'}
    if(-not$Process -or [string]::IsNullOrWhiteSpace([string]$Process.ExecutablePath) -or -not(Test-Path -LiteralPath $Process.ExecutablePath -PathType Leaf)){throw '8502_PROCESS_EXECUTABLE_MISSING'}
    if([IO.Path]::GetFileName([string]$Process.ExecutablePath) -ine 'python.exe'){throw '8502_PROCESS_NOT_PYTHON'}
    $command=[string]$Process.CommandLine;if([string]::IsNullOrWhiteSpace($command)){throw '8502_PROCESS_COMMANDLINE_MISSING'}
    if($command -notmatch '(?i)(?:-m\s+streamlit\s+run|(?:^|\s)streamlit(?:\.exe)?\s+run)'){throw '8502_PROCESS_NOT_STREAMLIT'}
    if($command -match '(?i)app_gaming_marketplace\.py'){throw '8502_PROCESS_FORBIDDEN_APP'}
    if($command -match '(?i)--server\.port(?:\s+|=)8501(?:\s|$)' -or $command -match '(?i)--server\.port(?:\s+|=)8504(?:\s|$)'){throw '8502_PROCESS_FORBIDDEN_PORT'}
    $portMatch=[regex]::Match($command,'(?i)--server\.port(?:\s+|=)(\d+)');if(-not$portMatch.Success -or [int]$portMatch.Groups[1].Value -ne 8502){throw '8502_PROCESS_PORT_MISMATCH'}
    $addressMatch=[regex]::Match($command,'(?i)--server\.address(?:\s+|=)([^\s]+)');if($addressMatch.Success -and $addressMatch.Groups[1].Value.Trim('"') -ne '127.0.0.1'){throw '8502_PROCESS_ADDRESS_MISMATCH'}
    $appMatch=[regex]::Match($command,'(?i)(?:"(?<quoted>[^"\r\n]*app_opensea_sales\.py)"|(?<bare>[^\s"\r\n]*app_opensea_sales\.py))');if(-not$appMatch.Success){throw '8502_PROCESS_APP_MISMATCH'};$appToken=if($appMatch.Groups['quoted'].Success){$appMatch.Groups['quoted'].Value}else{$appMatch.Groups['bare'].Value}
    if($appToken -match '[\\/]'){$normalized=[IO.Path]::GetFullPath($appToken);$allowed=@([IO.Path]::GetFullPath($ExpectedAppPath));if($ExpectedRuntimeAppPath){$allowed+=[IO.Path]::GetFullPath($ExpectedRuntimeAppPath)};if($allowed -notcontains $normalized){throw '8502_PROCESS_ABSOLUTE_PATH_MISMATCH'}}elseif($appToken -notin @('app_opensea_sales.py','streamlit_opensea_sales\app_opensea_sales.py')){throw '8502_PROCESS_APP_MISMATCH'}
    $Process
}
function Get-8502Process {
    param([string]$ExpectedRuntimeAppPath='')
    $connection=Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8502 -State Listen -ErrorAction SilentlyContinue|Where-Object {$_.LocalAddress -eq '127.0.0.1' -and [int]$_.LocalPort -eq 8502 -and $_.State -eq 'Listen'}|Select-Object -First 1
    if(-not$connection){throw '8502_PROCESS_NOT_FOUND'}
    $process=Get-CimInstance Win32_Process -Filter ('ProcessId='+$connection.OwningProcess)
    Test-8502ProcessIdentity $connection $process $script:ExpectedApp $ExpectedRuntimeAppPath
}
function Assert-AllowedMigrationSet([string[]]$Migrations){if($Migrations.Count -ne 3){throw 'MIGRATION_ALLOWLIST_FAILED'};for($i=0;$i-lt 3;$i++){if($Migrations[$i] -ne $script:AllowedMigrations[$i]){throw 'MIGRATION_ALLOWLIST_FAILED'}};if($Migrations -contains 'sql/add_site_product_events_trader_usd_toggle.sql'){throw 'REDUNDANT_MIGRATION_FORBIDDEN'}}

function Read-PreparedReleaseManifest {
    param([string]$Path,[string]$ExpectedHash,[string]$ExpectedHead,[object]$Context)
    if(-not(Test-Path $Path -PathType Leaf)){throw 'PREPARED_RELEASE_MANIFEST_MISSING'};if($ExpectedHash -and (Get-Sha256 $Path) -ne $ExpectedHash.ToLowerInvariant()){throw 'PREPARED_RELEASE_MANIFEST_HASH_MISMATCH'};$manifest=Get-Content $Path -Raw|ConvertFrom-Json
    foreach($name in @('manifest_version','prepared_release_head','prepared_release_git_tree_sha','requirements_txt_sha256','requirements_lock_sha256','wheelhouse','runtime_contract','validation')){if($null -eq $manifest.$name){throw 'PREPARED_RELEASE_MANIFEST_INCOMPLETE'}};if([int]$manifest.manifest_version -ne 2){throw 'PREPARED_RELEASE_MANIFEST_VERSION_INVALID'};if($ExpectedHead -and $manifest.prepared_release_head -ne $ExpectedHead){throw 'PREPARED_RELEASE_HEAD_MISMATCH'}
    $base=Split-Path $Path -Parent;$repo=if($manifest.prepared_repo_path){$manifest.prepared_repo_path}else{Join-Path $base 'repo'};if($Context.Mode -eq 'PRODUCTION'){if($Context.PreparedReleaseRoot -and [IO.Path]::GetFullPath($repo) -ne [IO.Path]::GetFullPath((Join-Path $Context.PreparedReleaseRoot 'repo'))){throw 'PREPARED_RELEASE_ROOT_MISMATCH'};if(-not(Test-Path $repo -PathType Container)){throw 'PREPARED_RELEASE_REPO_MISSING'};$tree=(& git -c ('safe.directory='+$repo) -C $repo rev-parse ($manifest.prepared_release_head+'^{tree}')).Trim();if($LASTEXITCODE -ne 0 -or $tree.ToLowerInvariant() -ne ([string]$manifest.prepared_release_git_tree_sha).ToLowerInvariant()){throw 'PREPARED_RELEASE_TREE_MISMATCH'};$repoHead=(& git -c ('safe.directory='+$repo) -C $repo rev-parse HEAD).Trim();if($LASTEXITCODE -ne 0 -or $repoHead -ne $manifest.prepared_release_head){throw 'PREPARED_RELEASE_HEAD_MISMATCH'};if(((& git -c ('safe.directory='+$repo) -C $repo status --porcelain)-join '') -ne ''){throw 'PREPARED_RELEASE_REPO_NOT_CLEAN'};$req=(Join-Path $repo 'requirements.txt');$lock=(Join-Path $repo 'requirements.lock.txt');if(-not(Test-Path $req -PathType Leaf) -or -not(Test-Path $lock -PathType Leaf) -or (Get-Sha256 $req).ToLowerInvariant() -ne ([string]$manifest.requirements_txt_sha256).ToLowerInvariant() -or (Get-Sha256 $lock).ToLowerInvariant() -ne ([string]$manifest.requirements_lock_sha256).ToLowerInvariant()){throw 'PREPARED_RELEASE_REQUIREMENTS_HASH_MISMATCH'}}
    if([int]$manifest.wheelhouse.package_count -ne 45 -or [string]::IsNullOrWhiteSpace([string]$manifest.wheelhouse.manifest_path) -or [string]$manifest.wheelhouse.manifest_sha256 -eq ''){throw 'PREPARED_RELEASE_WHEELHOUSE_INVALID'};$wheel=Join-Path $base $manifest.wheelhouse.manifest_path;if(-not(Test-Path $wheel -PathType Leaf) -or (Get-Sha256 $wheel).ToLowerInvariant() -ne ([string]$manifest.wheelhouse.manifest_sha256).ToLowerInvariant()){throw 'PREPARED_RELEASE_WHEELHOUSE_HASH_MISMATCH'};if([int]$manifest.runtime_contract.locked_package_count -ne 45 -or [int]$manifest.runtime_contract.exact_lock_match -ne 45 -or $manifest.runtime_contract.pip_check -ne 'PASS' -or $manifest.runtime_contract.import_gate -ne 'PASS'){throw 'PREPARED_RELEASE_RUNTIME_GATES_FAILED'};if([int]$manifest.validation.full_tests_failure_count -ne 0 -or $manifest.validation.canary -ne 'PASS' -or $manifest.validation.application_readers -ne 'PASS'){throw 'PREPARED_RELEASE_VALIDATION_GATES_FAILED'};[pscustomobject]@{Manifest=$manifest;Base=$base;Repo=$repo;WheelManifest=$wheel}
}
function Read-BackupManifest {
    param([string]$Path,[object]$Context)
    if(-not(Test-Path $Path -PathType Leaf)){throw 'BACKUP_MANIFEST_MISSING'};$manifest=Get-Content $Path -Raw|ConvertFrom-Json;if([int]$manifest.manifest_version -ne 2 -or -not$manifest.backup_complete -or $manifest.target_root -ne $Context.Root -or [int]$manifest.target_port -ne $Context.Port -or $manifest.target_app -ne $Context.AppPath){throw 'BACKUP_MANIFEST_INVALID'};$base=Split-Path $Path -Parent;foreach($pair in @(@('env_backup_relative_path','env_sha256'),@('git_bundle_relative_path','git_bundle_sha256'),@('db_dump_relative_path','db_dump_sha256'))){$candidate=Join-Path $base $manifest.($pair[0]);if(-not(Test-Path $candidate -PathType Leaf) -or (Get-Sha256 $candidate) -ne [string]$manifest.($pair[1])){throw 'BACKUP_MANIFEST_HASH_MISMATCH'}};if($manifest.db_dump_format -ne 'custom' -or $manifest.db_dump_validation -ne 'PASS'){throw 'BACKUP_DB_VALIDATION_MISSING'};if(@($manifest.dynamic_artifacts).Count -ne 6 -or @($manifest.production_refresh_tasks).Count -ne 2){throw 'BACKUP_MANIFEST_STATE_INCOMPLETE'};foreach($artifact in @($manifest.dynamic_artifacts)){if($artifact.existed_before){$candidate=Join-Path $base $artifact.backup_relative_path;if(-not(Test-Path $candidate -PathType Leaf) -or (Get-Sha256 $candidate) -ne [string]$artifact.sha256_before){throw 'BACKUP_ARTIFACT_HASH_MISMATCH'}}};[pscustomobject]@{Manifest=$manifest;Base=$base}
}

function Invoke-BackupCore {
    param([object]$Context,[switch]$Execute)
    Assert-Context $Context;if(-not$Execute){Write-KV 'MODE' 'DRY_RUN';Write-KV 'TARGET_ROOT' $Context.Root;Write-KV 'TARGET_PORT' $Context.Port;Write-KV 'BACKUP_MANIFEST_SCHEMA_VERSION' 2;Write-KV 'BACKUP_SET_VALID' 'YES';return}
    Set-Phase $Context 'BACKUP_VALIDATE';$head=$Context.ExpectedOldHead;$branch='main';$processPid=0;$processExe='simulation';$processCmd='simulation app_opensea_sales.py';if($Context.Mode -eq 'PRODUCTION'){$head=(& git -c ('safe.directory='+$Context.Root) -C $Context.Root rev-parse HEAD).Trim();$branch=(& git -c ('safe.directory='+$Context.Root) -C $Context.Root branch --show-current).Trim();if(((& git -c ('safe.directory='+$Context.Root) -C $Context.Root status --porcelain)-join '') -ne ''){throw 'PRODUCTION_WORKTREE_NOT_CLEAN'};$process=Get-8502Process;if(-not$process){throw '8502_PROCESS_NOT_FOUND'};$processPid=$process.ProcessId;$processExe=$process.ExecutablePath;$processCmd=$process.CommandLine;$tools=Get-PostgresTools;foreach($name in @('pg_dump','pg_restore','psql')){if(-not$tools.ContainsKey($name)){throw ('POSTGRES_TOOL_MISSING:'+ $name)}};Get-DatabaseEnvironment $Context.EnvPath -Required|Out-Null}elseif(-not(Test-Path $Context.EnvPath -PathType Leaf)){throw 'SIMULATION_ENV_MISSING'};Add-Mutation $Context 'BACKUP_CREATE';$stamp=Get-Date -Format yyyyMMdd_HHmmss;$short=if($head.Length -gt 8){$head.Substring(0,8)}else{$head};$out=Join-Path $Context.BackupRoot ($stamp+'_'+$short);New-Item -ItemType Directory -Path $out -Force|Out-Null;$manifest=[ordered]@{manifest_version=2;created_at=(Get-Date).ToUniversalTime().ToString('o');target_root=$Context.Root;target_port=$Context.Port;target_app=$Context.AppPath;old_git_head=$head;old_git_branch=$branch;old_git_clean=$true;old_process_pid=$processPid;old_process_executable=$processExe;old_process_command_line_sanitized=$processCmd;old_app_path=$Context.AppPath;old_port=$Context.Port;old_runtime_root=$Context.RuntimeRoot;env_backup_relative_path='.env';git_bundle_relative_path='production.bundle';db_dump_relative_path='production.dump';db_dump_format='custom';db_dump_validation='PENDING';dynamic_artifacts=@();active_runtime_existed=$false;production_refresh_tasks=@();backup_complete=$false}
    $bundleResult=Invoke-GitBundleBackup $Context $out;if($Context.Mode -eq 'SIMULATION'){$null=Copy-Item $Context.EnvPath (Join-Path $out '.env');$null=Set-Content (Join-Path $out 'production.dump') 'sandbox custom dump';$manifest.db_dump_validation='PASS'}else{Copy-Item $Context.EnvPath (Join-Path $out '.env');$env=Get-DatabaseEnvironment $Context.EnvPath -Required;Invoke-ChildProcess $tools.pg_dump @('--format=custom','--file',(Join-Path $out 'production.dump')) $Context.Root 1800 $env|Out-Null;Invoke-ChildProcess $tools.pg_restore @('--list',(Join-Path $out 'production.dump')) $Context.Root 300 $env|Out-Null;$manifest.db_dump_validation='PASS'};$manifest.git_bundle_validation='PASS';$manifest.env_sha256=Get-Sha256 (Join-Path $out '.env');$manifest.git_bundle_sha256=Get-Sha256 (Join-Path $out 'production.bundle');$manifest.db_dump_sha256=Get-Sha256 (Join-Path $out 'production.dump')
    foreach($definition in Get-DynamicArtifactDefinitions $Context){$entry=[ordered]@{relative_path=$definition.RelativePath;existed_before=(Test-Path $definition.Path -PathType Leaf)};if($entry.existed_before){$entry.backup_relative_path='artifacts\'+[IO.Path]::GetFileName($definition.Path);New-Item (Join-Path $out 'artifacts') -ItemType Directory -Force|Out-Null;Copy-Item $definition.Path (Join-Path $out $entry.backup_relative_path);$entry.sha256_before=Get-Sha256 $definition.Path;$entry.size_bytes=(Get-Item $definition.Path).Length};$manifest.dynamic_artifacts+=,$entry};$active=Join-Path $Context.RuntimeRoot 'ACTIVE_RUNTIME.json';if(Test-Path $active -PathType Leaf){New-Item (Join-Path $out 'runtime') -ItemType Directory -Force|Out-Null;Copy-Item $active (Join-Path $out 'runtime\ACTIVE_RUNTIME.json');$manifest.active_runtime_existed=$true;$manifest.active_runtime_backup_relative_path='runtime\ACTIVE_RUNTIME.json';$manifest.active_runtime_sha256=Get-Sha256 $active}
    foreach($name in $script:ManagedTasks){$entry=[ordered]@{task_name=$name;existed_before=$false};if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;$taskProperty=@();if($state.tasks){$taskProperty=@($state.tasks.PSObject.Properties|Where-Object Name -eq $name)};if($taskProperty.Count -gt 0){$entry.existed_before=$true;$entry.state=$state.tasks.$name}}else{$task=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue;if($task){$relative='tasks\'+$name+'.xml';New-Item (Join-Path $out 'tasks') -ItemType Directory -Force|Out-Null;Write-AtomicText (Join-Path $out $relative) (Export-ScheduledTask -TaskName $name -ErrorAction Stop);$entry.existed_before=$true;$entry.exported_xml_relative_path=$relative;$entry.xml_sha256=Get-Sha256 (Join-Path $out $relative);$entry.enabled=($task.State -ne 'Disabled')}};$manifest.production_refresh_tasks+=,$entry};$manifest.backup_complete=$true;Write-AtomicJson (Join-Path $out 'BACKUP_MANIFEST.json') $manifest;Write-KV 'BACKUP_MANIFEST_SCHEMA_VERSION' 2;Write-KV 'BACKUP_MANIFEST_PATH' (Join-Path $out 'BACKUP_MANIFEST.json');Write-KV 'BACKUP_RESULT' 'PASS'
}

function Write-SimulationArtifacts([object]$Context,[int[]]$Indexes) {$definitions=Get-DynamicArtifactDefinitions $Context;foreach($index in $Indexes){$path=$definitions[$index].Path;New-Item (Split-Path $path) -ItemType Directory -Force|Out-Null;switch($index){0{$payload=@{schema_version=1;source_market_build_id='release';source_latest_date='2026-01-01T00:00:00Z';periods=@{all=@{totals=@{transactions=1};usd_pricing=@{total_volume_usd=1}}}}};1{$payload=@{schema_version=1;source_market_build_id='release';source_latest_date='2026-01-01T00:00:00Z';unique_wallets=@{daily=@(@{date='2026-01-01';unique_wallets=1});monthly=@(@{month='2026-01';month_start='2026-01-01';month_end='2026-01-31';unique_wallets=1})}}};2{$payload=@{schema_version=1;source='opensea';generated_at='2026-01-01T00:00:00Z';event_count=1;wallet_count=1;wallets=@(@{wallet='sandbox-wallet'})}};3{$payload=@{schema_version=1;source='sandbox';items=@{Example=@{class='Weapon'}}}};4{$payload=@{schema_version=3;source='gunzscope';provider_scope=@{exclude_zero=$true;exclude_base=$false;sort='activeMints';order='asc'};provider_items=@{p1=@{provider_item_id='p1';provider_item_name='Example';provider_rarity='common';status='ok';ranking_eligible=$true;raw_active_mints=1}};catalog_mappings=@{Example=@{mapping_status='DIRECT_CURRENT';provider_item_id='p1'}};provider_item_conflicts=@()}};5{$payload=@{schema_version=1;source='opensea';profiles=@{};fallback_names=@{'sandbox-wallet'='Sandbox Wallet'}}};};Write-AtomicJson $path $payload}}
function Invoke-Readers([object]$Context) {if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;if($state.reader_fail){throw 'APPLICATION_READER_VALIDATION_FAILED'};foreach($definition in Get-DynamicArtifactDefinitions $Context){if(-not(Test-Path $definition.Path -PathType Leaf)){throw 'APPLICATION_READER_VALIDATION_FAILED'};try{$null=Get-Content $definition.Path -Raw|ConvertFrom-Json}catch{throw 'APPLICATION_READER_VALIDATION_FAILED'}};Write-KV 'POST_REFRESH_APPLICATION_READERS' 'PASS';return};$env=Get-SafeEnv $Context.EnvPath;$env['GUNZSCOPE_SUPPLY_SOURCE']='v3';$helper=Join-Path $Context.RepoRoot 'ops\production\validate_dynamic_artifacts.py';Invoke-ChildProcess $Context.ReleasePython @($helper,'--repo-root',$Context.RepoRoot,'--data-dir',$Context.DataRoot,'--env',$Context.EnvPath) $Context.RepoRoot 900 $env (Join-Path $Context.RuntimeRoot 'dynamic_reader_validation.log')|Out-Null;Write-KV 'POST_REFRESH_APPLICATION_READERS' 'PASS'}
function Invoke-RefreshAdapter([object]$Context,[string]$Name,[string]$Python,[string[]]$Arguments,[string]$WorkingDirectory) {if($Context.Mode -eq 'SIMULATION'){Add-Mutation $Context ('REFRESH_'+$Name);Add-Content (Join-Path $Context.Root 'refresh.commands.log') $Name;return};Invoke-ChildProcess $Python $Arguments $WorkingDirectory 1800 (Get-DatabaseEnvironment $Context.EnvPath)|Out-Null}
 function Get-RefreshPython([object]$Context) {
     if($Context.Mode -eq 'SIMULATION'){return $Context.ReleasePython}
     if(-not [string]::IsNullOrWhiteSpace([string]$Context.DeploymentRefreshPython)) {
         if(-not (Test-Path $Context.DeploymentRefreshPython -PathType Leaf)){throw 'DEPLOYMENT_REFRESH_RUNTIME_MISSING'}
         Assert-FinalRuntimePath $Context.DeploymentRefreshPython $Context.ExpectedReleaseHead $Context
         return $Context.DeploymentRefreshPython
     }
     $active=Join-Path $script:ExpectedRuntimeRoot 'ACTIVE_RUNTIME.json'
     if(-not(Test-Path $active -PathType Leaf)){throw 'ACTIVE_RUNTIME_MISSING'}
     $state=Get-Content $active -Raw|ConvertFrom-Json
     $head=(& git -c ('safe.directory='+$Context.Root) -C $Context.Root rev-parse HEAD).Trim()
     if($state.release_head -ne $head -or -not(Test-Path $state.python_path -PathType Leaf)){throw 'ACTIVE_RUNTIME_INVALID'}
     Assert-FinalRuntimePath $state.python_path $head $Context
     $state.python_path
 }
function Invoke-DerivedRefreshCore {param([object]$Context,[switch]$Execute);Assert-Context $Context;if(-not$Execute){Write-KV 'MODE' 'DRY_RUN';Write-KV 'DERIVED_REFRESH_PLAN' 'PASS';return};Set-Phase $Context 'DERIVED_REFRESH';Add-Mutation $Context 'DERIVED_REFRESH';$python=Get-RefreshPython $Context;$definitions=Get-DynamicArtifactDefinitions $Context;if($Context.Mode -eq 'SIMULATION'){Write-SimulationArtifacts $Context @(0,1,2)}else{$scripts=Join-Path $Context.RepoRoot 'scripts';Invoke-RefreshAdapter $Context 'market_period' $python @((Join-Path $scripts 'build_market_period_summaries.py'),'--data-dir',$Context.DataRoot) $Context.RepoRoot;Invoke-RefreshAdapter $Context 'market_expansion' $python @((Join-Path $scripts 'build_market_expansion_metrics.py')) $Context.RepoRoot;Invoke-RefreshAdapter $Context 'trader_analytics' $python @((Join-Path $scripts 'build_trader_analytics.py'),'--data-dir',$Context.DataRoot,'--output',$definitions[2].Path) $Context.RepoRoot};foreach($index in 0..2){if(-not(Test-Path $definitions[$index].Path -PathType Leaf) -or (Get-Item $definitions[$index].Path).Length -le 0){throw 'DERIVED_OUTPUT_MISSING'}};Write-KV 'DERIVED_MARKET_PERIOD' 'PASS';Write-KV 'DERIVED_MARKET_EXPANSION' 'PASS';Write-KV 'DERIVED_TRADER_ANALYTICS' 'PASS';Write-KV 'DERIVED_REFRESH' 'PASS'}
function Invoke-MetadataRefreshCore {param([object]$Context,[switch]$Execute);Assert-Context $Context;if(-not$Execute){Write-KV 'MODE' 'DRY_RUN';Write-KV 'METADATA_REFRESH_PLAN' 'PASS';return};Set-Phase $Context 'METADATA_REFRESH';Add-Mutation $Context 'METADATA_REFRESH';$python=Get-RefreshPython $Context;$definitions=Get-DynamicArtifactDefinitions $Context;if($Context.Mode -eq 'SIMULATION'){Write-SimulationArtifacts $Context @(3,4,5);Add-Content (Join-Path $Context.Root 'refresh.commands.log') 'item_class';Add-Content (Join-Path $Context.Root 'refresh.commands.log') 'gunzscope_v3';Add-Content (Join-Path $Context.Root 'refresh.commands.log') 'profile_sync'}else{$scripts=Join-Path $Context.RepoRoot 'scripts';Invoke-RefreshAdapter $Context 'item_class' $python @((Join-Path $scripts 'refresh_item_class_snapshot.py')) $Context.RepoRoot;Invoke-RefreshAdapter $Context 'gunzscope_v3' $python @((Join-Path $scripts 'refresh_gunzscope_supply_v3_provider.py')) $Context.RepoRoot;Invoke-RefreshAdapter $Context 'profile_sync' $python @((Join-Path $scripts 'run_trader_profile_sync.py')) $Context.RepoRoot};foreach($index in 3..5){if(-not(Test-Path $definitions[$index].Path -PathType Leaf) -or (Get-Item $definitions[$index].Path).Length -le 0){throw 'METADATA_OUTPUT_MISSING'}};Write-KV 'METADATA_ITEM_CLASS' 'PASS';Write-KV 'METADATA_GUNZSCOPE_V3' 'PASS';Write-KV 'METADATA_PROFILE_SYNC' 'PASS';Write-KV 'METADATA_REFRESH' 'PASS'}
function Get-DesiredTaskDefinition([object]$Context,[string]$Name) {$derived=$Name -eq $script:ManagedTasks[0];$minutes=if($derived){15}else{60};$scriptName=if($derived){'refresh_production_derived.ps1'}else{'refresh_production_metadata.ps1'};$approval=if($derived){'REFRESH_OTG_DERIVED_8502'}else{'REFRESH_OTG_METADATA_8502'};$path=Join-Path $Context.Root ('ops\production\'+$scriptName);$arguments='-NoProfile -ExecutionPolicy Bypass -File "'+$path+'" -Execute -ApprovalPhrase '+$approval;if($Context.Mode -eq 'SIMULATION' -or $Context.ReleasePython){$arguments+=' -ReleasePython "'+$Context.ReleasePython+'"'};[ordered]@{task_name=$Name;executable='PowerShell.exe';arguments=$arguments;working_directory=$Context.Root;interval_minutes=$minutes;multiple_instances='IgnoreNew';start_when_available=$true;principal='SYSTEM';run_level='Highest';enabled=$true}}
function Test-TaskDefinitionMatch([object]$Existing,[object]$Desired){foreach($key in @('executable','arguments','working_directory','interval_minutes','multiple_instances','start_when_available','principal','run_level','enabled')){if([string]$Existing.$key -ne [string]$Desired[$key]){return $false}};return $true}
function Invoke-TaskConfigurationCore {param([object]$Context,[switch]$Execute);Assert-Context $Context;if(-not$Execute){Write-KV 'MODE' 'DRY_RUN';Write-KV 'TASK_CONFIGURATION_PLAN' 'PASS';Write-KV 'PRODUCTION_REFRESH_TASK_COLLISION_POLICY' 'FAIL_CLOSED';foreach($name in $script:ManagedTasks){Write-KV ('TASK_'+$name) ((Get-DesiredTaskDefinition $Context $name)|ConvertTo-Json -Compress)};return};Set-Phase $Context 'TASK_CONFIGURATION';Add-Mutation $Context 'TASK_CONFIGURATION';if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;$tasks=@{};if($state.tasks){foreach($property in $state.tasks.PSObject.Properties){$tasks[$property.Name]=$property.Value}};foreach($name in $script:ManagedTasks){$desired=Get-DesiredTaskDefinition $Context $name;if($tasks.ContainsKey($name) -and -not(Test-TaskDefinitionMatch $tasks[$name] $desired)){throw ('TASK_COLLISION:'+ $name)};$tasks[$name]=[pscustomobject]$desired};$state.tasks=$tasks;Save-ContextState $Context $state}else{foreach($name in $script:ManagedTasks){$desired=Get-DesiredTaskDefinition $Context $name;$task=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue;if($task){$action=$task.Actions|Select-Object -First 1;$settings=$task.Settings;if("$($action.Execute)" -notmatch '(?i)power' -or "$($action.Arguments)" -ne $desired.arguments -or "$($action.WorkingDirectory)" -ne $desired.working_directory -or "$($settings.MultipleInstances)" -ne 'IgnoreNew' -or -not$settings.StartWhenAvailable){throw ('TASK_COLLISION:'+ $name)};continue};$action=New-ScheduledTaskAction -Execute $desired.executable -Argument $desired.arguments -WorkingDirectory $desired.working_directory;$trigger=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $desired.interval_minutes) -RepetitionDuration (New-TimeSpan -Days 3650);$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable;Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -User SYSTEM -ErrorAction Stop|Out-Null}};Write-KV 'TASK_CONFIGURATION' 'PASS';Write-KV 'PRODUCTION_REFRESH_TASKS' 'PASS'}

function Invoke-PrepareRuntime([object]$Context,[object]$Prepared) {$runtime=Get-FinalRuntimeRoot $Context.ExpectedReleaseHead $Context;$python=Get-FinalRuntimePython $Context.ExpectedReleaseHead $Context;$manifestPath=Join-Path $runtime 'RUNTIME_MANIFEST.json';$wheelHash=$Prepared.Manifest.wheelhouse.manifest_sha256;if(Test-Path $manifestPath -PathType Leaf){$existing=Get-Content $manifestPath -Raw|ConvertFrom-Json;if($existing.release_head -ne $Context.ExpectedReleaseHead -or $existing.requirements_lock_sha256 -ne $Prepared.Manifest.requirements_lock_sha256 -or $existing.wheelhouse_manifest_sha256 -ne $wheelHash){throw 'FINAL_RUNTIME_REUSE_FAIL_CLOSED'};if(-not(Test-Path $python -PathType Leaf)){throw 'FINAL_RUNTIME_REUSE_MISSING_PYTHON'};$Context.ReleasePython=$python;$Context.DeploymentRefreshPython=$python;Write-KV 'FINAL_RUNTIME_REUSED' 'YES';return};Add-Mutation $Context 'DEPLOY_PREPARE_RUNTIME';if($Context.Mode -eq 'SIMULATION'){New-Item (Join-Path $runtime '.venv\Scripts') -ItemType Directory -Force|Out-Null;Set-Content $python 'sandbox python';Write-AtomicJson $manifestPath ([ordered]@{release_head=$Context.ExpectedReleaseHead;python_path=$python;requirements_lock_sha256=$Prepared.Manifest.requirements_lock_sha256;exact_lock_match=45;pip_check='PASS';wheelhouse_manifest_sha256=$wheelHash;created_at=(Get-Date).ToUniversalTime().ToString('o')});$Context.ReleasePython=$python;$Context.DeploymentRefreshPython=$python;return};$base='C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe';if(-not(Test-Path $base -PathType Leaf)){throw 'BASE_PYTHON_MISSING'};New-Item $runtime -ItemType Directory -Force|Out-Null;Invoke-ChildProcess $base @('-m','venv','--without-pip',(Join-Path $runtime '.venv')) $Context.Root 60 @{} (Join-Path $runtime 'venv.log')|Out-Null;$python=Join-Path $runtime '.venv\Scripts\python.exe';Invoke-ChildProcess $python @('-m','ensurepip','--upgrade') $Context.Root 120 @{} (Join-Path $runtime 'ensurepip.log')|Out-Null;$wheels=Get-ChildItem (Join-Path $Prepared.Base 'wheelhouse') -Filter '*.whl' -File|Sort-Object Name;if(@($wheels).Count -ne 45){throw 'FINAL_RUNTIME_WHEELHOUSE_COUNT_FAILED'};foreach($wheel in $wheels){Invoke-ChildProcess $python @('-m','pip','install','--no-index','--no-deps','--disable-pip-version-check',$wheel.FullName) $Context.Root 300 @{} (Join-Path $runtime ('wheel_'+$wheel.BaseName+'.log'))|Out-Null};Invoke-ChildProcess $python @('-m','pip','check') $Context.Root 120 @{} (Join-Path $runtime 'pip_check.log')|Out-Null;Invoke-ChildProcess $python @('-c','import streamlit,pandas,plotly,numpy,psycopg2,dotenv,requests') $Context.Root 120 @{} (Join-Path $runtime 'import_gate.log')|Out-Null;Write-AtomicJson $manifestPath ([ordered]@{release_head=$Context.ExpectedReleaseHead;python_path=$python;requirements_lock_sha256=$Prepared.Manifest.requirements_lock_sha256;exact_lock_match=45;pip_check='PASS';wheelhouse_manifest_sha256=$wheelHash;created_at=(Get-Date).ToUniversalTime().ToString('o')});$Context.ReleasePython=$python;$Context.DeploymentRefreshPython=$python}
function Invoke-PreStopCanary([object]$Context,[object]$Prepared) {
    Set-Phase $Context 'DEPLOY_PRESTOP_CANARY'
    if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;if($state.canary_fail){throw 'PRESTOP_CANARY_FAILED'};Add-Mutation $Context 'DEPLOY_PRESTOP_CANARY';$state.canary='healthy';Save-ContextState $Context $state;Write-KV 'PRESTOP_CANARY' 'PASS';return}
    if(Invoke-HealthCheck 8505 1){throw 'PRESTOP_CANARY_PORT_OCCUPIED'}
    $env=Get-SafeEnv $Context.EnvPath;$env['GUNZSCOPE_SUPPLY_SOURCE']='v3';$env['OTG_ANALYTICS_WRITES_ENABLED']='false';$env['OTG_SITE_ANALYTICS_ENABLED']='false';$env['OTG_PRODUCT_EVENTS_ENABLED']='false';$env['OTG_FEEDBACK_WRITES_ENABLED']='false';$env['OTG_FEEDBACK_TELEGRAM_ENABLED']='false'
    $app=Join-Path $Prepared.Base 'repo\streamlit_opensea_sales\app_opensea_sales.py';$logRoot=Join-Path $Context.RuntimeRoot 'logs';New-Item $logRoot -ItemType Directory -Force|Out-Null;$log=Join-Path $logRoot 'prestop_canary.log';$psi=New-Object Diagnostics.ProcessStartInfo;$psi.FileName=$Context.ReleasePython;$psi.WorkingDirectory=(Split-Path $app);$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true;$psi.Arguments='-m streamlit run "'+$app+'" --server.address 127.0.0.1 --server.port 8505 --server.fileWatcherType none --browser.gatherUsageStats false';foreach($key in $env.Keys){$psi.EnvironmentVariables[$key]=[string]$env[$key]};$canary=New-Object Diagnostics.Process;$canary.StartInfo=$psi;if(-not$canary.Start()){throw 'PRESTOP_CANARY_START_FAILED'};$out=$canary.StandardOutput.ReadToEndAsync();$err=$canary.StandardError.ReadToEndAsync();try{if(-not(Invoke-HealthCheck 8505 60)){throw 'PRESTOP_CANARY_HTTP_FAILED'};$helper=Join-Path $Prepared.Base 'repo\ops\production\validate_dynamic_artifacts.py';Invoke-ChildProcess $Context.ReleasePython @($helper,'--repo-root',(Join-Path $Prepared.Base 'repo'),'--data-dir',(Join-Path $Prepared.Base 'repo\streamlit_opensea_sales\data_opensea_sales')) $Prepared.Base 900 $env (Join-Path $logRoot 'prestop_reader.log')|Out-Null}finally{if(-not$canary.HasExited){$canary.Kill()};$canary.WaitForExit(10000);$canaryLogs=$out.Result+$err.Result;Write-AtomicText $log $canaryLogs;if($canaryLogs -match 'Traceback|ModuleNotFoundError|ImportError|Uncaught app exception'){throw 'PRESTOP_CANARY_LOG_FAILED'};if(Invoke-HealthCheck 8505 1){throw 'PRESTOP_CANARY_ORPHAN'}};Add-Mutation $Context 'DEPLOY_PRESTOP_CANARY';Write-KV 'PRESTOP_CANARY' 'PASS'
}
function Resolve-8502RollbackProcess([object]$Context) {
    if($Context.Mode -eq 'SIMULATION') {
        $state=Get-ContextState $Context
        if($state.foreign_listener){throw 'ROLLBACK_FOREIGN_8502_LISTENER'}
        if([string]$state.process -in @('old-healthy','new-healthy','new-failed')){return [pscustomobject]@{State='EXPECTED_PROCESS_PRESENT';ProcessId=18502}}
        return [pscustomobject]@{State='NO_LISTENER';ProcessId=$null}
    }
    $connection=Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8502 -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1
    if(-not$connection){return [pscustomobject]@{State='NO_LISTENER';ProcessId=$null}}
    try{$process=Get-8502Process;return [pscustomobject]@{State='EXPECTED_PROCESS_PRESENT';ProcessId=$process.ProcessId;Process=$process}}catch{throw 'ROLLBACK_FOREIGN_8502_LISTENER'}
}
function Stop-ContextProcess([object]$Context) {Set-Phase $Context 'DEPLOY_STOP';Add-Mutation $Context 'DEPLOY_STOP';if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;$state.process='stopped';Save-ContextState $Context $state;return};$process=Get-8502Process;if(-not$process){throw '8502_PROCESS_NOT_FOUND'};Stop-Process -Id $process.ProcessId -Force;for($i=0;$i-lt 60;$i++){$after=Resolve-8502RollbackProcess $Context;if($after.State -eq 'NO_LISTENER'){return};Start-Sleep -Milliseconds 500};throw '8502_DID_NOT_STOP'}
function Stop-RollbackProcess([object]$Context) {Set-Phase $Context 'ROLLBACK_STOP';$resolution=Resolve-8502RollbackProcess $Context;if($resolution.State -eq 'NO_LISTENER'){return};Add-Mutation $Context 'ROLLBACK_STOP';if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;$state.process='stopped';Save-ContextState $Context $state;return};Stop-Process -Id $resolution.ProcessId -Force;for($i=0;$i-lt 60;$i++){$after=Resolve-8502RollbackProcess $Context;if($after.State -eq 'NO_LISTENER'){return};Start-Sleep -Milliseconds 500};throw 'ROLLBACK_8502_DID_NOT_STOP'}
function Start-ContextProcess([object]$Context,[string]$Python,[string]$App,[switch]$Old) {
    Add-Mutation $Context 'START_PROCESS'
    $launchId=[guid]::NewGuid().ToString('N')
    $logRoot=Join-Path $Context.RuntimeRoot 'logs'
    $stdoutLog=Join-Path $logRoot ('production_'+$launchId+'.out.log')
    $stderrLog=Join-Path $logRoot ('production_'+$launchId+'.err.log')
    if($Context.Mode -eq 'SIMULATION'){
        $state=Get-ContextState $Context
        $state.process=if($Old){'old-healthy'}elseif($state.fail_new_health){'new-failed'}else{'new-healthy'}
        Save-ContextState $Context $state
        Write-AtomicText $stdoutLog ('sandbox process '+$state.process)
        Write-AtomicText $stderrLog ''
        return [pscustomobject]@{Pid=$Context.Port;Id=$Context.Port;Process=$null;StdOutLogPath=$stdoutLog;StdErrLogPath=$stderrLog;StartedAt=(Get-Date).ToUniversalTime().ToString('o')}
    }
    if(-not(Test-Path $Python -PathType Leaf)){throw 'RUNTIME_PYTHON_MISSING'}
    $env=Get-SafeEnv $Context.EnvPath
    $oldEnv=@{}
    $process=$null
    $startFailure=$null
    $restoreFailure=$null
    foreach($key in $env.Keys){$oldEnv[$key]=[Environment]::GetEnvironmentVariable($key,'Process')}
    try {
        foreach($key in $env.Keys){[Environment]::SetEnvironmentVariable($key,[string]$env[$key],'Process')}
        try {
            $launch=Start-RedirectedProcess $Python @('-m','streamlit','run',$App,'--server.address','127.0.0.1','--server.port','8502','--server.fileWatcherType','none','--server.headless','true','--browser.gatherUsageStats','false') (Split-Path $App) $stdoutLog $stderrLog
            $process=$launch.Process
        } catch {
            $startFailure=$_.Exception
        }
    } finally {
        foreach($key in $env.Keys){try{[Environment]::SetEnvironmentVariable($key,$oldEnv[$key],'Process')}catch{if(-not$restoreFailure){$restoreFailure=$_.Exception}}}
    }
    if($startFailure -or $restoreFailure){
        if($process -and -not$process.HasExited){try{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue}catch{};try{$process.WaitForExit(10000)}catch{}}
        if($restoreFailure -and -not$startFailure){throw 'PROCESS_PARENT_ENV_RESTORE_FAILED'}
        throw 'PRODUCTION_START_FAILED'
    }
    if(-not$process){throw 'PRODUCTION_START_FAILED'}
    [pscustomobject]@{Process=$process;Pid=$process.Id;Id=$process.Id;StdOutLogPath=$stdoutLog;StdErrLogPath=$stderrLog;StartedAt=(Get-Date).ToUniversalTime().ToString('o')}
}
function Invoke-HealthCheck([int]$Port,[int]$Seconds=60){$until=(Get-Date).AddSeconds($Seconds);do{try{$response=Invoke-WebRequest ('http://127.0.0.1:'+ $Port) -UseBasicParsing -TimeoutSec 5;if($response.StatusCode -ge 200 -and $response.StatusCode -lt 500){return $true}}catch{};Start-Sleep -Milliseconds 500}while((Get-Date)-lt $until);$false}
function Set-FailClosedEnv([object]$Context){$lines=@();if(Test-Path $Context.EnvPath){$lines=Get-Content $Context.EnvPath};$updates=@{GUNZSCOPE_SUPPLY_SOURCE='v3';OTG_ANALYTICS_WRITES_ENABLED='false';OTG_SITE_ANALYTICS_ENABLED='false';OTG_PRODUCT_EVENTS_ENABLED='false';OTG_FEEDBACK_WRITES_ENABLED='false';OTG_FEEDBACK_TELEGRAM_ENABLED='false'};$seen=@{};$result=@();foreach($line in $lines){if($line -match '^\s*([^#=][^=]*)='){$key=$Matches[1].Trim();if($updates.ContainsKey($key)){$result+=($key+'='+$updates[$key]);$seen[$key]=$true}else{$result+=$line}}else{$result+=$line}};foreach($key in $updates.Keys){if(-not$seen.ContainsKey($key)){$result+=($key+'='+$updates[$key])}};Add-Mutation $Context 'DEPLOY_ENV';Write-AtomicText $Context.EnvPath (($result -join [Environment]::NewLine)+[Environment]::NewLine)}
function Invoke-ContextMigrations([object]$Context){Set-Phase $Context 'DEPLOY_MIGRATIONS';Assert-AllowedMigrationSet $script:AllowedMigrations;Add-Mutation $Context 'DEPLOY_MIGRATIONS';if($Context.Mode -eq 'SIMULATION'){Set-Content (Join-Path $Context.Root 'migrations.log') ($script:AllowedMigrations -join [Environment]::NewLine);return};$tools=Get-PostgresTools;if(-not$tools.ContainsKey('psql')){throw 'PSQL_MISSING'};$env=Get-DatabaseEnvironment $Context.EnvPath -Required;foreach($migration in $script:AllowedMigrations){$path=Join-Path $Context.RepoRoot $migration;if(-not(Test-Path $path)){throw ('MIGRATION_MISSING:'+ $migration)};Invoke-ChildProcess $tools.psql @('-X','-v','ON_ERROR_STOP=1','-f',$path) $Context.Root 300 $env|Out-Null}}
function Invoke-ContextGitFastForward([object]$Context,[string]$ReleaseHead){Set-Phase $Context 'DEPLOY_FAST_FORWARD';Add-Mutation $Context 'DEPLOY_FAST_FORWARD';if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;$state.current_head=$ReleaseHead;Save-ContextState $Context $state;return};& git -c ('safe.directory='+$Context.Root) -C $Context.Root fetch origin main;if($LASTEXITCODE -ne 0){throw 'GIT_FETCH_FAILED'};& git -c ('safe.directory='+$Context.Root) -C $Context.Root merge --ff-only origin/main;if($LASTEXITCODE -ne 0){throw 'GIT_FAST_FORWARD_FAILED'}}
function Invoke-ContextGitReset([object]$Context,[string]$OldHead){Set-Phase $Context 'ROLLBACK_GIT';Add-Mutation $Context 'ROLLBACK_GIT';if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;$state.current_head=$OldHead;Save-ContextState $Context $state;return};& git -c ('safe.directory='+$Context.Root) -C $Context.Root reset --hard $OldHead;if($LASTEXITCODE -ne 0){throw 'GIT_ROLLBACK_FAILED'}}
function Write-ActiveRuntime([object]$Context,[int]$ProcessId){$path=Join-Path $Context.RuntimeRoot 'ACTIVE_RUNTIME.json';Add-Mutation $Context 'DEPLOY_ACTIVE_RUNTIME';Write-AtomicJson $path ([ordered]@{release_head=$Context.ExpectedReleaseHead;runtime_root=(Get-FinalRuntimeRoot $Context.ExpectedReleaseHead $Context);python_path=$Context.ReleasePython;started_pid=$ProcessId;activated_at=(Get-Date).ToUniversalTime().ToString('o');health='PASS'})}

function Invoke-DeployCore {
    param([object]$Context,[switch]$Execute)
    Assert-Context $Context;if(-not$Execute){Write-KV 'MODE' 'DRY_RUN';Write-KV 'DEPLOY_PLAN' 'PASS';Write-KV 'MAIN_PROMOTION_REQUIRED' 'YES';Write-KV 'DEPLOY_REMOTE_MAIN_MUTATION' 'FORBIDDEN';Write-KV 'FINAL_RUNTIME_PATH_GUARD' 'PASS';Write-KV 'MUTATION_EXECUTED' 'NO';return};Set-Phase $Context 'DEPLOY_VALIDATE';$prepared=Read-PreparedReleaseManifest $Context.PreparedReleaseManifest $Context.PreparedReleaseManifestSha256 $Context.ExpectedReleaseHead $Context;$null=Read-BackupManifest $Context.BackupManifest $Context;Assert-AllowedMigrationSet $script:AllowedMigrations;if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;if($state.main_head -ne $Context.ExpectedReleaseHead){throw 'MAIN_PROMOTION_REQUIRED'}}else{$actual=(& git -c ('safe.directory='+$Context.Root) -C $Context.Root rev-parse HEAD).Trim();if($actual -ne $Context.ExpectedOldHead){throw 'EXPECTED_OLD_HEAD_MISMATCH'};if(((& git -c ('safe.directory='+$Context.Root) -C $Context.Root status --porcelain)-join '') -ne ''){throw 'PRODUCTION_WORKTREE_NOT_CLEAN'};$main=(& git -c ('safe.directory='+$Context.Root) -C $Context.Root rev-parse origin/main).Trim();if($main -ne $Context.ExpectedReleaseHead){throw 'MAIN_PROMOTION_REQUIRED'};& git -c ('safe.directory='+$Context.Root) -C $Context.Root merge-base --is-ancestor $Context.ExpectedOldHead $Context.ExpectedReleaseHead;if($LASTEXITCODE -ne 0){throw 'RELEASE_NOT_DESCENDANT'};Assert-FinalRuntimePath (Get-FinalRuntimePython $Context.ExpectedReleaseHead $Context) $Context.ExpectedReleaseHead $Context}
    $stopped=$false;try{Set-Phase $Context 'DEPLOY_PREPARE_RUNTIME';Invoke-PrepareRuntime $Context $prepared -Execute;Invoke-PreStopCanary $Context $prepared;Stop-ContextProcess $Context;$stopped=$true;Invoke-ContextGitFastForward $Context $Context.ExpectedReleaseHead;Set-Phase $Context 'DEPLOY_ENV';Set-FailClosedEnv $Context;Invoke-ContextMigrations $Context;Set-Phase $Context 'DEPLOY_DERIVED';Invoke-DerivedRefreshCore $Context -Execute;Set-Phase $Context 'DEPLOY_METADATA';Invoke-MetadataRefreshCore $Context -Execute;Set-Phase $Context 'DEPLOY_RUNTIME_READERS';Invoke-Readers $Context;Set-Phase $Context 'DEPLOY_START';$new=Start-ContextProcess $Context $Context.ReleasePython $Context.AppPath;Set-Phase $Context 'DEPLOY_HEALTH';$healthy=if($Context.Mode -eq 'SIMULATION'){(Get-ContextState $Context).process -eq 'new-healthy'}else{Invoke-HealthCheck 8502 60};if(-not$healthy){throw 'NEW_PRODUCTION_HEALTH_FAILED'};if($Context.Mode -eq 'PRODUCTION'){$listener=Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8502 -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1;if(-not$listener -or $listener.OwningProcess -ne $new.Id){throw 'NEW_PROCESS_IDENTITY_FAILED'};Test-8502ProcessIdentity $listener (Get-CimInstance Win32_Process -Filter ('ProcessId='+$listener.OwningProcess)) $Context.AppPath;Assert-CurrentLaunchLogs $new};if($Context.Mode -eq 'SIMULATION'){Assert-CurrentLaunchLogs $new};Write-ActiveRuntime $Context $new.Id;Set-Phase $Context 'DEPLOY_TASKS';Invoke-TaskConfigurationCore $Context -Execute;Set-Phase $Context 'DEPLOY_RECEIPT';Add-Mutation $Context 'DEPLOY_RECEIPT';Write-AtomicJson (Join-Path $Context.Root 'DEPLOYMENT_RECEIPT.json') ([ordered]@{old_head=$Context.ExpectedOldHead;new_head=$Context.ExpectedReleaseHead;new_pid=$new.Id;sql_migration_count=3;dynamic_artifact_count=6;health='PASS'});Write-KV 'DEPLOY_RESULT' 'PASS';return}catch{if($stopped){$Context.RollbackAttempted=$true;Write-KV 'AUTO_ROLLBACK_ATTEMPTED' 'YES';try{Invoke-RollbackCore $Context -Execute -Automatic;$Context.RollbackSucceeded=$true;$Context.StateRestored=$true;Write-KV 'AUTO_ROLLBACK_RESULT' 'PASS';Write-KV 'STATE_RESTORED' 'YES'}catch{Write-KV 'AUTO_ROLLBACK_RESULT' 'FAIL';Write-KV 'ROLLBACK_FAILURE' $_.Exception.Message}};throw}
}
function Invoke-RollbackCore {
    param([object]$Context,[switch]$Execute,[switch]$Automatic)
    Assert-Context $Context;if(-not$Execute){Write-KV 'MODE' 'DRY_RUN';Write-KV 'ROLLBACK_PLAN' 'PASS';Write-KV 'DB_SCHEMA_ROLLBACK' 'NOT_AUTOMATIC';Write-KV 'REMOTE_MAIN_ROLLBACK' 'NOT_AUTOMATIC';Write-KV 'MUTATION_EXECUTED' 'NO';return};Set-Phase $Context 'ROLLBACK_VALIDATE';$backup=Read-BackupManifest $Context.BackupManifest $Context;Add-Mutation $Context 'ROLLBACK_BEGIN';$manifest=$backup.Manifest
    Stop-RollbackProcess $Context;Invoke-ContextGitReset $Context ([string]$manifest.old_git_head);Set-Phase $Context 'ROLLBACK_ENV';Copy-Item (Join-Path $backup.Base $manifest.env_backup_relative_path) $Context.EnvPath -Force;if((Get-Sha256 $Context.EnvPath) -ne [string]$manifest.env_sha256){throw 'ROLLBACK_ENV_HASH_MISMATCH'};Set-Phase $Context 'ROLLBACK_ARTIFACTS';foreach($artifact in @($manifest.dynamic_artifacts)){$target=(Get-DynamicArtifactDefinitions $Context|Where-Object RelativePath -eq $artifact.relative_path).Path;if($artifact.existed_before){Copy-Item (Join-Path $backup.Base $artifact.backup_relative_path) $target -Force;if((Get-Sha256 $target) -ne [string]$artifact.sha256_before){throw 'ROLLBACK_ARTIFACT_STATE_MISMATCH'}}elseif(Test-Path $target -PathType Leaf){Remove-Item -LiteralPath $target -Force}};Set-Phase $Context 'ROLLBACK_TASKS';if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;$state.tasks=@{};foreach($task in @($manifest.production_refresh_tasks)){if($task.existed_before){$state.tasks[$task.task_name]=$task.state}};Save-ContextState $Context $state}else{foreach($name in $script:ManagedTasks){$entry=@($manifest.production_refresh_tasks|Where-Object task_name -eq $name)[0];$existing=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue;if($entry.existed_before){Register-ScheduledTask -TaskName $name -Xml (Get-Content (Join-Path $backup.Base $entry.exported_xml_relative_path) -Raw) -Force|Out-Null}elseif($existing){Unregister-ScheduledTask -TaskName $name -Confirm:$false}}};Set-Phase $Context 'ROLLBACK_RUNTIME';$active=Join-Path $Context.RuntimeRoot 'ACTIVE_RUNTIME.json';if($manifest.active_runtime_existed){Copy-Item (Join-Path $backup.Base $manifest.active_runtime_backup_relative_path) $active -Force}elseif(Test-Path $active -PathType Leaf){Remove-Item -LiteralPath $active -Force};Set-Phase $Context 'ROLLBACK_START';$oldPython=if($manifest.old_process_executable -and $manifest.old_process_executable -ne 'simulation'){$manifest.old_process_executable}else{$Context.ReleasePython};$oldStart=Start-ContextProcess $Context $oldPython $Context.AppPath -Old;Set-Phase $Context 'ROLLBACK_HEALTH';if($Context.Mode -eq 'PRODUCTION' -and -not(Invoke-HealthCheck 8502 60)){throw 'ROLLBACK_OLD_APP_HEALTH_FAILED'};Assert-CurrentLaunchLogs $oldStart;Write-KV 'DB_SCHEMA_ROLLBACK' 'NOT_AUTOMATIC';Write-KV 'REMOTE_MAIN_ROLLBACK' 'NOT_AUTOMATIC';Write-KV 'ROLLBACK_RESULT' 'PASS';$Context.StateRestored=$true
}
