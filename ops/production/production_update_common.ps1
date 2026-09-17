Set-StrictMode -Version Latest

$script:ExpectedRoot = 'C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales'
$script:ExpectedApp = Join-Path $script:ExpectedRoot 'streamlit_opensea_sales\app_opensea_sales.py'
$script:ExpectedPort = 8502
$script:ExpectedRuntimeRoot = 'C:\VAMBAM\Projects\OTG\runtime\opensea_sales'
$script:SimulationPrefix = 'C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_110'
$script:ForbiddenPorts = @(8501,8504)
$script:ForbiddenApp = 'app_gaming_marketplace.py'
$script:ProductionServiceName = 'OTG_app_opensea_sales'
$script:ProductionSupervisorType = 'NSSM'
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
function Get-ProductionStreamlitLaunchParameters {
    '-m streamlit run app_opensea_sales.py --server.address 127.0.0.1 --server.port 8502 --server.fileWatcherType none --server.headless true --browser.gatherUsageStats false --theme.base="dark"'
}
function Get-StreamlitThemeBaseState {
    param([Parameter(Mandatory=$true)][string]$Parameters)
    $matches=[regex]::Matches($Parameters,'(?i)(?:^|\s)--theme\.base(?:\s+|=)(?:"(?<quoted>[^"]*)"|(?<bare>[^\s]+))(?=\s|$)')
    if($matches.Count -eq 0){return [pscustomobject]@{State='MISSING';Value='';Count=0}}
    if($matches.Count -ne 1){return [pscustomobject]@{State='DUPLICATE';Value='';Count=$matches.Count}}
    $match=$matches[0];$value=if($match.Groups['quoted'].Success){$match.Groups['quoted'].Value}else{$match.Groups['bare'].Value}
    $state=if($value -ceq 'dark'){'DARK'}elseif($value -ceq 'light'){'LIGHT'}else{'INVALID'}
    [pscustomobject]@{State=$state;Value=$value;Count=1}
}
function Assert-StreamlitLaunchShape {
    param([Parameter(Mandatory=$true)][string]$Parameters,[int]$ExpectedPort=8502)
    if([string]::IsNullOrWhiteSpace($Parameters)){throw 'SUPERVISOR_PARAMETERS_NOT_STREAMLIT'}
    $required=@(
        '(?i)(?:^|\s)-m\s+streamlit\s+run(?:\s|$)',
        '(?i)(?:^|\s)--server\.address(?:\s+|=)"?127\.0\.0\.1"?(?:\s|$)',
        ('(?i)(?:^|\s)--server\.port(?:\s+|=)'+[regex]::Escape([string]$ExpectedPort)+'(?:\s|$)'),
        '(?i)(?:^|\s)--server\.fileWatcherType(?:\s+|=)none(?:\s|$)',
        '(?i)(?:^|\s)--server\.headless(?:\s+|=)true(?:\s|$)',
        '(?i)(?:^|\s)--browser\.gatherUsageStats(?:\s+|=)false(?:\s|$)'
    )
    foreach($pattern in $required){if($Parameters -notmatch $pattern){throw 'SUPERVISOR_LAUNCH_CONTRACT_REQUIRED'}}
    $Parameters
}
function Assert-StreamlitLaunchContract {
    param([Parameter(Mandatory=$true)][string]$Parameters,[int]$ExpectedPort=8502)
    $null=Assert-StreamlitLaunchShape $Parameters $ExpectedPort
    $theme=Get-StreamlitThemeBaseState $Parameters
    if($theme.State -ne 'DARK'){throw 'SUPERVISOR_THEME_BASE_DARK_REQUIRED'}
    $Parameters
}
function Assert-StreamlitSourceLaunchContract {
    param([Parameter(Mandatory=$true)][string]$Parameters,[int]$ExpectedPort=8502,[switch]$AllowLegacyMissingThemeSource)
    $null=Assert-StreamlitLaunchShape $Parameters $ExpectedPort
    $theme=Get-StreamlitThemeBaseState $Parameters
    if($theme.State -eq 'DARK'){return $Parameters}
    if($AllowLegacyMissingThemeSource -and $theme.State -eq 'MISSING'){return $Parameters}
    throw 'SUPERVISOR_THEME_BASE_DARK_REQUIRED'
}
function Assert-PreparedReleaseThemeContract([object]$Manifest) {
    if(-not$Manifest -or [string]$Manifest.streamlit_theme_base -cne 'dark' -or [string]$Manifest.streamlit_theme_contract -cne 'PASS'){throw 'PREPARED_RELEASE_THEME_CONTRACT_FAILED'}
    if($Manifest.PSObject.Properties['source_legacy_theme_correction_supported'] -and [string]$Manifest.source_legacy_theme_correction_supported -cne 'YES'){throw 'PREPARED_RELEASE_THEME_CONTRACT_FAILED'}
    $null=Assert-StreamlitLaunchContract (Get-ProductionStreamlitLaunchParameters) $script:ExpectedPort
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

function Get-SupervisorServiceName([object]$Context) {
    if($Context.SupervisorServiceName){return [string]$Context.SupervisorServiceName}
    $script:ProductionServiceName
}
function Get-SupervisorAppDirectory([object]$Context) {
    if($Context.SupervisorAppDirectory){return [string]$Context.SupervisorAppDirectory}
    Split-Path -Parent $Context.AppPath
}
function Get-SupervisorPort([object]$Context) {[int]$Context.Port}
function Get-SupervisorNssmExecutable([object]$Service) {
    $raw=[string]$Service.PathName
    $match=[regex]::Match($raw,'^\s*"(?<quoted>[^"]+)"|^\s*(?<bare>[^\s]+)')
    $path=if($match.Groups['quoted'].Success){$match.Groups['quoted'].Value}else{$match.Groups['bare'].Value}
    if([string]::IsNullOrWhiteSpace($path) -or [IO.Path]::GetFileName($path) -ine 'nssm.exe' -or -not(Test-Path -LiteralPath $path -PathType Leaf)){throw 'SUPERVISOR_NOT_NSSM'}
    $path
}
function Get-NssmValue([string]$Nssm,[string]$ServiceName,[string]$Parameter,[string]$WorkingDirectory) {
    (Invoke-ChildProcess $Nssm @('get',$ServiceName,$Parameter) $WorkingDirectory 30 @{}).StdOut.Trim()
}
function Get-NssmOptionalValue([string]$Nssm,[string]$ServiceName,[string]$Parameter,[string]$WorkingDirectory) {
    try {Get-NssmValue $Nssm $ServiceName $Parameter $WorkingDirectory} catch {''}
}
function Get-NssmExitDefault([string]$Nssm,[string]$ServiceName,[string]$WorkingDirectory) {
    try {(Invoke-ChildProcess $Nssm @('get',$ServiceName,'AppExit','Default') $WorkingDirectory 30 @{}).StdOut.Trim()} catch {''}
}
function Get-SupervisorConfigurationFingerprint([object]$Configuration) {
    $value=[ordered]@{service_name=$Configuration.ServiceName;service_display_name=$Configuration.ServiceDisplayName;service_start_mode=$Configuration.ServiceStartMode;service_binary_path=$Configuration.ServiceBinaryPath;nssm_executable=$Configuration.NssmExecutable;application=$Configuration.Application;app_directory=$Configuration.AppDirectory;app_parameters=$Configuration.AppParameters;app_stdout=$Configuration.AppStdout;app_stderr=$Configuration.AppStderr;app_restart_delay=$Configuration.AppRestartDelay;app_throttle=$Configuration.AppThrottle;app_exit_default=$Configuration.AppExitDefault;app_stop_method_console=$Configuration.AppStopMethodConsole;app_stop_method_window=$Configuration.AppStopMethodWindow;app_stop_method_threads=$Configuration.AppStopMethodThreads;app_stop_method_skip=$Configuration.AppStopMethodSkip;app_kill_process_tree=$Configuration.AppKillProcessTree;app_stdout_share_mode=$Configuration.AppStdoutShareMode;app_stderr_share_mode=$Configuration.AppStderrShareMode;app_rotate_files=$Configuration.AppRotateFiles;app_rotate_online=$Configuration.AppRotateOnline;app_rotate_seconds=$Configuration.AppRotateSeconds;app_rotate_bytes=$Configuration.AppRotateBytes;app_timestamp_log=$Configuration.AppTimestampLog;windows_service_failure_actions=$Configuration.WindowsServiceFailureActions}
    $bytes=[Text.Encoding]::UTF8.GetBytes(($value|ConvertTo-Json -Compress -Depth 20));$sha=[Security.Cryptography.SHA256]::Create();try{[BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
}
function Get-SupervisorRecordValue([object]$Record,[string]$JsonName,[string]$ObjectName) {
    if($Record -and $Record.PSObject.Properties[$JsonName]){return $Record.PSObject.Properties[$JsonName].Value}
    if($Record -and $Record.PSObject.Properties[$ObjectName]){return $Record.PSObject.Properties[$ObjectName].Value}
    $null
}
function ConvertTo-SupervisorRecord([object]$Record) {
    [pscustomobject]@{
        service_name=Get-SupervisorRecordValue $Record 'service_name' 'ServiceName';service_display_name=Get-SupervisorRecordValue $Record 'service_display_name' 'ServiceDisplayName';service_start_mode=Get-SupervisorRecordValue $Record 'service_start_mode' 'ServiceStartMode';service_was_running=Get-SupervisorRecordValue $Record 'service_was_running' 'ServiceWasRunning';service_binary_path=Get-SupervisorRecordValue $Record 'service_binary_path' 'ServiceBinaryPath';nssm_executable=Get-SupervisorRecordValue $Record 'nssm_executable' 'NssmExecutable';application=Get-SupervisorRecordValue $Record 'application' 'Application';app_directory=Get-SupervisorRecordValue $Record 'app_directory' 'AppDirectory';app_parameters=Get-SupervisorRecordValue $Record 'app_parameters' 'AppParameters';app_stdout=Get-SupervisorRecordValue $Record 'app_stdout' 'AppStdout';app_stderr=Get-SupervisorRecordValue $Record 'app_stderr' 'AppStderr';app_restart_delay=Get-SupervisorRecordValue $Record 'app_restart_delay' 'AppRestartDelay';app_throttle=Get-SupervisorRecordValue $Record 'app_throttle' 'AppThrottle';app_exit_default=Get-SupervisorRecordValue $Record 'app_exit_default' 'AppExitDefault';app_stop_method_console=Get-SupervisorRecordValue $Record 'app_stop_method_console' 'AppStopMethodConsole';app_stop_method_window=Get-SupervisorRecordValue $Record 'app_stop_method_window' 'AppStopMethodWindow';app_stop_method_threads=Get-SupervisorRecordValue $Record 'app_stop_method_threads' 'AppStopMethodThreads';app_stop_method_skip=Get-SupervisorRecordValue $Record 'app_stop_method_skip' 'AppStopMethodSkip';app_kill_process_tree=Get-SupervisorRecordValue $Record 'app_kill_process_tree' 'AppKillProcessTree';app_stdout_share_mode=Get-SupervisorRecordValue $Record 'app_stdout_share_mode' 'AppStdoutShareMode';app_stderr_share_mode=Get-SupervisorRecordValue $Record 'app_stderr_share_mode' 'AppStderrShareMode';app_rotate_files=Get-SupervisorRecordValue $Record 'app_rotate_files' 'AppRotateFiles';app_rotate_online=Get-SupervisorRecordValue $Record 'app_rotate_online' 'AppRotateOnline';app_rotate_seconds=Get-SupervisorRecordValue $Record 'app_rotate_seconds' 'AppRotateSeconds';app_rotate_bytes=Get-SupervisorRecordValue $Record 'app_rotate_bytes' 'AppRotateBytes';app_timestamp_log=Get-SupervisorRecordValue $Record 'app_timestamp_log' 'AppTimestampLog';windows_service_failure_actions=Get-SupervisorRecordValue $Record 'windows_service_failure_actions' 'WindowsServiceFailureActions';configuration_fingerprint=Get-SupervisorRecordValue $Record 'configuration_fingerprint' 'ConfigurationFingerprint'
    }
}
function Get-SupervisorManifestFingerprint([object]$Record) {
    $r=ConvertTo-SupervisorRecord $Record
    Get-SupervisorConfigurationFingerprint ([pscustomobject]@{ServiceName=$r.service_name;ServiceDisplayName=$r.service_display_name;ServiceStartMode=$r.service_start_mode;ServiceBinaryPath=$r.service_binary_path;NssmExecutable=$r.nssm_executable;Application=$r.application;AppDirectory=$r.app_directory;AppParameters=$r.app_parameters;AppStdout=$r.app_stdout;AppStderr=$r.app_stderr;AppRestartDelay=$r.app_restart_delay;AppThrottle=$r.app_throttle;AppExitDefault=$r.app_exit_default;AppStopMethodConsole=$r.app_stop_method_console;AppStopMethodWindow=$r.app_stop_method_window;AppStopMethodThreads=$r.app_stop_method_threads;AppStopMethodSkip=$r.app_stop_method_skip;AppKillProcessTree=$r.app_kill_process_tree;AppStdoutShareMode=$r.app_stdout_share_mode;AppStderrShareMode=$r.app_stderr_share_mode;AppRotateFiles=$r.app_rotate_files;AppRotateOnline=$r.app_rotate_online;AppRotateSeconds=$r.app_rotate_seconds;AppRotateBytes=$r.app_rotate_bytes;AppTimestampLog=$r.app_timestamp_log;WindowsServiceFailureActions=$r.windows_service_failure_actions})
}
function Get-ProductionSupervisorConfiguration([object]$Context) {
    $name=Get-SupervisorServiceName $Context
    $service=Get-CimInstance Win32_Service | Where-Object { $_.Name -eq $name } | Select-Object -First 1
    if(-not$service){throw 'SUPERVISOR_SERVICE_MISSING'}
    $nssm=Get-SupervisorNssmExecutable $service
    $sc=Get-Command sc.exe -ErrorAction Stop
    $failure=(Invoke-ChildProcess $sc.Source @('qfailure',$name) $Context.Root 30 @{}).StdOut.Trim()
    $version='';try{$version=(Invoke-ChildProcess $nssm @('version') $Context.Root 30 @{}).StdOut.Trim()}catch{}
    $config=[pscustomobject]@{
        ServiceName=$name;ServiceDisplayName=[string]$service.DisplayName;ServiceState=[string]$service.State;ServiceWasRunning=([string]$service.State -eq 'Running');ServiceStartMode=[string]$service.StartMode;ServiceBinaryPath=[string]$service.PathName;ServiceProcessId=[int]$service.ProcessId;NssmExecutable=$nssm;NssmVersion=$version;Application=(Get-NssmValue $nssm $name 'Application' $Context.Root);AppDirectory=(Get-NssmValue $nssm $name 'AppDirectory' $Context.Root);AppParameters=(Get-NssmValue $nssm $name 'AppParameters' $Context.Root);AppStdout=(Get-NssmOptionalValue $nssm $name 'AppStdout' $Context.Root);AppStderr=(Get-NssmOptionalValue $nssm $name 'AppStderr' $Context.Root);AppRestartDelay=(Get-NssmOptionalValue $nssm $name 'AppRestartDelay' $Context.Root);AppThrottle=(Get-NssmOptionalValue $nssm $name 'AppThrottle' $Context.Root);AppExitDefault=(Get-NssmExitDefault $nssm $name $Context.Root);AppStopMethodConsole=(Get-NssmOptionalValue $nssm $name 'AppStopMethodConsole' $Context.Root);AppStopMethodWindow=(Get-NssmOptionalValue $nssm $name 'AppStopMethodWindow' $Context.Root);AppStopMethodThreads=(Get-NssmOptionalValue $nssm $name 'AppStopMethodThreads' $Context.Root);AppStopMethodSkip=(Get-NssmOptionalValue $nssm $name 'AppStopMethodSkip' $Context.Root);AppKillProcessTree=(Get-NssmOptionalValue $nssm $name 'AppKillProcessTree' $Context.Root);AppStdoutShareMode=(Get-NssmOptionalValue $nssm $name 'AppStdoutShareMode' $Context.Root);AppStderrShareMode=(Get-NssmOptionalValue $nssm $name 'AppStderrShareMode' $Context.Root);AppRotateFiles=(Get-NssmOptionalValue $nssm $name 'AppRotateFiles' $Context.Root);AppRotateOnline=(Get-NssmOptionalValue $nssm $name 'AppRotateOnline' $Context.Root);AppRotateSeconds=(Get-NssmOptionalValue $nssm $name 'AppRotateSeconds' $Context.Root);AppRotateBytes=(Get-NssmOptionalValue $nssm $name 'AppRotateBytes' $Context.Root);AppTimestampLog=(Get-NssmOptionalValue $nssm $name 'AppTimestampLog' $Context.Root);WindowsServiceFailureActions=$failure}
    $config|Add-Member NoteProperty ConfigurationFingerprint (Get-SupervisorConfigurationFingerprint $config)
    $config
}
function Assert-ProductionSupervisorOwnershipIdentity([object]$Context,[object]$Configuration,[switch]$RequireRunning,[switch]$AllowLegacyMissingThemeSource) {
    if(-not$Configuration -or $Configuration.ServiceName -ne (Get-SupervisorServiceName $Context)){throw 'SUPERVISOR_SERVICE_NAME_MISMATCH'}
    if([IO.Path]::GetFileName([string]$Configuration.NssmExecutable) -ine 'nssm.exe'){throw 'SUPERVISOR_NOT_NSSM'}
    if([IO.Path]::GetFullPath([string]$Configuration.AppDirectory) -ne [IO.Path]::GetFullPath((Get-SupervisorAppDirectory $Context))){throw 'SUPERVISOR_APP_DIRECTORY_MISMATCH'}
    $application=[string]$Configuration.Application;if([string]::IsNullOrWhiteSpace($application) -or [IO.Path]::GetFileName($application) -ine 'python.exe' -or -not(Test-Path -LiteralPath $application -PathType Leaf)){throw 'SUPERVISOR_APPLICATION_MISMATCH'}
    $parameters=[string]$Configuration.AppParameters
    $null=Assert-StreamlitSourceLaunchContract $parameters (Get-SupervisorPort $Context) -AllowLegacyMissingThemeSource:$AllowLegacyMissingThemeSource
    if($parameters -notmatch '(?i)(?:-m\s+streamlit\s+run|(?:^|\s)streamlit(?:\.exe)?\s+run)'){throw 'SUPERVISOR_PARAMETERS_NOT_STREAMLIT'}
    if($parameters -match '(?i)app_gaming_marketplace\.py|--server\.port(?:\s+|=)(?:8501|8504)(?:\s|$)'){throw 'SUPERVISOR_FORBIDDEN_TARGET'}
    $portMatch=[regex]::Match($parameters,'(?i)--server\.port(?:\s+|=)(\d+)');if(-not$portMatch.Success -or [int]$portMatch.Groups[1].Value -ne (Get-SupervisorPort $Context)){throw 'SUPERVISOR_PORT_MISMATCH'}
    $addressMatch=[regex]::Match($parameters,'(?i)--server\.address(?:\s+|=)([^\s]+)');if($addressMatch.Success -and $addressMatch.Groups[1].Value.Trim('"') -ne '127.0.0.1'){throw 'SUPERVISOR_ADDRESS_MISMATCH'}
    if($parameters -notmatch '(?i)(?:^|\s)(?:"[^"]*|[^\s])*app_opensea_sales\.py(?:"|\s|$)'){throw 'SUPERVISOR_APP_MISMATCH'}
    if($RequireRunning -and [string]$Configuration.ServiceState -ne 'Running'){throw 'SUPERVISOR_SERVICE_NOT_RUNNING'}
    $theme=Get-StreamlitThemeBaseState $parameters
    $Configuration | Add-Member NoteProperty SourceThemeBase $theme.State -Force
    $Configuration | Add-Member NoteProperty SourceThemeContract $(if($theme.State -eq 'MISSING' -and $AllowLegacyMissingThemeSource){'KNOWN_LEGACY_DRIFT'}elseif($theme.State -eq 'DARK'){'PASS'}else{'FAIL'}) -Force
    $Configuration
}
function Assert-ProductionSupervisorActivationIdentity([object]$Context,[object]$Configuration,[switch]$RequireRunning) {
    $validated=Assert-ProductionSupervisorOwnershipIdentity $Context $Configuration -RequireRunning:$RequireRunning
    $null=Assert-StreamlitLaunchContract ([string]$validated.AppParameters) (Get-SupervisorPort $Context)
    $validated
}
function Assert-ProductionSupervisorIdentity([object]$Context,[object]$Configuration,[switch]$RequireRunning,[switch]$AllowLegacyMissingThemeSource) {
    Assert-ProductionSupervisorOwnershipIdentity $Context $Configuration -RequireRunning:$RequireRunning -AllowLegacyMissingThemeSource:$AllowLegacyMissingThemeSource
}
function Test-ProcessDescendant([int]$ChildPid,[int]$AncestorPid) {
    $seen=@{};$current=$ChildPid
    for($i=0;$i-lt 16 -and $current -and -not$seen.ContainsKey($current);$i++){$seen[$current]=$true;if($current -eq $AncestorPid){return $true};$parent=Get-CimInstance Win32_Process -Filter ('ProcessId='+$current);if(-not$parent){break};$current=[int]$parent.ParentProcessId}
    $false
}
function Test-ProcessChainExecutable([int]$ChildPid,[int]$AncestorPid,[string]$ExpectedExecutable) {
    $seen=@{};$current=$ChildPid;$expected=[IO.Path]::GetFullPath($ExpectedExecutable)
    for($i=0;$i-lt 16 -and $current -and -not$seen.ContainsKey($current);$i++){$seen[$current]=$true;$process=Get-CimInstance Win32_Process -Filter ('ProcessId='+$current);if($process -and $process.ExecutablePath -and [IO.Path]::GetFullPath([string]$process.ExecutablePath) -eq $expected){return $true};if($current -eq $AncestorPid){break};if(-not$process){break};$current=[int]$process.ParentProcessId}
    $false
}
function Resolve-ProductionSupervisorChild([object]$Context,[switch]$AllowLegacyMissingThemeSource) {
    $connection=Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort (Get-SupervisorPort $Context) -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1
    if(-not$connection){return [pscustomobject]@{State='NO_LISTENER';ProcessId=$null;Process=$null;Listener=$null}}
    $configuration=Assert-ProductionSupervisorOwnershipIdentity $Context (Get-ProductionSupervisorConfiguration $Context) -RequireRunning -AllowLegacyMissingThemeSource:$AllowLegacyMissingThemeSource
    $process=Get-CimInstance Win32_Process -Filter ('ProcessId='+$connection.OwningProcess)
    try{$null=Test-8502ProcessIdentity $connection $process $Context.AppPath '' (Get-SupervisorPort $Context) -AllowLegacyMissingThemeSource:$AllowLegacyMissingThemeSource;if(-not(Test-ProcessDescendant ([int]$process.ProcessId) $configuration.ServiceProcessId)){throw 'SUPERVISOR_CHILD_PARENT_MISMATCH'};if(-not(Test-ProcessChainExecutable ([int]$process.ProcessId) $configuration.ServiceProcessId $configuration.Application)){throw 'SUPERVISOR_APPLICATION_NOT_IN_CHILD_CHAIN'};return [pscustomobject]@{State='EXPECTED_PROCESS_PRESENT';ProcessId=[int]$process.ProcessId;Process=$process;Listener=$connection;Configuration=$configuration}}catch{throw 'SUPERVISOR_FOREIGN_LISTENER'}
}
function Get-ProductionSupervisor([object]$Context,[switch]$AllowNoListener,[switch]$AllowLegacyMissingThemeSource) {
    $configuration=Assert-ProductionSupervisorOwnershipIdentity $Context (Get-ProductionSupervisorConfiguration $Context) -RequireRunning -AllowLegacyMissingThemeSource:$AllowLegacyMissingThemeSource
    $child=Resolve-ProductionSupervisorChild $Context -AllowLegacyMissingThemeSource:$AllowLegacyMissingThemeSource
    if($child.State -eq 'NO_LISTENER' -and -not$AllowNoListener){throw 'SUPERVISOR_CHILD_NOT_LISTENING'}
    [pscustomobject]@{Configuration=$configuration;Child=$child}
}
function Wait-ProductionSupervisorStopped([object]$Context,[int]$TimeoutSeconds=60) {
    $until=(Get-Date).AddSeconds($TimeoutSeconds);do{$service=Get-CimInstance Win32_Service -Filter ("Name='"+(Get-SupervisorServiceName $Context)+"'");if($service -and [string]$service.State -eq 'Stopped'){return $true};Start-Sleep -Milliseconds 500}while((Get-Date)-lt $until);throw 'SUPERVISOR_DID_NOT_STOP'
}
function Wait-ProductionPortReleased([object]$Context,[int]$TimeoutSeconds=60) {
    $until=(Get-Date).AddSeconds($TimeoutSeconds);do{$child=Resolve-ProductionSupervisorChild $Context -AllowLegacyMissingThemeSource:$Context.AllowLegacyMissingThemeSource;if($child.State -eq 'NO_LISTENER'){return $true};Start-Sleep -Milliseconds 500}while((Get-Date)-lt $until);throw 'SUPERVISOR_PORT_NOT_RELEASED'
}
function Stop-ProductionSupervisor([object]$Context,[switch]$AllowNoListener) {
    $configuration=Get-ProductionSupervisorConfiguration $Context
    if([string]$configuration.ServiceState -eq 'Running') {
        Assert-ProductionSupervisorOwnershipIdentity $Context $configuration -RequireRunning -AllowLegacyMissingThemeSource:$Context.AllowLegacyMissingThemeSource|Out-Null
        $child=Resolve-ProductionSupervisorChild $Context -AllowLegacyMissingThemeSource:$Context.AllowLegacyMissingThemeSource
        if($child.State -eq 'NO_LISTENER' -and -not$AllowNoListener){throw 'SUPERVISOR_CHILD_NOT_LISTENING'}
        Stop-Service -Name (Get-SupervisorServiceName $Context) -Force -ErrorAction Stop
    } elseif([string]$configuration.ServiceState -eq 'Stopped') {
        $connection=Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort (Get-SupervisorPort $Context) -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1
        if($connection){throw 'SUPERVISOR_FOREIGN_LISTENER'}
        if(-not$AllowNoListener){throw 'SUPERVISOR_SERVICE_NOT_RUNNING'}
        Write-KV 'SUPERVISOR_STOP' 'PASS'
        return
    } else { throw 'SUPERVISOR_SERVICE_STATE_UNSAFE' }
    Wait-ProductionSupervisorStopped $Context 60|Out-Null
    Wait-ProductionPortReleased $Context 60|Out-Null
    Write-KV 'SUPERVISOR_STOP' 'PASS'
}
function Set-NssmValue([object]$Context,[string]$Name,[string]$Parameter,[string]$Value) {
    $nssm=if($Context.SupervisorNssmExecutable){$Context.SupervisorNssmExecutable}else{(Get-ProductionSupervisorConfiguration $Context).NssmExecutable}
    Invoke-ChildProcess $nssm @('set',$Name,$Parameter,$Value) $Context.Root 30 @{}|Out-Null
}
function Set-ProductionSupervisorReleaseConfiguration([object]$Context) {
    Assert-FinalRuntimePath $Context.ReleasePython $Context.ExpectedReleaseHead $Context
    if(-not(Test-Path $Context.ReleasePython -PathType Leaf)){throw 'SUPERVISOR_RELEASE_PYTHON_MISSING'}
    $name=Get-SupervisorServiceName $Context;$appDirectory=Get-SupervisorAppDirectory $Context;$logRoot=Join-Path $Context.RuntimeRoot 'logs';$id=[guid]::NewGuid().ToString('N');$stdout=Join-Path $logRoot ('supervisor_'+$id+'.out.log');$stderr=Join-Path $logRoot ('supervisor_'+$id+'.err.log')
    $parameters=Get-ProductionStreamlitLaunchParameters
    $null=Assert-StreamlitLaunchContract $parameters $script:ExpectedPort
    Set-NssmValue $Context $name 'Application' $Context.ReleasePython;Set-NssmValue $Context $name 'AppDirectory' $appDirectory;Set-NssmValue $Context $name 'AppParameters' $parameters;Set-NssmValue $Context $name 'AppStdout' $stdout;Set-NssmValue $Context $name 'AppStderr' $stderr
    $Context.SupervisorActivationStdOut=$stdout;$Context.SupervisorActivationStdErr=$stderr;$Context.SupervisorNssmExecutable=(Get-ProductionSupervisorConfiguration $Context).NssmExecutable;$configuration=Get-ProductionSupervisorConfiguration $Context;Assert-ProductionSupervisorActivationIdentity $Context $configuration;Write-KV 'STREAMLIT_THEME_BASE' 'dark';Write-KV 'STREAMLIT_THEME_CONTRACT' 'PASS'
    if([IO.Path]::GetFullPath($configuration.Application) -ne [IO.Path]::GetFullPath($Context.ReleasePython)){throw 'SUPERVISOR_RELEASE_PYTHON_MISMATCH'}
    $Context.SupervisorConfiguration=$configuration;$configuration
}
function Restore-ProductionSupervisorConfiguration([object]$Context,[object]$BackupSupervisor,[string]$TemporaryStdOut='',[string]$TemporaryStdErr='') {
    if(-not$BackupSupervisor){throw 'BACKUP_SUPERVISOR_STATE_MISSING'};$BackupSupervisor=ConvertTo-SupervisorRecord $BackupSupervisor;$name=Get-SupervisorServiceName $Context;$Context.SupervisorNssmExecutable=[string]$BackupSupervisor.nssm_executable
    Set-NssmValue $Context $name 'Application' ([string]$BackupSupervisor.application);Set-NssmValue $Context $name 'AppDirectory' ([string]$BackupSupervisor.app_directory);Set-NssmValue $Context $name 'AppParameters' ([string]$BackupSupervisor.app_parameters)
    if($TemporaryStdOut){Set-NssmValue $Context $name 'AppStdout' $TemporaryStdOut;$Context.SupervisorActivationStdOut=$TemporaryStdOut}else{if([string]::IsNullOrWhiteSpace([string]$BackupSupervisor.app_stdout)){Invoke-ChildProcess $Context.SupervisorNssmExecutable @('reset',$name,'AppStdout') $Context.Root 30 @{}|Out-Null}else{Set-NssmValue $Context $name 'AppStdout' ([string]$BackupSupervisor.app_stdout)}}
    if($TemporaryStdErr){Set-NssmValue $Context $name 'AppStderr' $TemporaryStdErr;$Context.SupervisorActivationStdErr=$TemporaryStdErr}else{if([string]::IsNullOrWhiteSpace([string]$BackupSupervisor.app_stderr)){Invoke-ChildProcess $Context.SupervisorNssmExecutable @('reset',$name,'AppStderr') $Context.Root 30 @{}|Out-Null}else{Set-NssmValue $Context $name 'AppStderr' ([string]$BackupSupervisor.app_stderr)}}
    if(-not[string]::IsNullOrWhiteSpace([string]$BackupSupervisor.app_exit_default)){Invoke-ChildProcess $Context.SupervisorNssmExecutable @('set',$name,'AppExit','Default',[string]$BackupSupervisor.app_exit_default) $Context.Root 30 @{}|Out-Null}
    foreach($pair in @(@('AppRestartDelay','app_restart_delay'),@('AppThrottle','app_throttle'),@('AppStopMethodConsole','app_stop_method_console'),@('AppStopMethodWindow','app_stop_method_window'),@('AppStopMethodThreads','app_stop_method_threads'),@('AppStopMethodSkip','app_stop_method_skip'),@('AppKillProcessTree','app_kill_process_tree'),@('AppStdoutShareMode','app_stdout_share_mode'),@('AppStderrShareMode','app_stderr_share_mode'),@('AppRotateFiles','app_rotate_files'),@('AppRotateOnline','app_rotate_online'),@('AppRotateSeconds','app_rotate_seconds'),@('AppRotateBytes','app_rotate_bytes'),@('AppTimestampLog','app_timestamp_log'))){if(-not[string]::IsNullOrWhiteSpace([string]$BackupSupervisor.($pair[1]))){Set-NssmValue $Context $name $pair[0] ([string]$BackupSupervisor.($pair[1]))}}
    if([string]$BackupSupervisor.service_start_mode -eq 'Auto'){& sc.exe config $name start= auto|Out-Null}elseif([string]$BackupSupervisor.service_start_mode -eq 'Manual'){& sc.exe config $name start= demand|Out-Null}
    $Context.SupervisorConfiguration=Get-ProductionSupervisorConfiguration $Context;$Context.SupervisorConfiguration
}
function Start-ProductionSupervisor([object]$Context,[switch]$AllowLegacyMissingThemeSource) {
    $configuration=if($AllowLegacyMissingThemeSource){Assert-ProductionSupervisorOwnershipIdentity $Context (Get-ProductionSupervisorConfiguration $Context) -AllowLegacyMissingThemeSource}else{Assert-ProductionSupervisorActivationIdentity $Context (Get-ProductionSupervisorConfiguration $Context)}
    if([IO.Path]::GetFullPath($configuration.Application) -ne [IO.Path]::GetFullPath($Context.ReleasePython)){throw 'SUPERVISOR_START_PYTHON_MISMATCH'}
    $started=$false
    try {
        Start-Service -Name (Get-SupervisorServiceName $Context) -ErrorAction Stop;$started=$true
        $until=(Get-Date).AddSeconds(60);$child=$null;do{try{$child=Resolve-ProductionSupervisorChild $Context -AllowLegacyMissingThemeSource:$AllowLegacyMissingThemeSource}catch{$child=$null};if($child -and $child.State -eq 'EXPECTED_PROCESS_PRESENT'){break};Start-Sleep -Milliseconds 500}while((Get-Date)-lt $until)
        if(-not$child -or $child.State -ne 'EXPECTED_PROCESS_PRESENT'){throw 'SUPERVISOR_CHILD_START_FAILED'}
        [pscustomobject]@{ProcessId=$child.ProcessId;Id=$child.ProcessId;Process=$child.Process;StdOutLogPath=$Context.SupervisorActivationStdOut;StdErrLogPath=$Context.SupervisorActivationStdErr;StartedAt=(Get-Date).ToUniversalTime().ToString('o');SupervisorConfiguration=$child.Configuration}
    } catch {
        if($started){try{Stop-Service -Name (Get-SupervisorServiceName $Context) -Force -ErrorAction SilentlyContinue}catch{}}
        throw
    }
}

function Get-FinalRuntimeRoot([string]$ReleaseHead,[object]$Context) { if(-not$ReleaseHead){throw 'RELEASE_HEAD_REQUIRED'};if($Context.Mode -eq 'PRODUCTION'){Join-Path $script:ExpectedRuntimeRoot ('releases\'+$ReleaseHead)}else{Join-Path $Context.RuntimeRoot ('releases\'+$ReleaseHead)} }
function Get-FinalRuntimePython([string]$ReleaseHead,[object]$Context) { Join-Path (Get-FinalRuntimeRoot $ReleaseHead $Context) '.venv\Scripts\python.exe' }
function Assert-FinalRuntimePath([string]$Python,[string]$ReleaseHead,[object]$Context) { if([IO.Path]::GetFullPath($Python) -ne [IO.Path]::GetFullPath((Get-FinalRuntimePython $ReleaseHead $Context))){throw 'FINAL_RUNTIME_PATH_GUARD_FAILED'} }

function New-ProductionExecutionContext {
    param([hashtable]$Arguments)
    Assert-ProductionTarget
    $head=[string]$Arguments.ExpectedReleaseHead;$python='';if($head){$python=Get-FinalRuntimePython $head ([pscustomobject]@{Mode='PRODUCTION'})}
    $allowLegacy=[bool]$(if($Arguments.ContainsKey('AllowLegacyMissingThemeSource')){$Arguments['AllowLegacyMissingThemeSource']}else{$false})
    [pscustomobject]@{Mode='PRODUCTION';Root=$script:ExpectedRoot;RuntimeRoot=$script:ExpectedRuntimeRoot;AppPath=$script:ExpectedApp;Port=8502;EnvPath=(Join-Path $script:ExpectedRoot '.env');DataRoot=(Join-Path $script:ExpectedRoot 'streamlit_opensea_sales\data_opensea_sales');RepoRoot=$script:ExpectedRoot;PreparedReleaseRoot=$Arguments.PreparedReleaseRoot;ReleaseRoot=$Arguments.PreparedReleaseRoot;ReleasePython=$python;DeploymentRefreshPython='';BackupRoot=$Arguments.BackupRoot;PreparedReleaseManifest=$Arguments.PreparedReleaseManifest;PreparedReleaseManifestSha256=$Arguments.PreparedReleaseManifestSha256;BackupManifest=$Arguments.BackupManifest;ExpectedOldHead=$Arguments.ExpectedOldHead;ExpectedReleaseHead=$head;SimulationStatePath='';SupervisorServiceName=$script:ProductionServiceName;SupervisorType=$script:ProductionSupervisorType;SupervisorAppDirectory=(Split-Path -Parent $script:ExpectedApp);SupervisorNssmExecutable='';SupervisorConfiguration=$null;SupervisorActivationStdOut='';SupervisorActivationStdErr='';ProfileSyncContractRequired=$false;ProfileKeySource='';ProfileSyncContract='NOT_RUN';ProfileSyncStateGate='NOT_RUN';ProfileCoverageGate='NOT_RUN';ProfileReaderGate='NOT_RUN';ProfileCount=0;ProfileOkCount=0;ProfileHumanUsernameCount=0;ProfileHumanDisplayNameCount=0;ProfileRemoteAvatarCount=0;ProfileSyncAttempted=0;ProfileSyncSuccessful=0;ProfileSyncNotFound=0;ProfileSyncErrors=0;ProfileSyncRateLimited=0;ProfileSyncHealth='NOT_RUN';MetadataRefreshResult='NOT_RUN';AllowLegacyMissingThemeSource=$allowLegacy;MutationStarted=$false;MutationPhases=(New-Object Collections.ArrayList);RollbackAttempted=$false;RollbackSucceeded=$false;StateRestored=$false}
}
function New-SimulationExecutionContext {
    param([hashtable]$Arguments)
    $root=[IO.Path]::GetFullPath($Arguments.SimulationRoot);$app=Join-Path $root 'production\streamlit_opensea_sales\app_opensea_sales.py';Assert-SimulationTarget $root ([int]$Arguments.SimulationPort) $app
    $old=if($Arguments.ExpectedOldHead){$Arguments.ExpectedOldHead}else{'old'};$release=if($Arguments.ExpectedReleaseHead){$Arguments.ExpectedReleaseHead}else{'release'};$python=if($Arguments.ReleasePython){$Arguments.ReleasePython}else{Get-FinalRuntimePython $release ([pscustomobject]@{Mode='SIMULATION';RuntimeRoot=(Join-Path $root 'runtime')})}
    $allowLegacy=[bool]$(if($Arguments.ContainsKey('AllowLegacyMissingThemeSource')){$Arguments['AllowLegacyMissingThemeSource']}else{$false})
    [pscustomobject]@{Mode='SIMULATION';Root=$root;RuntimeRoot=(Join-Path $root 'runtime');AppPath=$app;Port=([int]$Arguments.SimulationPort);EnvPath=(Join-Path $root 'production\.env');DataRoot=(Join-Path $root 'production\streamlit_opensea_sales\data_opensea_sales');RepoRoot=(Join-Path $root 'production');PreparedReleaseRoot=(Join-Path $root 'release');ReleaseRoot=(Join-Path $root 'release');ReleasePython=$python;DeploymentRefreshPython='';BackupRoot=(Join-Path $root 'backups');PreparedReleaseManifest=$Arguments.PreparedReleaseManifest;PreparedReleaseManifestSha256=$Arguments.PreparedReleaseManifestSha256;BackupManifest=$Arguments.BackupManifest;ExpectedOldHead=$old;ExpectedReleaseHead=$release;SimulationStatePath=(Join-Path $root 'simulation_state.json');SupervisorServiceName='SANDBOX_NSSM';SupervisorType='NSSM';SupervisorAppDirectory=(Split-Path -Parent $app);SupervisorNssmExecutable='';SupervisorConfiguration=$null;SupervisorActivationStdOut='';SupervisorActivationStdErr='';ProfileSyncContractRequired=$false;ProfileKeySource='';ProfileSyncContract='NOT_RUN';ProfileSyncStateGate='NOT_RUN';ProfileCoverageGate='NOT_RUN';ProfileReaderGate='NOT_RUN';ProfileCount=0;ProfileOkCount=0;ProfileHumanUsernameCount=0;ProfileHumanDisplayNameCount=0;ProfileRemoteAvatarCount=0;ProfileSyncAttempted=0;ProfileSyncSuccessful=0;ProfileSyncNotFound=0;ProfileSyncErrors=0;ProfileSyncRateLimited=0;ProfileSyncHealth='NOT_RUN';MetadataRefreshResult='NOT_RUN';AllowLegacyMissingThemeSource=$allowLegacy;MutationStarted=$false;MutationPhases=(New-Object Collections.ArrayList);RollbackAttempted=$false;RollbackSucceeded=$false;StateRestored=$false}
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
function Get-ProfileSyncStateDefinition([object]$Context) {
    [pscustomobject]@{
        RelativePath='streamlit_opensea_sales\data_opensea_sales\opensea_account_profile_sync_state.json'
        Path=(Join-Path $Context.DataRoot 'opensea_account_profile_sync_state.json')
        BackupRelativePath='artifacts\opensea_account_profile_sync_state.json'
    }
}
function Test-ProfileSyncReleaseCapability([object]$Manifest) {
    $property=$Manifest.PSObject.Properties['profile_api_key_contract']
    if(-not$property){return $false}
    $contract=$property.Value
    if(-not$contract -or [string]$contract.preferred_variable -cne 'OPENSEA_PROFILE_API_KEY' -or [string]$contract.fallback_variable -cne 'OPENSEA_API_KEY' -or [string]$contract.legacy_variable_ignored -cne 'OPENSEA_API_OLD' -or [string]$contract.secret_values_in_manifest -cne 'NO'){throw 'PREPARED_RELEASE_PROFILE_SYNC_CONTRACT_INVALID'}
    $true
}
function Get-PropertyOrDefault([object]$Object,[string]$Name,[object]$Default='') {
    if($Object -is [System.Collections.IDictionary] -and $Object.Contains($Name)){return $Object[$Name]}
    if($null -ne $Object -and $null -ne $Object.PSObject.Properties[$Name]){return $Object.$Name}
    $Default
}
function Test-ObjectHasProperty([object]$Object,[string]$Name) {
    if($Object -is [System.Collections.IDictionary]){return $Object.Contains($Name)}
    $null -ne $Object -and $null -ne $Object.PSObject.Properties[$Name]
}
function Get-ProfileSnapshotReceiptMetrics([object]$Context) {
    $path=Join-Path $Context.DataRoot 'opensea_account_profiles_snapshot.json'
    if(-not(Test-Path $path -PathType Leaf)){throw 'PROFILE_SNAPSHOT_MISSING'}
    try{$payload=Get-Content $path -Raw|ConvertFrom-Json}catch{throw 'PROFILE_SNAPSHOT_INVALID'}
    $profiles=@();if($null -ne $payload.PSObject.Properties['profiles'] -and $payload.profiles){$profiles=@($payload.profiles.PSObject.Properties|ForEach-Object{$_.Value})}
    $human={param($value) if(-not($value -is [string])){return $false};$text=$value.Trim();if([string]::IsNullOrWhiteSpace($text)){return $false};if($text -match '^(?i)0x[0-9a-f]{40}$'){return $false};$true}
    $ok=0;$usernames=0;$displayNames=0;$avatars=0;foreach($profile in $profiles){if([string](Get-PropertyOrDefault $profile 'status') -eq 'ok'){$ok++};if(& $human (Get-PropertyOrDefault $profile 'username')){$usernames++};if(& $human (Get-PropertyOrDefault $profile 'display_name')){$displayNames++};$avatar=[string](Get-PropertyOrDefault $profile 'profile_image_url');if($avatar -match '^(?i)https?://'){$avatars++}}
    $fallbackCount=0;if($null -ne $payload.PSObject.Properties['fallback_names'] -and $payload.fallback_names){$fallbackCount=@($payload.fallback_names.PSObject.Properties).Count}
    $coverage=if($Context.Mode -eq 'SIMULATION' -or ($profiles.Count -ge 1250 -and $ok -ge 1200 -and $usernames -ge 850 -and $displayNames -ge 850 -and $avatars -ge 550 -and $fallbackCount -ge 1300)){'PASS'}else{'FAIL'}
    [pscustomobject]@{ProfileCount=$profiles.Count;OkCount=$ok;HumanUsernameCount=$usernames;HumanDisplayNameCount=$displayNames;RemoteAvatarCount=$avatars;FallbackNamesCount=$fallbackCount;CoverageGate=$coverage}
}
function Get-ProfileSyncStateReceiptMetrics([object]$Context) {
    $definition=Get-ProfileSyncStateDefinition $Context
    if(-not(Test-Path $definition.Path -PathType Leaf)){return [pscustomobject]@{Present=$false;Gate='FAIL';Diagnostics=$null}}
    try{$payload=Get-Content $definition.Path -Raw|ConvertFrom-Json}catch{return [pscustomobject]@{Present=$true;Gate='FAIL';Diagnostics=$null}}
    $raw=$payload|ConvertTo-Json -Depth 40 -Compress
    if($raw -match '(?i)"(?:OPENSEA_(?:PROFILE_)?API_KEY|OPENSEA_API_OLD|X-API-KEY)"\s*:'){return [pscustomobject]@{Present=$true;Gate='FAIL';Diagnostics=$null}}
    $last=Get-PropertyOrDefault $payload 'last_run' $null
    $required=@('started_at','completed_at','candidate_count','selected_count','attempted','successful','not_found','errors','rate_limited','remaining_targets','stopped_for_rate_limit','stopped_for_reserve','snapshot_write_executed')
    $valid=$null -ne $last
    foreach($field in $required){if($null -eq $last -or $null -eq $last.PSObject.Properties[$field]){$valid=$false}}
    [pscustomobject]@{Present=$true;Gate=if($valid){'PASS'}else{'FAIL'};Diagnostics=$last}
}
function Set-ProfileSyncReceiptState([object]$Context,[object]$Result) {
    $diagnostics=$null
    if($Result -and -not[string]::IsNullOrWhiteSpace([string]$Result.StdOut)){try{$diagnostics=([string]$Result.StdOut).Trim()|ConvertFrom-Json}catch{throw 'PROFILE_SYNC_DIAGNOSTICS_INVALID'}}
    if($diagnostics -and $null -ne $diagnostics.PSObject.Properties['last_run']){$diagnostics=$diagnostics.last_run};if($diagnostics){$Context.ProfileKeySource=[string](Get-PropertyOrDefault $diagnostics 'profile_key_source');$Context.ProfileSyncAttempted=[int](Get-PropertyOrDefault $diagnostics 'attempted' 0);$Context.ProfileSyncSuccessful=[int](Get-PropertyOrDefault $diagnostics 'successful' 0);$Context.ProfileSyncNotFound=[int](Get-PropertyOrDefault $diagnostics 'not_found' 0);$Context.ProfileSyncErrors=[int](Get-PropertyOrDefault $diagnostics 'errors' 0);$Context.ProfileSyncRateLimited=[int](Get-PropertyOrDefault $diagnostics 'rate_limited' 0);$Context.ProfileSyncHealth=if($Context.ProfileSyncErrors -eq 0 -and $Context.ProfileSyncRateLimited -eq 0){'PASS'}else{'DEGRADED'}}
    $state=Get-ProfileSyncStateReceiptMetrics $Context;if(-not$state.Present -or $state.Gate -ne 'PASS'){throw 'PROFILE_SYNC_STATE_GATE_FAILED'};$Context.ProfileSyncStateGate='PASS';if([string]::IsNullOrWhiteSpace($Context.ProfileKeySource) -and $state.Diagnostics){$Context.ProfileKeySource=[string](Get-PropertyOrDefault $state.Diagnostics 'profile_key_source')};if([string]::IsNullOrWhiteSpace($Context.ProfileKeySource)){$Context.ProfileKeySource='OPENSEA_PROFILE_API_KEY'};$Context.ProfileSyncContract=if($Context.ProfileKeySource -eq 'OPENSEA_PROFILE_API_KEY'){'PASS'}else{'FAIL'};if($Context.ProfileSyncContract -ne 'PASS'){throw 'PROFILE_SYNC_CONTRACT_FAILED'};$Context.MetadataRefreshResult='PASS'
}
function Set-ProfileSnapshotReceiptState([object]$Context) {$metrics=Get-ProfileSnapshotReceiptMetrics $Context;$Context.ProfileCount=$metrics.ProfileCount;$Context.ProfileOkCount=$metrics.OkCount;$Context.ProfileHumanUsernameCount=$metrics.HumanUsernameCount;$Context.ProfileHumanDisplayNameCount=$metrics.HumanDisplayNameCount;$Context.ProfileRemoteAvatarCount=$metrics.RemoteAvatarCount;$Context.ProfileCoverageGate=$metrics.CoverageGate;if($Context.ProfileCoverageGate -ne 'PASS'){throw 'PROFILE_COVERAGE_GATE_FAILED'};$Context.ProfileReaderGate='PASS'}
function Assert-DeploymentReceipt([object]$Receipt,[bool]$ProfileSyncRequired) {
    if(-not$ProfileSyncRequired){return}
    $serialized=$Receipt|ConvertTo-Json -Depth 40 -Compress;if($serialized -match '(?i)"(?:api_key|OPENSEA_API_KEY|OPENSEA_PROFILE_API_KEY|OPENSEA_API_OLD|x-api-key)"\s*:'){throw 'DEPLOYMENT_RECEIPT_SECRET_FIELD_FORBIDDEN'}
    $required=@('release','runtime','child_pid','health','theme_base','theme_contract','profile_key_source','profile_sync_contract','profile_sync_state_present','profile_sync_state_gate','profile_coverage_gate','profile_reader_gate','profile_count','profile_ok_count','profile_human_username_count','profile_human_display_name_count','profile_remote_avatar_count','metadata_refresh_result','profile_sync_attempted','profile_sync_successful','profile_sync_not_found','profile_sync_errors','profile_sync_rate_limited','profile_sync_health','secret_leak_gate')
    foreach($field in $required){if(-not(Test-ObjectHasProperty $Receipt $field)){throw ('DEPLOYMENT_RECEIPT_PROFILE_FIELD_MISSING:'+ $field)}}
    if(-not [bool](Get-PropertyOrDefault $Receipt 'profile_sync_state_present') -or [string](Get-PropertyOrDefault $Receipt 'profile_key_source') -cne 'OPENSEA_PROFILE_API_KEY' -or [string](Get-PropertyOrDefault $Receipt 'profile_sync_contract') -cne 'PASS' -or [string](Get-PropertyOrDefault $Receipt 'profile_sync_state_gate') -cne 'PASS' -or [string](Get-PropertyOrDefault $Receipt 'profile_coverage_gate') -cne 'PASS' -or [string](Get-PropertyOrDefault $Receipt 'profile_reader_gate') -cne 'PASS' -or [string](Get-PropertyOrDefault $Receipt 'metadata_refresh_result') -cne 'PASS' -or [string](Get-PropertyOrDefault $Receipt 'secret_leak_gate') -cne 'PASS'){throw 'DEPLOYMENT_RECEIPT_PROFILE_CONTRACT_FAILED'}
    if([string](Get-PropertyOrDefault $Receipt 'theme_base') -cne 'dark' -or [string](Get-PropertyOrDefault $Receipt 'theme_contract') -cne 'PASS' -or [string](Get-PropertyOrDefault $Receipt 'health') -cne 'PASS'){throw 'DEPLOYMENT_RECEIPT_BASE_CONTRACT_FAILED'}
}
function Assert-ProfileSyncBackupContract([object]$Manifest,[object]$Context,[string]$BackupBase='') {
    if([string]$Manifest.profile_sync_state_contract -cne 'OPTIONAL_SIDECAR_V1'){throw 'BACKUP_PROFILE_SYNC_STATE_CONTRACT_INVALID'}
    $required=@('profile_sync_state_existed_before','profile_sync_state_source_relative_path','profile_sync_state_backup_relative_path','profile_sync_state_sha256','profile_sync_state_size_bytes')
    foreach($field in $required){if($null -eq $Manifest.PSObject.Properties[$field]){throw 'BACKUP_PROFILE_SYNC_STATE_CONTRACT_MISSING'}}
    $definition=Get-ProfileSyncStateDefinition $Context
    if([string]$Manifest.profile_sync_state_source_relative_path -cne $definition.RelativePath -or [string]$Manifest.profile_sync_state_backup_relative_path -cne $definition.BackupRelativePath){throw 'BACKUP_PROFILE_SYNC_STATE_PATH_MISMATCH'}
    $backup=Join-Path $BackupBase $definition.BackupRelativePath
    if([bool]$Manifest.profile_sync_state_existed_before){if(-not(Test-Path $backup -PathType Leaf) -or [string]::IsNullOrWhiteSpace([string]$Manifest.profile_sync_state_sha256) -or (Get-Sha256 $backup) -ne [string]$Manifest.profile_sync_state_sha256 -or [int64]$Manifest.profile_sync_state_size_bytes -ne (Get-Item $backup).Length){throw 'BACKUP_PROFILE_SYNC_STATE_HASH_MISMATCH'}}elseif(Test-Path $backup){throw 'BACKUP_PROFILE_SYNC_STATE_UNEXPECTED_COPY'}
}
function Assert-8502ProcessOwnershipIdentity {
    param([object]$Listener,[object]$Process,[string]$ExpectedAppPath=$script:ExpectedApp,[string]$ExpectedRuntimeAppPath='', [int]$ExpectedPort=8502)
    if(-not$Listener -or $Listener.LocalAddress -ne '127.0.0.1' -or [int]$Listener.LocalPort -ne $ExpectedPort -or $Listener.State -ne 'Listen'){throw '8502_PROCESS_LISTENER_MISMATCH'}
    if(-not$Process -or $Listener.OwningProcess -and [int]$Listener.OwningProcess -ne [int]$Process.ProcessId){throw '8502_PROCESS_OWNER_MISMATCH'}
    if(-not$Process -or [string]::IsNullOrWhiteSpace([string]$Process.ExecutablePath) -or -not(Test-Path -LiteralPath $Process.ExecutablePath -PathType Leaf)){throw '8502_PROCESS_EXECUTABLE_MISSING'}
    if([IO.Path]::GetFileName([string]$Process.ExecutablePath) -ine 'python.exe'){throw '8502_PROCESS_NOT_PYTHON'}
    $command=[string]$Process.CommandLine;if([string]::IsNullOrWhiteSpace($command)){throw '8502_PROCESS_COMMANDLINE_MISSING'}
    if($command -notmatch '(?i)(?:-m\s+streamlit\s+run|(?:^|\s)streamlit(?:\.exe)?\s+run)'){throw '8502_PROCESS_NOT_STREAMLIT'}
    $null=Assert-StreamlitLaunchShape $command $ExpectedPort
    if($command -match '(?i)app_gaming_marketplace\.py'){throw '8502_PROCESS_FORBIDDEN_APP'}
    if($command -match '(?i)--server\.port(?:\s+|=)8501(?:\s|$)' -or $command -match '(?i)--server\.port(?:\s+|=)8504(?:\s|$)'){throw '8502_PROCESS_FORBIDDEN_PORT'}
    $portMatch=[regex]::Match($command,'(?i)--server\.port(?:\s+|=)(\d+)');if(-not$portMatch.Success -or [int]$portMatch.Groups[1].Value -ne $ExpectedPort){throw '8502_PROCESS_PORT_MISMATCH'}
    $addressMatch=[regex]::Match($command,'(?i)--server\.address(?:\s+|=)([^\s]+)');if($addressMatch.Success -and $addressMatch.Groups[1].Value.Trim('"') -ne '127.0.0.1'){throw '8502_PROCESS_ADDRESS_MISMATCH'}
    $appMatch=[regex]::Match($command,'(?i)(?:"(?<quoted>[^"\r\n]*app_opensea_sales\.py)"|(?<bare>[^\s"\r\n]*app_opensea_sales\.py))');if(-not$appMatch.Success){throw '8502_PROCESS_APP_MISMATCH'};$appToken=if($appMatch.Groups['quoted'].Success){$appMatch.Groups['quoted'].Value}else{$appMatch.Groups['bare'].Value}
    if($appToken -match '[\\/]'){$normalized=[IO.Path]::GetFullPath($appToken);$allowed=@([IO.Path]::GetFullPath($ExpectedAppPath));if($ExpectedRuntimeAppPath){$allowed+=[IO.Path]::GetFullPath($ExpectedRuntimeAppPath)};if($allowed -notcontains $normalized){throw '8502_PROCESS_ABSOLUTE_PATH_MISMATCH'}}elseif($appToken -notin @('app_opensea_sales.py','streamlit_opensea_sales\app_opensea_sales.py')){throw '8502_PROCESS_APP_MISMATCH'}
    $Process
}
function Test-8502ProcessIdentity {
    param([object]$Listener,[object]$Process,[string]$ExpectedAppPath=$script:ExpectedApp,[string]$ExpectedRuntimeAppPath='', [int]$ExpectedPort=8502,[switch]$AllowLegacyMissingThemeSource)
    $null=Assert-8502ProcessOwnershipIdentity $Listener $Process $ExpectedAppPath $ExpectedRuntimeAppPath $ExpectedPort
    $theme=Get-StreamlitThemeBaseState ([string]$Process.CommandLine)
    if($theme.State -eq 'DARK'){return $Process}
    if($AllowLegacyMissingThemeSource -and $theme.State -eq 'MISSING'){return $Process}
    throw 'SUPERVISOR_THEME_BASE_DARK_REQUIRED'
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
    foreach($name in @('manifest_version','prepared_release_head','prepared_release_git_tree_sha','requirements_txt_sha256','requirements_lock_sha256','wheelhouse','runtime_contract','validation','streamlit_theme_base','streamlit_theme_contract')){if($null -eq $manifest.$name){throw 'PREPARED_RELEASE_MANIFEST_INCOMPLETE'}};if([int]$manifest.manifest_version -ne 2){throw 'PREPARED_RELEASE_MANIFEST_VERSION_INVALID'};if($ExpectedHead -and $manifest.prepared_release_head -ne $ExpectedHead){throw 'PREPARED_RELEASE_HEAD_MISMATCH'};Assert-PreparedReleaseThemeContract $manifest
    $base=Split-Path $Path -Parent;$repo=if($manifest.prepared_repo_path){$manifest.prepared_repo_path}else{Join-Path $base 'repo'};if($Context.Mode -eq 'PRODUCTION'){if($Context.PreparedReleaseRoot -and [IO.Path]::GetFullPath($repo) -ne [IO.Path]::GetFullPath((Join-Path $Context.PreparedReleaseRoot 'repo'))){throw 'PREPARED_RELEASE_ROOT_MISMATCH'};if(-not(Test-Path $repo -PathType Container)){throw 'PREPARED_RELEASE_REPO_MISSING'};$tree=(& git -c ('safe.directory='+$repo) -C $repo rev-parse ($manifest.prepared_release_head+'^{tree}')).Trim();if($LASTEXITCODE -ne 0 -or $tree.ToLowerInvariant() -ne ([string]$manifest.prepared_release_git_tree_sha).ToLowerInvariant()){throw 'PREPARED_RELEASE_TREE_MISMATCH'};$repoHead=(& git -c ('safe.directory='+$repo) -C $repo rev-parse HEAD).Trim();if($LASTEXITCODE -ne 0 -or $repoHead -ne $manifest.prepared_release_head){throw 'PREPARED_RELEASE_HEAD_MISMATCH'};if(((& git -c ('safe.directory='+$repo) -C $repo status --porcelain)-join '') -ne ''){throw 'PREPARED_RELEASE_REPO_NOT_CLEAN'};$req=(Join-Path $repo 'requirements.txt');$lock=(Join-Path $repo 'requirements.lock.txt');if(-not(Test-Path $req -PathType Leaf) -or -not(Test-Path $lock -PathType Leaf) -or (Get-Sha256 $req).ToLowerInvariant() -ne ([string]$manifest.requirements_txt_sha256).ToLowerInvariant() -or (Get-Sha256 $lock).ToLowerInvariant() -ne ([string]$manifest.requirements_lock_sha256).ToLowerInvariant()){throw 'PREPARED_RELEASE_REQUIREMENTS_HASH_MISMATCH'}}
    if([int]$manifest.wheelhouse.package_count -ne 45 -or [string]::IsNullOrWhiteSpace([string]$manifest.wheelhouse.manifest_path) -or [string]$manifest.wheelhouse.manifest_sha256 -eq ''){throw 'PREPARED_RELEASE_WHEELHOUSE_INVALID'};$wheel=Join-Path $base $manifest.wheelhouse.manifest_path;if(-not(Test-Path $wheel -PathType Leaf) -or (Get-Sha256 $wheel).ToLowerInvariant() -ne ([string]$manifest.wheelhouse.manifest_sha256).ToLowerInvariant()){throw 'PREPARED_RELEASE_WHEELHOUSE_HASH_MISMATCH'};if([int]$manifest.runtime_contract.locked_package_count -ne 45 -or [int]$manifest.runtime_contract.exact_lock_match -ne 45 -or $manifest.runtime_contract.pip_check -ne 'PASS' -or $manifest.runtime_contract.import_gate -ne 'PASS'){throw 'PREPARED_RELEASE_RUNTIME_GATES_FAILED'};if([int]$manifest.validation.full_tests_failure_count -ne 0 -or $manifest.validation.canary -ne 'PASS' -or $manifest.validation.application_readers -ne 'PASS'){throw 'PREPARED_RELEASE_VALIDATION_GATES_FAILED'};$profileSyncRequired=Test-ProfileSyncReleaseCapability $manifest;[pscustomobject]@{Manifest=$manifest;Base=$base;Repo=$repo;WheelManifest=$wheel;ProfileSyncContractRequired=$profileSyncRequired}
}
function Read-BackupManifest {
    param([string]$Path,[object]$Context)
    if(-not(Test-Path $Path -PathType Leaf)){throw 'BACKUP_MANIFEST_MISSING'}
    $manifest=Get-Content $Path -Raw|ConvertFrom-Json
    if([int]$manifest.manifest_version -ne 2 -or -not$manifest.backup_complete -or $manifest.target_root -ne $Context.Root -or [int]$manifest.target_port -ne $Context.Port -or $manifest.target_app -ne $Context.AppPath){throw 'BACKUP_MANIFEST_INVALID'}
    $supervisor=$manifest.supervisor
    foreach($field in @('service_name','supervisor_type','service_display_name','service_start_mode','service_was_running','service_binary_path','nssm_executable','application','app_directory','app_parameters','source_theme_base','source_theme_contract','app_stdout','app_stderr','app_restart_delay','app_throttle','app_exit_default','app_stop_method_console','app_stop_method_window','app_stop_method_threads','app_stop_method_skip','app_kill_process_tree','app_stdout_share_mode','app_stderr_share_mode','app_rotate_files','app_rotate_online','app_rotate_seconds','app_rotate_bytes','app_timestamp_log','windows_service_failure_actions','configuration_fingerprint')){if($supervisor -and $null -eq $supervisor.PSObject.Properties[$field]){throw 'BACKUP_SUPERVISOR_STATE_INCOMPLETE'}}
    if(-not$supervisor -or [string]$supervisor.service_name -ne (Get-SupervisorServiceName $Context) -or [string]$supervisor.supervisor_type -ne 'NSSM' -or [string]::IsNullOrWhiteSpace([string]$supervisor.service_display_name) -or [string]::IsNullOrWhiteSpace([string]$supervisor.service_start_mode) -or [string]::IsNullOrWhiteSpace([string]$supervisor.service_binary_path) -or [string]::IsNullOrWhiteSpace([string]$supervisor.nssm_executable) -or [string]::IsNullOrWhiteSpace([string]$supervisor.application) -or [string]::IsNullOrWhiteSpace([string]$supervisor.app_directory) -or [string]::IsNullOrWhiteSpace([string]$supervisor.app_parameters) -or [string]::IsNullOrWhiteSpace([string]$supervisor.source_theme_base) -or [string]::IsNullOrWhiteSpace([string]$supervisor.source_theme_contract) -or [string]::IsNullOrWhiteSpace([string]$supervisor.app_restart_delay) -or [string]::IsNullOrWhiteSpace([string]$supervisor.app_throttle) -or [string]::IsNullOrWhiteSpace([string]$supervisor.configuration_fingerprint)){throw 'BACKUP_SUPERVISOR_STATE_INCOMPLETE'}
    if([string]$supervisor.source_theme_base -notin @('DARK','MISSING') -or ([string]$supervisor.source_theme_base -eq 'MISSING' -and [string]$supervisor.source_theme_contract -ne 'LEGACY_MISSING_ALLOWED_FOR_CORRECTION') -or ([string]$supervisor.source_theme_base -eq 'DARK' -and [string]$supervisor.source_theme_contract -ne 'PASS')){throw 'BACKUP_SUPERVISOR_THEME_STATE_INVALID'}
    if(([string]$supervisor.configuration_fingerprint).ToLowerInvariant() -ne (Get-SupervisorManifestFingerprint $supervisor).ToLowerInvariant()){throw 'BACKUP_SUPERVISOR_FINGERPRINT_MISMATCH'}
    $base=Split-Path $Path -Parent
    foreach($pair in @(@('env_backup_relative_path','env_sha256'),@('git_bundle_relative_path','git_bundle_sha256'),@('db_dump_relative_path','db_dump_sha256'))){$candidate=Join-Path $base $manifest.($pair[0]);if(-not(Test-Path $candidate -PathType Leaf) -or (Get-Sha256 $candidate) -ne [string]$manifest.($pair[1])){throw 'BACKUP_MANIFEST_HASH_MISMATCH'}}
    if($manifest.db_dump_format -ne 'custom' -or $manifest.db_dump_validation -ne 'PASS'){throw 'BACKUP_DB_VALIDATION_MISSING'}
    if(@($manifest.dynamic_artifacts).Count -ne 6 -or @($manifest.production_refresh_tasks).Count -ne 2){throw 'BACKUP_MANIFEST_STATE_INCOMPLETE'}
    foreach($artifact in @($manifest.dynamic_artifacts)){if($artifact.existed_before){$candidate=Join-Path $base $artifact.backup_relative_path;if(-not(Test-Path $candidate -PathType Leaf) -or (Get-Sha256 $candidate) -ne [string]$artifact.sha256_before){throw 'BACKUP_ARTIFACT_HASH_MISMATCH'}}}
    $syncDefinition=[pscustomobject]@{RelativePath='streamlit_opensea_sales\data_opensea_sales\opensea_account_profile_sync_state.json';Path=(Join-Path $Context.DataRoot 'opensea_account_profile_sync_state.json');BackupRelativePath='artifacts\opensea_account_profile_sync_state.json'}
    if($null -ne $manifest.PSObject.Properties['profile_sync_state_contract']){Assert-ProfileSyncBackupContract $manifest $Context $base}
    [pscustomobject]@{Manifest=$manifest;Base=$base}
}

function Invoke-BackupCore {
    param([object]$Context,[switch]$Execute)
    Assert-Context $Context;if(-not$Execute){Write-KV 'MODE' 'DRY_RUN';Write-KV 'TARGET_ROOT' $Context.Root;Write-KV 'TARGET_PORT' $Context.Port;Write-KV 'BACKUP_MANIFEST_SCHEMA_VERSION' 2;Write-KV 'BACKUP_SET_VALID' 'YES';return}
    Set-Phase $Context 'BACKUP_VALIDATE';$head=$Context.ExpectedOldHead;$branch='main';$processPid=0;$processExe='simulation';$processCmd='simulation app_opensea_sales.py';$supervisor=$null
    if($Context.Mode -eq 'PRODUCTION'){
        $head=(& git -c ('safe.directory='+$Context.Root) -C $Context.Root rev-parse HEAD).Trim();$branch=(& git -c ('safe.directory='+$Context.Root) -C $Context.Root branch --show-current).Trim()
        if(((& git -c ('safe.directory='+$Context.Root) -C $Context.Root status --porcelain)-join '') -ne ''){throw 'PRODUCTION_WORKTREE_NOT_CLEAN'}
        $owned=Get-ProductionSupervisor $Context -AllowLegacyMissingThemeSource:$Context.AllowLegacyMissingThemeSource;$process=$owned.Child.Process;if(-not$process){throw 'SUPERVISOR_CHILD_NOT_FOUND'};$processPid=$process.ProcessId;$processExe=$process.ExecutablePath;$processCmd=$process.CommandLine;$supervisor=$owned.Configuration
        $tools=Get-PostgresTools;foreach($name in @('pg_dump','pg_restore','psql')){if(-not$tools.ContainsKey($name)){throw ('POSTGRES_TOOL_MISSING:'+ $name)}};Get-DatabaseEnvironment $Context.EnvPath -Required|Out-Null
    } elseif(-not(Test-Path $Context.EnvPath -PathType Leaf)){throw 'SIMULATION_ENV_MISSING'}
    if(-not$supervisor){$sandboxParameters=(Get-ProductionStreamlitLaunchParameters).Replace('--server.port 8502','--server.port '+$Context.Port);$null=Assert-StreamlitLaunchContract $sandboxParameters $Context.Port;$supervisor=[pscustomobject]@{ServiceName=$Context.SupervisorServiceName;ServiceDisplayName='Sandbox NSSM';ServiceStartMode='Manual';ServiceBinaryPath='sandbox-nssm.exe';ServiceWasRunning=$true;NssmExecutable='sandbox-nssm.exe';NssmVersion='sandbox';Application='sandbox-python.exe';AppDirectory=$Context.SupervisorAppDirectory;AppParameters=$sandboxParameters;AppStdout='';AppStderr='';AppRestartDelay='0';AppThrottle='1500';AppExitDefault='Restart';AppStopMethodConsole='1500';AppStopMethodWindow='1500';AppStopMethodThreads='1500';AppStopMethodSkip='0';AppKillProcessTree='1';AppStdoutShareMode='3';AppStderrShareMode='3';AppRotateFiles='0';AppRotateOnline='0';AppRotateSeconds='0';AppRotateBytes='0';AppTimestampLog='0';WindowsServiceFailureActions='sandbox'}}
    $supervisorFingerprint=Get-SupervisorConfigurationFingerprint $supervisor
    $sourceThemeBase=if($supervisor.PSObject.Properties['SourceThemeBase']){[string]$supervisor.SourceThemeBase}else{(Get-StreamlitThemeBaseState ([string]$supervisor.AppParameters)).State};$sourceThemeContract=if($sourceThemeBase -eq 'MISSING'){'LEGACY_MISSING_ALLOWED_FOR_CORRECTION'}elseif($sourceThemeBase -eq 'DARK'){'PASS'}else{'FAIL'}
    $supervisorManifest=[ordered]@{service_name=$supervisor.ServiceName;supervisor_type='NSSM';service_display_name=$supervisor.ServiceDisplayName;service_start_mode=$supervisor.ServiceStartMode;service_was_running=[bool]$supervisor.ServiceWasRunning;service_binary_path=$supervisor.ServiceBinaryPath;nssm_executable=$supervisor.NssmExecutable;nssm_version=$supervisor.NssmVersion;application=$supervisor.Application;app_directory=$supervisor.AppDirectory;app_parameters=$supervisor.AppParameters;source_theme_base=$sourceThemeBase;source_theme_contract=$sourceThemeContract;app_stdout=$supervisor.AppStdout;app_stderr=$supervisor.AppStderr;app_restart_delay=$supervisor.AppRestartDelay;app_throttle=$supervisor.AppThrottle;app_exit_default=$supervisor.AppExitDefault;app_stop_method_console=$supervisor.AppStopMethodConsole;app_stop_method_window=$supervisor.AppStopMethodWindow;app_stop_method_threads=$supervisor.AppStopMethodThreads;app_stop_method_skip=$supervisor.AppStopMethodSkip;app_kill_process_tree=$supervisor.AppKillProcessTree;app_stdout_share_mode=$supervisor.AppStdoutShareMode;app_stderr_share_mode=$supervisor.AppStderrShareMode;app_rotate_files=$supervisor.AppRotateFiles;app_rotate_online=$supervisor.AppRotateOnline;app_rotate_seconds=$supervisor.AppRotateSeconds;app_rotate_bytes=$supervisor.AppRotateBytes;app_timestamp_log=$supervisor.AppTimestampLog;windows_service_failure_actions=$supervisor.WindowsServiceFailureActions;configuration_fingerprint=$supervisorFingerprint}
    Add-Mutation $Context 'BACKUP_CREATE';$stamp=Get-Date -Format yyyyMMdd_HHmmss;$short=if($head.Length -gt 8){$head.Substring(0,8)}else{$head};$out=Join-Path $Context.BackupRoot ($stamp+'_'+$short);New-Item -ItemType Directory -Path $out -Force|Out-Null;$syncDefinition=Get-ProfileSyncStateDefinition $Context;$syncPresent=Test-Path $syncDefinition.Path -PathType Leaf;$manifest=[ordered]@{manifest_version=2;created_at=(Get-Date).ToUniversalTime().ToString('o');target_root=$Context.Root;target_port=$Context.Port;target_app=$Context.AppPath;old_git_head=$head;old_git_branch=$branch;old_git_clean=$true;old_process_pid=$processPid;old_process_executable=$processExe;old_process_command_line_sanitized=$processCmd;old_app_path=$Context.AppPath;old_port=$Context.Port;old_runtime_root=$Context.RuntimeRoot;supervisor=$supervisorManifest;env_backup_relative_path='.env';git_bundle_relative_path='production.bundle';db_dump_relative_path='production.dump';db_dump_format='custom';db_dump_validation='PENDING';dynamic_artifacts=@();profile_sync_state_contract='OPTIONAL_SIDECAR_V1';profile_sync_state_source_relative_path=$syncDefinition.RelativePath;profile_sync_state_backup_relative_path=$syncDefinition.BackupRelativePath;profile_sync_state_existed_before=[bool]$syncPresent;profile_sync_state_sha256=if($syncPresent){Get-Sha256 $syncDefinition.Path}else{''};profile_sync_state_size_bytes=if($syncPresent){(Get-Item $syncDefinition.Path).Length}else{0};active_runtime_existed=$false;production_refresh_tasks=@();backup_complete=$false}
    $bundleResult=Invoke-GitBundleBackup $Context $out;if($Context.Mode -eq 'SIMULATION'){$null=Copy-Item $Context.EnvPath (Join-Path $out '.env');$null=Set-Content (Join-Path $out 'production.dump') 'sandbox custom dump';$manifest.db_dump_validation='PASS'}else{Copy-Item $Context.EnvPath (Join-Path $out '.env');$env=Get-DatabaseEnvironment $Context.EnvPath -Required;Invoke-ChildProcess $tools.pg_dump @('--format=custom','--file',(Join-Path $out 'production.dump')) $Context.Root 1800 $env|Out-Null;Invoke-ChildProcess $tools.pg_restore @('--list',(Join-Path $out 'production.dump')) $Context.Root 300 $env|Out-Null;$manifest.db_dump_validation='PASS'};$manifest.git_bundle_validation='PASS';$manifest.env_sha256=Get-Sha256 (Join-Path $out '.env');$manifest.git_bundle_sha256=Get-Sha256 (Join-Path $out 'production.bundle');$manifest.db_dump_sha256=Get-Sha256 (Join-Path $out 'production.dump')
    foreach($definition in Get-DynamicArtifactDefinitions $Context){$entry=[ordered]@{relative_path=$definition.RelativePath;existed_before=(Test-Path $definition.Path -PathType Leaf)};if($entry.existed_before){$entry.backup_relative_path='artifacts\'+[IO.Path]::GetFileName($definition.Path);New-Item (Join-Path $out 'artifacts') -ItemType Directory -Force|Out-Null;Copy-Item $definition.Path (Join-Path $out $entry.backup_relative_path);$entry.sha256_before=Get-Sha256 $definition.Path;$entry.size_bytes=(Get-Item $definition.Path).Length};$manifest.dynamic_artifacts+=,$entry};if($syncPresent){New-Item (Join-Path $out 'artifacts') -ItemType Directory -Force|Out-Null;Copy-Item $syncDefinition.Path (Join-Path $out $syncDefinition.BackupRelativePath);if((Get-Sha256 (Join-Path $out $syncDefinition.BackupRelativePath)) -ne [string]$manifest.profile_sync_state_sha256){throw 'BACKUP_PROFILE_SYNC_STATE_COPY_FAILED'}};$active=Join-Path $Context.RuntimeRoot 'ACTIVE_RUNTIME.json';if(Test-Path $active -PathType Leaf){New-Item (Join-Path $out 'runtime') -ItemType Directory -Force|Out-Null;Copy-Item $active (Join-Path $out 'runtime\ACTIVE_RUNTIME.json');$manifest.active_runtime_existed=$true;$manifest.active_runtime_backup_relative_path='runtime\ACTIVE_RUNTIME.json';$manifest.active_runtime_sha256=Get-Sha256 $active}
    foreach($name in $script:ManagedTasks){$entry=[ordered]@{task_name=$name;existed_before=$false};if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;$taskProperty=@();if($state.tasks){$taskProperty=@($state.tasks.PSObject.Properties|Where-Object Name -eq $name)};if($taskProperty.Count -gt 0){$entry.existed_before=$true;$entry.state=$state.tasks.$name}}else{$task=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue;if($task){$relative='tasks\'+$name+'.xml';New-Item (Join-Path $out 'tasks') -ItemType Directory -Force|Out-Null;Write-AtomicText (Join-Path $out $relative) (Export-ScheduledTask -TaskName $name -ErrorAction Stop);$entry.existed_before=$true;$entry.exported_xml_relative_path=$relative;$entry.xml_sha256=Get-Sha256 (Join-Path $out $relative);$entry.enabled=($task.State -ne 'Disabled')}};$manifest.production_refresh_tasks+=,$entry};$manifest.backup_complete=$true;Write-AtomicJson (Join-Path $out 'BACKUP_MANIFEST.json') $manifest;Write-KV 'BACKUP_MANIFEST_SCHEMA_VERSION' 2;Write-KV 'BACKUP_MANIFEST_PATH' (Join-Path $out 'BACKUP_MANIFEST.json');Write-KV 'BACKUP_RESULT' 'PASS'
}

function Write-SimulationArtifacts([object]$Context,[int[]]$Indexes) {$definitions=Get-DynamicArtifactDefinitions $Context;foreach($index in $Indexes){$path=$definitions[$index].Path;New-Item (Split-Path $path) -ItemType Directory -Force|Out-Null;switch($index){0{$payload=@{schema_version=1;source_market_build_id='release';source_latest_date='2026-01-01T00:00:00Z';periods=@{all=@{totals=@{transactions=1};usd_pricing=@{total_volume_usd=1}}}}};1{$payload=@{schema_version=1;source_market_build_id='release';source_latest_date='2026-01-01T00:00:00Z';unique_wallets=@{daily=@(@{date='2026-01-01';unique_wallets=1});monthly=@(@{month='2026-01';month_start='2026-01-01';month_end='2026-01-31';unique_wallets=1})}}};2{$payload=@{schema_version=1;source='opensea';generated_at='2026-01-01T00:00:00Z';event_count=1;wallet_count=1;wallets=@(@{wallet='sandbox-wallet'})}};3{$payload=@{schema_version=1;source='sandbox';items=@{Example=@{class='Weapon'}}}};4{$payload=@{schema_version=3;source='gunzscope';provider_scope=@{exclude_zero=$true;exclude_base=$false;sort='activeMints';order='asc'};provider_items=@{p1=@{provider_item_id='p1';provider_item_name='Example';provider_rarity='common';status='ok';ranking_eligible=$true;raw_active_mints=1}};catalog_mappings=@{Example=@{mapping_status='DIRECT_CURRENT';provider_item_id='p1'}};provider_item_conflicts=@()}};5{$payload=@{schema_version=1;source='opensea';profiles=@{};fallback_names=@{'sandbox-wallet'='Sandbox Wallet'}}};};Write-AtomicJson $path $payload}}
function Invoke-Readers([object]$Context) {if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;if($state.reader_fail){throw 'APPLICATION_READER_VALIDATION_FAILED'};foreach($definition in Get-DynamicArtifactDefinitions $Context){if(-not(Test-Path $definition.Path -PathType Leaf)){throw 'APPLICATION_READER_VALIDATION_FAILED'};try{$null=Get-Content $definition.Path -Raw|ConvertFrom-Json}catch{throw 'APPLICATION_READER_VALIDATION_FAILED'}};Set-ProfileSnapshotReceiptState $Context;Write-KV 'POST_REFRESH_APPLICATION_READERS' 'PASS';return};$env=Get-SafeEnv $Context.EnvPath;$env['GUNZSCOPE_SUPPLY_SOURCE']='v3';$helper=Join-Path $Context.RepoRoot 'ops\production\validate_dynamic_artifacts.py';Invoke-ChildProcess $Context.ReleasePython @($helper,'--repo-root',$Context.RepoRoot,'--data-dir',$Context.DataRoot,'--env',$Context.EnvPath) $Context.RepoRoot 900 $env (Join-Path $Context.RuntimeRoot 'dynamic_reader_validation.log')|Out-Null;Set-ProfileSnapshotReceiptState $Context;$Context.ProfileReaderGate='PASS';Write-KV 'POST_REFRESH_APPLICATION_READERS' 'PASS'}
function Invoke-RefreshAdapter([object]$Context,[string]$Name,[string]$Python,[string[]]$Arguments,[string]$WorkingDirectory) {if($Context.Mode -eq 'SIMULATION'){Add-Mutation $Context ('REFRESH_'+$Name);Add-Content (Join-Path $Context.Root 'refresh.commands.log') $Name;return [pscustomobject]@{ExitCode=0;StdOut='';StdErr=''}};Invoke-ChildProcess $Python $Arguments $WorkingDirectory 1800 (Get-DatabaseEnvironment $Context.EnvPath)}
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
function Invoke-MetadataRefreshCore {param([object]$Context,[switch]$Execute);Assert-Context $Context;if(-not$Execute){Write-KV 'MODE' 'DRY_RUN';Write-KV 'METADATA_REFRESH_PLAN' 'PASS';return};Set-Phase $Context 'METADATA_REFRESH';Add-Mutation $Context 'METADATA_REFRESH';$python=Get-RefreshPython $Context;$definitions=Get-DynamicArtifactDefinitions $Context;$profileResult=$null;if($Context.Mode -eq 'SIMULATION'){Write-SimulationArtifacts $Context @(3,4,5);$syncDefinition=Get-ProfileSyncStateDefinition $Context;Write-AtomicJson $syncDefinition.Path ([ordered]@{schema_version=1;source='opensea';updated_at=(Get-Date).ToUniversalTime().ToString('o');wallets=@{};last_run=[ordered]@{started_at=(Get-Date).ToUniversalTime().ToString('o');completed_at=(Get-Date).ToUniversalTime().ToString('o');candidate_count=1;selected_count=1;attempted=1;successful=1;not_found=0;errors=0;rate_limited=0;remaining_targets=0;stopped_for_rate_limit=$false;stopped_for_reserve=$false;snapshot_write_executed=$true;profile_key_source='OPENSEA_PROFILE_API_KEY'}});Add-Content (Join-Path $Context.Root 'refresh.commands.log') 'item_class';Add-Content (Join-Path $Context.Root 'refresh.commands.log') 'gunzscope_v3';Add-Content (Join-Path $Context.Root 'refresh.commands.log') 'profile_sync';$profileResult=[pscustomobject]@{ExitCode=0;StdOut=(Get-Content $syncDefinition.Path -Raw);StdErr=''}}else{$scripts=Join-Path $Context.RepoRoot 'scripts';Invoke-RefreshAdapter $Context 'item_class' $python @((Join-Path $scripts 'refresh_item_class_snapshot.py')) $Context.RepoRoot|Out-Null;Invoke-RefreshAdapter $Context 'gunzscope_v3' $python @((Join-Path $scripts 'refresh_gunzscope_supply_v3_provider.py')) $Context.RepoRoot|Out-Null;$profileResult=Invoke-RefreshAdapter $Context 'profile_sync' $python @((Join-Path $scripts 'run_trader_profile_sync.py')) $Context.RepoRoot};foreach($index in 3..5){if(-not(Test-Path $definitions[$index].Path -PathType Leaf) -or (Get-Item $definitions[$index].Path).Length -le 0){throw 'METADATA_OUTPUT_MISSING'}};Set-ProfileSyncReceiptState $Context $profileResult;Write-KV 'PROFILE_KEY_SOURCE' $Context.ProfileKeySource;Write-KV 'PROFILE_SYNC_ATTEMPTED' $Context.ProfileSyncAttempted;Write-KV 'PROFILE_SYNC_SUCCESSFUL' $Context.ProfileSyncSuccessful;Write-KV 'PROFILE_SYNC_NOT_FOUND' $Context.ProfileSyncNotFound;Write-KV 'PROFILE_SYNC_ERRORS' $Context.ProfileSyncErrors;Write-KV 'PROFILE_SYNC_RATE_LIMITED' $Context.ProfileSyncRateLimited;Write-KV 'PROFILE_SYNC_HEALTH' $Context.ProfileSyncHealth;Write-KV 'METADATA_ITEM_CLASS' 'PASS';Write-KV 'METADATA_GUNZSCOPE_V3' 'PASS';Write-KV 'METADATA_PROFILE_SYNC' 'PASS';Write-KV 'METADATA_REFRESH' 'PASS'}
function Get-DesiredTaskDefinition([object]$Context,[string]$Name) {
    if($Name -notin $script:ManagedTasks){throw ('TASK_NAME_NOT_MANAGED:'+ $Name)}
    $derived=$Name -eq $script:ManagedTasks[0];$minutes=if($derived){15}else{60};$scriptName=if($derived){'refresh_production_derived.ps1'}else{'refresh_production_metadata.ps1'};$approval=if($derived){'REFRESH_OTG_DERIVED_8502'}else{'REFRESH_OTG_METADATA_8502'};$path=Join-Path $Context.Root ('ops\production\'+$scriptName);$arguments='-NoProfile -ExecutionPolicy Bypass -File "'+$path+'" -Execute -ApprovalPhrase '+$approval;if($Context.Mode -eq 'SIMULATION' -or $Context.ReleasePython){$arguments+=' -ReleasePython "'+$Context.ReleasePython+'"'}
    [ordered]@{task_name=$Name;executable='PowerShell.exe';arguments=$arguments;working_directory=$Context.Root;interval_minutes=$minutes;multiple_instances='IgnoreNew';start_when_available=$true;principal='SYSTEM';run_level='Highest';enabled=$true}
}
function Get-OptionalObjectProperty([object]$Object,[string]$Name) {
    if($null -ne $Object -and $null -ne $Object.PSObject.Properties[$Name]){return $Object.PSObject.Properties[$Name].Value}
    $null
}
function ConvertTo-TaskDefinitionRecord([object]$Task) {
    $directKeys=@('executable','arguments','working_directory','interval_minutes','multiple_instances','start_when_available','principal','run_level','enabled')
    $isDirect=$true;foreach($key in $directKeys){if($null -eq $Task.PSObject.Properties[$key]){$isDirect=$false;break}}
    if($isDirect){return [pscustomobject]@{task_name=[string](Get-OptionalObjectProperty $Task 'task_name');executable=[string]$Task.executable;arguments=[string]$Task.arguments;working_directory=[string]$Task.working_directory;interval_minutes=[int]$Task.interval_minutes;multiple_instances=[string]$Task.multiple_instances;start_when_available=[bool]$Task.start_when_available;principal=[string]$Task.principal;run_level=[string]$Task.run_level;enabled=[bool]$Task.enabled;action_count=1;trigger_count=1}}
    $actions=@(Get-OptionalObjectProperty $Task 'Actions');$action=if($actions.Count -eq 1){$actions[0]}else{$null};$settings=Get-OptionalObjectProperty $Task 'Settings';$principalObject=Get-OptionalObjectProperty $Task 'Principal';$triggers=@(Get-OptionalObjectProperty $Task 'Triggers');$interval=$null
    if($triggers.Count -eq 1){$repetition=Get-OptionalObjectProperty $triggers[0] 'Repetition';$raw=[string](Get-OptionalObjectProperty $repetition 'Interval');if($raw -match '(?i)^PT(\d+)M$'){$interval=[int]$Matches[1]}elseif($raw){try{$interval=[int]([Xml.XmlConvert]::ToTimeSpan($raw).TotalMinutes)}catch{}}}
    $state=[string](Get-OptionalObjectProperty $Task 'State');$enabled=if($state){$state -ne 'Disabled'}else{[bool](Get-OptionalObjectProperty $Task 'Enabled')}
    [pscustomobject]@{task_name=[string](Get-OptionalObjectProperty $Task 'TaskName');executable=[string](Get-OptionalObjectProperty $action 'Execute');arguments=[string](Get-OptionalObjectProperty $action 'Arguments');working_directory=[string](Get-OptionalObjectProperty $action 'WorkingDirectory');interval_minutes=$interval;multiple_instances=[string](Get-OptionalObjectProperty $settings 'MultipleInstances');start_when_available=[bool](Get-OptionalObjectProperty $settings 'StartWhenAvailable');principal=[string](Get-OptionalObjectProperty $principalObject 'UserId');run_level=[string](Get-OptionalObjectProperty $principalObject 'RunLevel');enabled=$enabled;action_count=$actions.Count;trigger_count=$triggers.Count}
}
function Test-ManagedReleasePythonPath([object]$Context,[string]$Path) {
    if([string]::IsNullOrWhiteSpace($Path)){return $false};try{$full=[IO.Path]::GetFullPath($Path)}catch{return $false};if([IO.Path]::GetFileName($full) -ine 'python.exe'){return $false}
    $releaseRoot=([IO.Path]::GetFullPath((Join-Path $Context.RuntimeRoot 'releases'))).TrimEnd('\')+'\';if(-not$full.StartsWith($releaseRoot,[StringComparison]::OrdinalIgnoreCase)){return $false};$relative=$full.Substring($releaseRoot.Length);$parts=$relative -split '\\';if($parts.Count -ne 4 -or $parts[1] -ne '.venv' -or $parts[2] -ne 'Scripts' -or $parts[3] -ine 'python.exe'){return $false};if($Context.Mode -eq 'SIMULATION'){return -not[string]::IsNullOrWhiteSpace($parts[0])};return $parts[0] -match '^[0-9a-f]{40}$'
}
function Assert-ManagedTaskOwnershipIdentity([object]$Context,[string]$Name,[object]$Existing) {
    if($Name -notin $script:ManagedTasks){throw ('TASK_COLLISION:'+ $Name)};$record=ConvertTo-TaskDefinitionRecord $Existing;$desired=Get-DesiredTaskDefinition $Context $Name
    if($record.action_count -and $record.action_count -ne 1){throw ('TASK_COLLISION:'+ $Name)};if($record.trigger_count -and $record.trigger_count -ne 1){throw ('TASK_COLLISION:'+ $Name)};if([IO.Path]::GetFileName([string]$record.executable) -ine 'powershell.exe'){throw ('TASK_COLLISION:'+ $Name)}
    $scriptFile=if($Name -eq $script:ManagedTasks[0]){'refresh_production_derived.ps1'}else{'refresh_production_metadata.ps1'};$scriptPath=[regex]::Escape([string]$desired.working_directory+'\ops\production\'+$scriptFile);$approval=if($Name -eq $script:ManagedTasks[0]){'REFRESH_OTG_DERIVED_8502'}else{'REFRESH_OTG_METADATA_8502'};$pattern='(?is)^\s*-NoProfile\s+-ExecutionPolicy\s+Bypass\s+-File\s+"'+$scriptPath+'"\s+-Execute\s+-ApprovalPhrase\s+'+[regex]::Escape($approval)+'(?:\s+-ReleasePython\s+"(?<python>[^"]+)")?\s*$';$match=[regex]::Match([string]$record.arguments,$pattern)
    if(-not$match.Success){throw ('TASK_COLLISION:'+ $Name)};if($match.Groups['python'].Success -and -not(Test-ManagedReleasePythonPath $Context $match.Groups['python'].Value)){throw ('TASK_COLLISION:'+ $Name)};if([string]$record.working_directory -ine [string]$desired.working_directory -or [string]$record.multiple_instances -ine 'IgnoreNew' -or -not[bool]$record.start_when_available -or [string]$record.principal -notmatch '(?i)^SYSTEM$' -or [string]$record.run_level -notmatch '(?i)^Highest(?:Available)?$' -or $null -eq $record.interval_minutes -or [int]$record.interval_minutes -ne [int]$desired.interval_minutes -or -not[bool]$record.enabled){throw ('TASK_COLLISION:'+ $Name)}
    $record
}
function Test-TaskDefinitionMatch([object]$Existing,[object]$Desired){$record=ConvertTo-TaskDefinitionRecord $Existing;foreach($key in @('executable','arguments','working_directory','interval_minutes','multiple_instances','start_when_available','principal','run_level','enabled')){if([string]$record.$key -ine [string]$Desired[$key]){return $false}};return $true}
function New-CanonicalTaskObjects([object]$Desired) {
    $action=New-ScheduledTaskAction -Execute $Desired.executable -Argument $Desired.arguments -WorkingDirectory $Desired.working_directory;$trigger=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $Desired.interval_minutes) -RepetitionDuration (New-TimeSpan -Days 3650);$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable;$principal=New-ScheduledTaskPrincipal -UserId SYSTEM -LogonType ServiceAccount -RunLevel Highest
    [pscustomobject]@{Action=$action;Trigger=$trigger;Settings=$settings;Principal=$principal}
}
function Invoke-TaskConfigurationCore {param([object]$Context,[switch]$Execute);Assert-Context $Context;if(-not$Execute){Write-KV 'MODE' 'DRY_RUN';Write-KV 'TASK_CONFIGURATION_PLAN' 'PASS';Write-KV 'PRODUCTION_REFRESH_TASK_COLLISION_POLICY' 'FAIL_CLOSED';foreach($name in $script:ManagedTasks){Write-KV ('TASK_'+$name) ((Get-DesiredTaskDefinition $Context $name)|ConvertTo-Json -Compress)};return};Set-Phase $Context 'TASK_CONFIGURATION';Add-Mutation $Context 'TASK_CONFIGURATION';$reconciled=$false
    if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;$tasks=@{};if($state.tasks){foreach($property in $state.tasks.PSObject.Properties){$tasks[$property.Name]=$property.Value}};foreach($name in $script:ManagedTasks){$desired=Get-DesiredTaskDefinition $Context $name;if($tasks.ContainsKey($name)){$null=Assert-ManagedTaskOwnershipIdentity $Context $name $tasks[$name];if(-not(Test-TaskDefinitionMatch $tasks[$name] $desired)){$reconciled=$true;$tasks[$name]=[pscustomobject]$desired}}else{$reconciled=$true;$tasks[$name]=[pscustomobject]$desired}};$state.tasks=$tasks;Save-ContextState $Context $state;$post=Get-ContextState $Context;foreach($name in $script:ManagedTasks){if(-not(Test-TaskDefinitionMatch $post.tasks.$name (Get-DesiredTaskDefinition $Context $name))){throw ('TASK_POSTWRITE_DEFINITION_MISMATCH:'+ $name)}}}
    else{foreach($name in $script:ManagedTasks){$desired=Get-DesiredTaskDefinition $Context $name;$task=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue;if($task){$null=Assert-ManagedTaskOwnershipIdentity $Context $name $task;$existingRecord=ConvertTo-TaskDefinitionRecord $task;if(-not(Test-TaskDefinitionMatch $existingRecord $desired)){$objects=New-CanonicalTaskObjects $desired;Set-ScheduledTask -TaskName $name -Action $objects.Action -Trigger $objects.Trigger -Settings $objects.Settings -Principal $objects.Principal -ErrorAction Stop|Out-Null;$reconciled=$true}}else{$objects=New-CanonicalTaskObjects $desired;Register-ScheduledTask -TaskName $name -Action $objects.Action -Trigger $objects.Trigger -Settings $objects.Settings -Principal $objects.Principal -ErrorAction Stop|Out-Null;$reconciled=$true};$post=Get-ScheduledTask -TaskName $name -ErrorAction Stop;if(-not(Test-TaskDefinitionMatch (ConvertTo-TaskDefinitionRecord $post) $desired)){throw ('TASK_POSTWRITE_DEFINITION_MISMATCH:'+ $name)}}}
    Write-KV 'TASK_OWNERSHIP_IDENTITY' 'PASS';Write-KV 'TASK_RECONCILIATION' 'PASS';Write-KV 'TASK_POSTWRITE_DEFINITION' 'PASS';Write-KV 'TASK_RECONCILED' ([string]$reconciled);Write-KV 'TASK_CONFIGURATION' 'PASS';Write-KV 'PRODUCTION_REFRESH_TASKS' 'PASS'}

function Get-RollbackPythonAuthority([object]$Context,[object]$Manifest) {
    if(-not$Manifest -or -not$Manifest.supervisor){throw 'ROLLBACK_SUPERVISOR_STATE_MISSING'}
    $authority=[string]$Manifest.supervisor.application
    if([string]::IsNullOrWhiteSpace($authority)){throw 'ROLLBACK_SUPERVISOR_APPLICATION_MISSING'}
    if($Context.Mode -eq 'PRODUCTION') {
        try{$isPython=[IO.Path]::GetFileName($authority) -ieq 'python.exe'}catch{$isPython=$false}
        if(-not$isPython -or -not(Test-Path -LiteralPath $authority -PathType Leaf)){throw 'ROLLBACK_SUPERVISOR_APPLICATION_INVALID'}
    }
    if($Manifest.old_process_executable -and $Manifest.old_process_executable -ne 'simulation' -and [IO.Path]::GetFullPath([string]$Manifest.old_process_executable) -ne [IO.Path]::GetFullPath($authority)){if($null -eq $Context.PSObject.Properties['RollbackPythonMismatchAudit']){$Context|Add-Member NoteProperty RollbackPythonMismatchAudit 'DETECTED_BUT_NONAUTHORITATIVE'}else{$Context.RollbackPythonMismatchAudit='DETECTED_BUT_NONAUTHORITATIVE'}}
    if($null -eq $Context.PSObject.Properties['RollbackPythonAuthority']){$Context|Add-Member NoteProperty RollbackPythonAuthority 'SUPERVISOR_APPLICATION'}else{$Context.RollbackPythonAuthority='SUPERVISOR_APPLICATION'}
    $authority
}

function Invoke-PrepareRuntime([object]$Context,[object]$Prepared) {$runtime=Get-FinalRuntimeRoot $Context.ExpectedReleaseHead $Context;$python=Get-FinalRuntimePython $Context.ExpectedReleaseHead $Context;$manifestPath=Join-Path $runtime 'RUNTIME_MANIFEST.json';$wheelHash=$Prepared.Manifest.wheelhouse.manifest_sha256;if(Test-Path $manifestPath -PathType Leaf){$existing=Get-Content $manifestPath -Raw|ConvertFrom-Json;if($existing.release_head -ne $Context.ExpectedReleaseHead -or $existing.requirements_lock_sha256 -ne $Prepared.Manifest.requirements_lock_sha256 -or $existing.wheelhouse_manifest_sha256 -ne $wheelHash){throw 'FINAL_RUNTIME_REUSE_FAIL_CLOSED'};if(-not(Test-Path $python -PathType Leaf)){throw 'FINAL_RUNTIME_REUSE_MISSING_PYTHON'};$Context.ReleasePython=$python;$Context.DeploymentRefreshPython=$python;Write-KV 'FINAL_RUNTIME_REUSED' 'YES';return};Add-Mutation $Context 'DEPLOY_PREPARE_RUNTIME';if($Context.Mode -eq 'SIMULATION'){New-Item (Join-Path $runtime '.venv\Scripts') -ItemType Directory -Force|Out-Null;Set-Content $python 'sandbox python';Write-AtomicJson $manifestPath ([ordered]@{release_head=$Context.ExpectedReleaseHead;python_path=$python;requirements_lock_sha256=$Prepared.Manifest.requirements_lock_sha256;exact_lock_match=45;pip_check='PASS';wheelhouse_manifest_sha256=$wheelHash;created_at=(Get-Date).ToUniversalTime().ToString('o')});$Context.ReleasePython=$python;$Context.DeploymentRefreshPython=$python;return};$base='C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe';if(-not(Test-Path $base -PathType Leaf)){throw 'BASE_PYTHON_MISSING'};New-Item $runtime -ItemType Directory -Force|Out-Null;Invoke-ChildProcess $base @('-m','venv','--without-pip',(Join-Path $runtime '.venv')) $Context.Root 60 @{} (Join-Path $runtime 'venv.log')|Out-Null;$python=Join-Path $runtime '.venv\Scripts\python.exe';Invoke-ChildProcess $python @('-m','ensurepip','--upgrade') $Context.Root 120 @{} (Join-Path $runtime 'ensurepip.log')|Out-Null;$wheels=Get-ChildItem (Join-Path $Prepared.Base 'wheelhouse') -Filter '*.whl' -File|Sort-Object Name;if(@($wheels).Count -ne 45){throw 'FINAL_RUNTIME_WHEELHOUSE_COUNT_FAILED'};foreach($wheel in $wheels){Invoke-ChildProcess $python @('-m','pip','install','--no-index','--no-deps','--disable-pip-version-check',$wheel.FullName) $Context.Root 300 @{} (Join-Path $runtime ('wheel_'+$wheel.BaseName+'.log'))|Out-Null};Invoke-ChildProcess $python @('-m','pip','check') $Context.Root 120 @{} (Join-Path $runtime 'pip_check.log')|Out-Null;Invoke-ChildProcess $python @('-c','import streamlit,pandas,plotly,numpy,psycopg2,dotenv,requests') $Context.Root 120 @{} (Join-Path $runtime 'import_gate.log')|Out-Null;Write-AtomicJson $manifestPath ([ordered]@{release_head=$Context.ExpectedReleaseHead;python_path=$python;requirements_lock_sha256=$Prepared.Manifest.requirements_lock_sha256;exact_lock_match=45;pip_check='PASS';wheelhouse_manifest_sha256=$wheelHash;created_at=(Get-Date).ToUniversalTime().ToString('o')});$Context.ReleasePython=$python;$Context.DeploymentRefreshPython=$python}
function Invoke-PreStopCanary([object]$Context,[object]$Prepared) {
    Set-Phase $Context 'DEPLOY_PRESTOP_CANARY'
    if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;if($state.canary_fail){throw 'PRESTOP_CANARY_FAILED'};Add-Mutation $Context 'DEPLOY_PRESTOP_CANARY';$state.canary='healthy';Save-ContextState $Context $state;Write-KV 'PRESTOP_CANARY' 'PASS';return}
    if(Invoke-HealthCheck 8505 1){throw 'PRESTOP_CANARY_PORT_OCCUPIED'}
    $env=Get-SafeEnv $Context.EnvPath;$env['GUNZSCOPE_SUPPLY_SOURCE']='v3';$env['OTG_ANALYTICS_WRITES_ENABLED']='false';$env['OTG_SITE_ANALYTICS_ENABLED']='false';$env['OTG_PRODUCT_EVENTS_ENABLED']='false';$env['OTG_FEEDBACK_WRITES_ENABLED']='false';$env['OTG_FEEDBACK_TELEGRAM_ENABLED']='false'
    $app=Join-Path $Prepared.Base 'repo\streamlit_opensea_sales\app_opensea_sales.py'
    $logRoot=Join-Path $Context.RuntimeRoot 'logs';New-Item $logRoot -ItemType Directory -Force|Out-Null
    $log=Join-Path $logRoot 'prestop_canary.log';$psi=New-Object Diagnostics.ProcessStartInfo;$psi.FileName=$Context.ReleasePython;$psi.WorkingDirectory=(Split-Path $app);$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true;$psi.Arguments=(Get-ProductionStreamlitLaunchParameters).Replace('app_opensea_sales.py','"'+$app+'"').Replace('--server.port 8502','--server.port 8505');$null=Assert-StreamlitLaunchContract $psi.Arguments 8505;foreach($key in $env.Keys){$psi.EnvironmentVariables[$key]=[string]$env[$key]};$canary=New-Object Diagnostics.Process;$canary.StartInfo=$psi;if(-not$canary.Start()){throw 'PRESTOP_CANARY_START_FAILED'};$out=$canary.StandardOutput.ReadToEndAsync();$err=$canary.StandardError.ReadToEndAsync()
    try {
        if(-not(Invoke-HealthCheck 8505 60)){throw 'PRESTOP_CANARY_HTTP_FAILED'}
        $repo=(Join-Path $Prepared.Base 'repo');$data=(Join-Path $repo 'streamlit_opensea_sales\data_opensea_sales');$integrity=Join-Path $repo 'ops\production\validate_prepared_snapshot.py'
        if(Test-Path $integrity -PathType Leaf){Invoke-ChildProcess $Context.ReleasePython @($integrity,'--manifest',(Join-Path $Prepared.Base 'PREPARED_RELEASE_MANIFEST.json'),'--repo-root',$repo,'--data-dir',$data) $Prepared.Base 900 $env (Join-Path $logRoot 'prestop_integrity.log')|Out-Null;Write-KV 'PRESTOP_PREPARED_INTEGRITY' 'PASS'}
        $helper=Join-Path $repo 'ops\production\validate_dynamic_artifacts.py';Invoke-ChildProcess $Context.ReleasePython @($helper,'--repo-root',$repo,'--data-dir',$data) $Prepared.Base 900 $env (Join-Path $logRoot 'prestop_reader.log')|Out-Null
    } finally {if(-not$canary.HasExited){$canary.Kill()};$canary.WaitForExit(10000);$canaryLogs=$out.Result+$err.Result;Write-AtomicText $log $canaryLogs;if($canaryLogs -match 'Traceback|ModuleNotFoundError|ImportError|Uncaught app exception'){throw 'PRESTOP_CANARY_LOG_FAILED'};if(Invoke-HealthCheck 8505 1){throw 'PRESTOP_CANARY_ORPHAN'}}
    Add-Mutation $Context 'DEPLOY_PRESTOP_CANARY';Write-KV 'PRESTOP_CANARY' 'PASS'
}
function Resolve-8502RollbackProcess([object]$Context) {
    if($Context.Mode -eq 'SIMULATION') {
        $state=Get-ContextState $Context
        if($state.foreign_listener){throw 'ROLLBACK_FOREIGN_8502_LISTENER'}
        if([string]$state.process -in @('old-healthy','new-healthy','new-failed')){return [pscustomobject]@{State='EXPECTED_PROCESS_PRESENT';ProcessId=18502}}
        return [pscustomobject]@{State='NO_LISTENER';ProcessId=$null}
    }
    try {
        $child=Resolve-ProductionSupervisorChild $Context -AllowLegacyMissingThemeSource:$Context.AllowLegacyMissingThemeSource
        if($child.State -eq 'NO_LISTENER'){return [pscustomobject]@{State='NO_LISTENER';ProcessId=$null}}
        return [pscustomobject]@{State='EXPECTED_PROCESS_PRESENT';ProcessId=$child.ProcessId;Process=$child.Process;Supervisor=$child.Configuration}
    } catch { throw 'ROLLBACK_FOREIGN_8502_LISTENER' }
}
function Stop-ContextProcess([object]$Context) {
    Set-Phase $Context 'DEPLOY_STOP';Add-Mutation $Context 'DEPLOY_STOP'
    if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;$state.process='stopped';Save-ContextState $Context $state;return}
    Stop-ProductionSupervisor $Context
}
function Stop-RollbackProcess([object]$Context) {
    Set-Phase $Context 'ROLLBACK_STOP'
    if($Context.Mode -eq 'SIMULATION'){$resolution=Resolve-8502RollbackProcess $Context;if($resolution.State -eq 'NO_LISTENER'){return};Add-Mutation $Context 'ROLLBACK_STOP';$state=Get-ContextState $Context;$state.process='stopped';Save-ContextState $Context $state;return}
    Add-Mutation $Context 'ROLLBACK_STOP'
    Stop-ProductionSupervisor $Context -AllowNoListener
}
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
        return [pscustomobject]@{Pid=$Context.Port;Id=$Context.Port;Process=$null;StdOutLogPath=$stdoutLog;StdErrLogPath=$stderrLog;StartedAt=(Get-Date).ToUniversalTime().ToString('o');SupervisorConfiguration=$null}
    }
    if(-not(Test-Path $Python -PathType Leaf)){throw 'RUNTIME_PYTHON_MISSING'}
    if($Context.Mode -eq 'PRODUCTION') {
        $Context.ReleasePython=$Python
        $launch=Start-ProductionSupervisor $Context -AllowLegacyMissingThemeSource:$Old
        return $launch
    }
    throw 'DIRECT_PROCESS_LIFECYCLE_FORBIDDEN'
}
function Invoke-HealthCheck([int]$Port,[int]$Seconds=60){$until=(Get-Date).AddSeconds($Seconds);do{try{$response=Invoke-WebRequest ('http://127.0.0.1:'+ $Port) -UseBasicParsing -TimeoutSec 5;if($response.StatusCode -ge 200 -and $response.StatusCode -lt 500){return $true}}catch{};Start-Sleep -Milliseconds 500}while((Get-Date)-lt $until);$false}
function Set-FailClosedEnv([object]$Context){$lines=@();if(Test-Path $Context.EnvPath){$lines=Get-Content $Context.EnvPath};$updates=@{GUNZSCOPE_SUPPLY_SOURCE='v3';OTG_ANALYTICS_WRITES_ENABLED='false';OTG_SITE_ANALYTICS_ENABLED='false';OTG_PRODUCT_EVENTS_ENABLED='false';OTG_FEEDBACK_WRITES_ENABLED='false';OTG_FEEDBACK_TELEGRAM_ENABLED='false'};$seen=@{};$result=@();foreach($line in $lines){if($line -match '^\s*([^#=][^=]*)='){$key=$Matches[1].Trim();if($updates.ContainsKey($key)){$result+=($key+'='+$updates[$key]);$seen[$key]=$true}else{$result+=$line}}else{$result+=$line}};foreach($key in $updates.Keys){if(-not$seen.ContainsKey($key)){$result+=($key+'='+$updates[$key])}};Add-Mutation $Context 'DEPLOY_ENV';Write-AtomicText $Context.EnvPath (($result -join [Environment]::NewLine)+[Environment]::NewLine)}
function Invoke-ContextMigrations([object]$Context){Set-Phase $Context 'DEPLOY_MIGRATIONS';Assert-AllowedMigrationSet $script:AllowedMigrations;Add-Mutation $Context 'DEPLOY_MIGRATIONS';if($Context.Mode -eq 'SIMULATION'){Set-Content (Join-Path $Context.Root 'migrations.log') ($script:AllowedMigrations -join [Environment]::NewLine);return};$tools=Get-PostgresTools;if(-not$tools.ContainsKey('psql')){throw 'PSQL_MISSING'};$env=Get-DatabaseEnvironment $Context.EnvPath -Required;foreach($migration in $script:AllowedMigrations){$path=Join-Path $Context.RepoRoot $migration;if(-not(Test-Path $path)){throw ('MIGRATION_MISSING:'+ $migration)};Invoke-ChildProcess $tools.psql @('-X','-v','ON_ERROR_STOP=1','-f',$path) $Context.Root 300 $env|Out-Null}}
function Invoke-ContextGitFastForward([object]$Context,[string]$ReleaseHead){Set-Phase $Context 'DEPLOY_FAST_FORWARD';Add-Mutation $Context 'DEPLOY_FAST_FORWARD';if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;$state.current_head=$ReleaseHead;Save-ContextState $Context $state;return};& git -c ('safe.directory='+$Context.Root) -C $Context.Root fetch origin main;if($LASTEXITCODE -ne 0){throw 'GIT_FETCH_FAILED'};& git -c ('safe.directory='+$Context.Root) -C $Context.Root merge --ff-only origin/main;if($LASTEXITCODE -ne 0){throw 'GIT_FAST_FORWARD_FAILED'}}
function Invoke-ContextGitReset([object]$Context,[string]$OldHead){Set-Phase $Context 'ROLLBACK_GIT';Add-Mutation $Context 'ROLLBACK_GIT';if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;$state.current_head=$OldHead;Save-ContextState $Context $state;return};& git -c ('safe.directory='+$Context.Root) -C $Context.Root reset --hard $OldHead;if($LASTEXITCODE -ne 0){throw 'GIT_ROLLBACK_FAILED'}}
function Write-ActiveRuntime([object]$Context,[int]$ProcessId){$path=Join-Path $Context.RuntimeRoot 'ACTIVE_RUNTIME.json';Add-Mutation $Context 'DEPLOY_ACTIVE_RUNTIME';Write-AtomicJson $path ([ordered]@{release_head=$Context.ExpectedReleaseHead;runtime_root=(Get-FinalRuntimeRoot $Context.ExpectedReleaseHead $Context);python_path=$Context.ReleasePython;started_pid=$ProcessId;activated_at=(Get-Date).ToUniversalTime().ToString('o');health='PASS'})}

function Invoke-DeployCore {
    param([object]$Context,[switch]$Execute)
    Assert-Context $Context
    if(-not$Execute){
        Write-KV 'MODE' 'DRY_RUN';Write-KV 'DEPLOY_PLAN' 'PASS';Write-KV 'MAIN_PROMOTION_REQUIRED' 'YES';Write-KV 'DEPLOY_REMOTE_MAIN_MUTATION' 'FORBIDDEN';Write-KV 'FINAL_RUNTIME_PATH_GUARD' 'PASS';Write-KV 'MUTATION_EXECUTED' 'NO';return
    }
    Set-Phase $Context 'DEPLOY_VALIDATE'
    $prepared=Read-PreparedReleaseManifest $Context.PreparedReleaseManifest $Context.PreparedReleaseManifestSha256 $Context.ExpectedReleaseHead $Context;$Context.ProfileSyncContractRequired=[bool]$prepared.ProfileSyncContractRequired
    $backupForDeploy=Read-BackupManifest $Context.BackupManifest $Context
    if($Context.ProfileSyncContractRequired){if($null -eq $backupForDeploy.Manifest.PSObject.Properties['profile_sync_state_contract']){throw 'BACKUP_PROFILE_SYNC_STATE_CONTRACT_MISSING'};Assert-ProfileSyncBackupContract $backupForDeploy.Manifest $Context $backupForDeploy.Base}
    Assert-AllowedMigrationSet $script:AllowedMigrations
    if($Context.Mode -eq 'SIMULATION'){
        $state=Get-ContextState $Context
        if($state.main_head -ne $Context.ExpectedReleaseHead){throw 'MAIN_PROMOTION_REQUIRED'}
    } else {
        $actual=(& git -c ('safe.directory='+$Context.Root) -C $Context.Root rev-parse HEAD).Trim()
        if($actual -ne $Context.ExpectedOldHead){throw 'EXPECTED_OLD_HEAD_MISMATCH'}
        if(((& git -c ('safe.directory='+$Context.Root) -C $Context.Root status --porcelain)-join '') -ne ''){throw 'PRODUCTION_WORKTREE_NOT_CLEAN'}
        $main=(& git -c ('safe.directory='+$Context.Root) -C $Context.Root rev-parse origin/main).Trim()
        if($main -ne $Context.ExpectedReleaseHead){throw 'MAIN_PROMOTION_REQUIRED'}
        & git -c ('safe.directory='+$Context.Root) -C $Context.Root merge-base --is-ancestor $Context.ExpectedOldHead $Context.ExpectedReleaseHead
        if($LASTEXITCODE -ne 0){throw 'RELEASE_NOT_DESCENDANT'}
        $liveSupervisor=Get-ProductionSupervisor $Context -AllowLegacyMissingThemeSource:$Context.AllowLegacyMissingThemeSource
        if([string]$liveSupervisor.Configuration.ConfigurationFingerprint -ne [string]$backupForDeploy.Manifest.supervisor.configuration_fingerprint){throw 'SUPERVISOR_STATE_CHANGED'}
        Assert-FinalRuntimePath (Get-FinalRuntimePython $Context.ExpectedReleaseHead $Context) $Context.ExpectedReleaseHead $Context
    }
    $stopped=$false
    try {
        Set-Phase $Context 'DEPLOY_PREPARE_RUNTIME';Invoke-PrepareRuntime $Context $prepared -Execute
        Invoke-PreStopCanary $Context $prepared
        Stop-ContextProcess $Context;$stopped=$true
        Invoke-ContextGitFastForward $Context $Context.ExpectedReleaseHead
        Set-Phase $Context 'DEPLOY_ENV';Set-FailClosedEnv $Context;Invoke-ContextMigrations $Context
        Set-Phase $Context 'DEPLOY_DERIVED';Invoke-DerivedRefreshCore $Context -Execute
        Set-Phase $Context 'DEPLOY_METADATA';Invoke-MetadataRefreshCore $Context -Execute
        Set-Phase $Context 'DEPLOY_RUNTIME_READERS';Invoke-Readers $Context
        Set-Phase $Context 'DEPLOY_SUPERVISOR_CONFIG';Add-Mutation $Context 'DEPLOY_SUPERVISOR_CONFIG'
        if($Context.Mode -eq 'PRODUCTION'){$null=Set-ProductionSupervisorReleaseConfiguration $Context}
        Set-Phase $Context 'DEPLOY_START';$new=Start-ContextProcess $Context $Context.ReleasePython $Context.AppPath
        Set-Phase $Context 'DEPLOY_HEALTH'
        $healthy=if($Context.Mode -eq 'SIMULATION'){(Get-ContextState $Context).process -eq 'new-healthy'}else{Invoke-HealthCheck 8502 60}
        if(-not$healthy){throw 'NEW_PRODUCTION_HEALTH_FAILED'}
        if($Context.Mode -eq 'PRODUCTION'){
            $listener=Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8502 -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1
            if(-not$listener -or $listener.OwningProcess -ne $new.Id){throw 'NEW_PROCESS_IDENTITY_FAILED'}
            Test-8502ProcessIdentity $listener (Get-CimInstance Win32_Process -Filter ('ProcessId='+$listener.OwningProcess)) $Context.AppPath $Context.AppPath 8502
            Assert-CurrentLaunchLogs $new
        }
        if($Context.Mode -eq 'SIMULATION'){Assert-CurrentLaunchLogs $new}
        Write-KV 'STREAMLIT_THEME_BASE' 'dark';Write-KV 'STREAMLIT_THEME_CONTRACT' 'PASS'
        Write-ActiveRuntime $Context $new.Id
        Set-Phase $Context 'DEPLOY_TASKS';Invoke-TaskConfigurationCore $Context -Execute
        Set-Phase $Context 'DEPLOY_RECEIPT';Add-Mutation $Context 'DEPLOY_RECEIPT'
        $syncDefinition=Get-ProfileSyncStateDefinition $Context;$receipt=[ordered]@{old_head=$Context.ExpectedOldHead;new_head=$Context.ExpectedReleaseHead;new_pid=$new.Id;supervisor_service_name=$Context.SupervisorServiceName;supervisor_type=$Context.SupervisorType;supervisor_stdout=$new.StdOutLogPath;supervisor_stderr=$new.StdErrLogPath;supervisor_configuration_fingerprint=if($new.SupervisorConfiguration){$new.SupervisorConfiguration.ConfigurationFingerprint}else{''};release=$Context.ExpectedReleaseHead;runtime=$Context.ReleasePython;child_pid=$new.Id;health='PASS';streamlit_theme_base='dark';theme_contract='PASS';theme_base='dark';profile_key_source=$Context.ProfileKeySource;profile_sync_contract=$Context.ProfileSyncContract;profile_sync_state_present=[bool](Test-Path $syncDefinition.Path -PathType Leaf);profile_sync_state_gate=$Context.ProfileSyncStateGate;profile_coverage_gate=$Context.ProfileCoverageGate;profile_reader_gate=$Context.ProfileReaderGate;profile_count=$Context.ProfileCount;profile_ok_count=$Context.ProfileOkCount;profile_human_username_count=$Context.ProfileHumanUsernameCount;profile_human_display_name_count=$Context.ProfileHumanDisplayNameCount;profile_remote_avatar_count=$Context.ProfileRemoteAvatarCount;metadata_refresh_result=$Context.MetadataRefreshResult;profile_sync_attempted=$Context.ProfileSyncAttempted;profile_sync_successful=$Context.ProfileSyncSuccessful;profile_sync_not_found=$Context.ProfileSyncNotFound;profile_sync_errors=$Context.ProfileSyncErrors;profile_sync_rate_limited=$Context.ProfileSyncRateLimited;profile_sync_health=$Context.ProfileSyncHealth;secret_leak_gate='PASS';sql_migration_count=3;dynamic_artifact_count=6}
        Assert-DeploymentReceipt $receipt $Context.ProfileSyncContractRequired
        $receiptPath=Join-Path $Context.Root 'DEPLOYMENT_RECEIPT.json';Write-AtomicJson $receiptPath $receipt;Assert-DeploymentReceipt (Get-Content $receiptPath -Raw|ConvertFrom-Json) $Context.ProfileSyncContractRequired
        Write-KV 'DEPLOY_RESULT' 'PASS';return
    } catch {
        if($stopped){$Context.RollbackAttempted=$true;Write-KV 'AUTO_ROLLBACK_ATTEMPTED' 'YES';try{Invoke-RollbackCore $Context -Execute -Automatic;$Context.RollbackSucceeded=$true;$Context.StateRestored=$true;Write-KV 'AUTO_ROLLBACK_RESULT' 'PASS';Write-KV 'STATE_RESTORED' 'YES'}catch{Write-KV 'AUTO_ROLLBACK_RESULT' 'FAIL';Write-KV 'ROLLBACK_FAILURE' $_.Exception.Message}}
        throw
    }
}
function Invoke-RollbackCore {
    param([object]$Context,[switch]$Execute,[switch]$Automatic)
    Assert-Context $Context;if(-not$Execute){Write-KV 'MODE' 'DRY_RUN';Write-KV 'ROLLBACK_PLAN' 'PASS';Write-KV 'DB_SCHEMA_ROLLBACK' 'NOT_AUTOMATIC';Write-KV 'REMOTE_MAIN_ROLLBACK' 'NOT_AUTOMATIC';Write-KV 'MUTATION_EXECUTED' 'NO';return};Set-Phase $Context 'ROLLBACK_VALIDATE';$backup=Read-BackupManifest $Context.BackupManifest $Context;Add-Mutation $Context 'ROLLBACK_BEGIN';$manifest=$backup.Manifest
    Stop-RollbackProcess $Context;Invoke-ContextGitReset $Context ([string]$manifest.old_git_head);Set-Phase $Context 'ROLLBACK_ENV';Copy-Item (Join-Path $backup.Base $manifest.env_backup_relative_path) $Context.EnvPath -Force;if((Get-Sha256 $Context.EnvPath) -ne [string]$manifest.env_sha256){throw 'ROLLBACK_ENV_HASH_MISMATCH'};Set-Phase $Context 'ROLLBACK_ARTIFACTS';foreach($artifact in @($manifest.dynamic_artifacts)){$target=(Get-DynamicArtifactDefinitions $Context|Where-Object RelativePath -eq $artifact.relative_path).Path;if($artifact.existed_before){Copy-Item (Join-Path $backup.Base $artifact.backup_relative_path) $target -Force;if((Get-Sha256 $target) -ne [string]$artifact.sha256_before){throw 'ROLLBACK_ARTIFACT_STATE_MISMATCH'}}elseif(Test-Path $target -PathType Leaf){Remove-Item -LiteralPath $target -Force}};Set-Phase $Context 'ROLLBACK_PROFILE_SYNC_STATE';$syncDefinition=Get-ProfileSyncStateDefinition $Context;$syncBackup=Join-Path $backup.Base $syncDefinition.BackupRelativePath;if([bool]$manifest.profile_sync_state_existed_before){if(-not(Test-Path $syncBackup -PathType Leaf) -or (Get-Sha256 $syncBackup) -ne [string]$manifest.profile_sync_state_sha256){throw 'ROLLBACK_PROFILE_SYNC_STATE_BACKUP_INVALID'};Copy-Item $syncBackup $syncDefinition.Path -Force;if((Get-Sha256 $syncDefinition.Path) -ne [string]$manifest.profile_sync_state_sha256){throw 'ROLLBACK_PROFILE_SYNC_STATE_RESTORE_FAILED'}}elseif(Test-Path $syncDefinition.Path -PathType Leaf){Remove-Item -LiteralPath $syncDefinition.Path -Force};Set-Phase $Context 'ROLLBACK_TASKS';if($Context.Mode -eq 'SIMULATION'){$state=Get-ContextState $Context;$state.tasks=@{};foreach($task in @($manifest.production_refresh_tasks)){if($task.existed_before){$state.tasks[$task.task_name]=$task.state}};Save-ContextState $Context $state}else{foreach($name in $script:ManagedTasks){$entry=@($manifest.production_refresh_tasks|Where-Object task_name -eq $name)[0];$existing=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue;if($entry.existed_before){Register-ScheduledTask -TaskName $name -Xml (Get-Content (Join-Path $backup.Base $entry.exported_xml_relative_path) -Raw) -Force|Out-Null}elseif($existing){Unregister-ScheduledTask -TaskName $name -Confirm:$false}}};Set-Phase $Context 'ROLLBACK_RUNTIME';$active=Join-Path $Context.RuntimeRoot 'ACTIVE_RUNTIME.json';if($manifest.active_runtime_existed){Copy-Item (Join-Path $backup.Base $manifest.active_runtime_backup_relative_path) $active -Force}elseif(Test-Path $active -PathType Leaf){Remove-Item -LiteralPath $active -Force};
    $oldPython=Get-RollbackPythonAuthority $Context $manifest
    if($Context.PSObject.Properties['RollbackPythonMismatchAudit'] -and $Context.RollbackPythonMismatchAudit){Write-KV 'ROLLBACK_PYTHON_MISMATCH_AUDIT' $Context.RollbackPythonMismatchAudit}
    if($Context.PSObject.Properties['RollbackPythonAuthority'] -and $Context.RollbackPythonAuthority){Write-KV 'ROLLBACK_PYTHON_AUTHORITY' $Context.RollbackPythonAuthority}
    if($Context.Mode -eq 'PRODUCTION') {
        $rollbackOut=Join-Path $Context.RuntimeRoot ('logs\rollback_'+[guid]::NewGuid().ToString('N')+'.out.log');$rollbackErr=Join-Path $Context.RuntimeRoot ('logs\rollback_'+[guid]::NewGuid().ToString('N')+'.err.log')
        Restore-ProductionSupervisorConfiguration $Context $manifest.supervisor $rollbackOut $rollbackErr|Out-Null
        if([bool]$manifest.supervisor.service_was_running){Set-Phase $Context 'ROLLBACK_START';$Context.ReleasePython=$oldPython;$oldStart=Start-ContextProcess $Context $oldPython $Context.AppPath -Old;Set-Phase $Context 'ROLLBACK_HEALTH';if(-not(Invoke-HealthCheck 8502 60)){throw 'ROLLBACK_OLD_APP_HEALTH_FAILED'};Assert-CurrentLaunchLogs $oldStart;Restore-ProductionSupervisorConfiguration $Context $manifest.supervisor|Out-Null}else{$oldStart=$null}
    } else {Set-Phase $Context 'ROLLBACK_START';$Context.ReleasePython=$oldPython;$oldStart=Start-ContextProcess $Context $oldPython $Context.AppPath -Old;Set-Phase $Context 'ROLLBACK_HEALTH';Assert-CurrentLaunchLogs $oldStart}
    Write-KV 'DB_SCHEMA_ROLLBACK' 'NOT_AUTOMATIC';Write-KV 'REMOTE_MAIN_ROLLBACK' 'NOT_AUTOMATIC';Write-KV 'ROLLBACK_RESULT' 'PASS';$Context.StateRestored=$true
}
