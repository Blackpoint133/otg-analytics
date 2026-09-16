[CmdletBinding()]
param([switch]$Execute)

$ErrorActionPreference='Stop'
$Ops=$PSScriptRoot
$SandboxRoot='C:\VAMBAM\Projects\OTG\DEV\production_tooling_sandbox_122'
$Port=$null
$ServiceName=$null
$Nssm=$null
$Python=$null
$ForeignPid=$null
$ServiceCreated=$false
$SandboxPath=$null

function Say([string]$Name,[object]$Value){Write-Output ($Name+'='+[string]$Value)}
function Run-Nssm([string[]]$Arguments){Invoke-ChildProcess $Nssm $Arguments $SandboxPath 60 @{}|Out-Null}
function Set-SandboxNssm([string]$Parameter,[string]$Value){Run-Nssm @('set',$ServiceName,$Parameter,$Value)}
function Get-SandboxListener {
    Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1
}
function Wait-SandboxListener([bool]$Present,[int]$TimeoutSeconds=30) {
    $until=(Get-Date).AddSeconds($TimeoutSeconds)
    do {$listener=Get-SandboxListener;if($Present -and $listener){return $listener};if(-not$Present -and -not$listener){return $null};Start-Sleep -Milliseconds 250} while((Get-Date)-lt $until)
    throw $(if($Present){'SANDBOX_LISTENER_START_TIMEOUT'}else{'SANDBOX_LISTENER_RELEASE_TIMEOUT'})
}
function Get-SandboxChild {
    $ctx=[pscustomobject]@{Mode='PRODUCTION';Root=$SandboxPath;RuntimeRoot=(Join-Path $SandboxPath 'runtime');AppPath=(Join-Path $SandboxPath 'app_opensea_sales.py');Port=$Port;SupervisorServiceName=$ServiceName;SupervisorType='NSSM';SupervisorAppDirectory=$SandboxPath;ExpectedReleaseHead='sandbox';ReleasePython=$Python;SupervisorNssmExecutable='';SupervisorConfiguration=$null;SupervisorActivationStdOut='';SupervisorActivationStdErr=''}
    $until=(Get-Date).AddSeconds(30);$resolved=$null;$last=$null
    do {try{$resolved=Resolve-ProductionSupervisorChild $ctx;if($resolved.State -eq 'EXPECTED_PROCESS_PRESENT'){break}}catch{$last=$_};Start-Sleep -Milliseconds 500} while((Get-Date)-lt $until)
    if(-not$resolved -or $resolved.State -ne 'EXPECTED_PROCESS_PRESENT'){if($last){throw $last};throw 'SANDBOX_EXPECTED_CHILD_MISSING'}
    [pscustomobject]@{Context=$ctx;Resolved=$resolved;Configuration=$resolved.Configuration;Process=$resolved.Process;Listener=$resolved.Listener}
}
function Config-Projection([object]$Configuration) {
    [ordered]@{ServiceName=$Configuration.ServiceName;ServiceDisplayName=$Configuration.ServiceDisplayName;ServiceStartMode=$Configuration.ServiceStartMode;ServiceBinaryPath=$Configuration.ServiceBinaryPath;NssmExecutable=$Configuration.NssmExecutable;Application=$Configuration.Application;AppDirectory=$Configuration.AppDirectory;AppParameters=$Configuration.AppParameters;AppStdout=$Configuration.AppStdout;AppStderr=$Configuration.AppStderr;AppRestartDelay=$Configuration.AppRestartDelay;AppThrottle=$Configuration.AppThrottle;AppExitDefault=$Configuration.AppExitDefault;AppStopMethodConsole=$Configuration.AppStopMethodConsole;AppStopMethodWindow=$Configuration.AppStopMethodWindow;AppStopMethodThreads=$Configuration.AppStopMethodThreads;AppStopMethodSkip=$Configuration.AppStopMethodSkip;AppKillProcessTree=$Configuration.AppKillProcessTree;AppStdoutShareMode=$Configuration.AppStdoutShareMode;AppStderrShareMode=$Configuration.AppStderrShareMode;AppRotateFiles=$Configuration.AppRotateFiles;AppRotateOnline=$Configuration.AppRotateOnline;AppRotateSeconds=$Configuration.AppRotateSeconds;AppRotateBytes=$Configuration.AppRotateBytes;AppTimestampLog=$Configuration.AppTimestampLog;WindowsServiceFailureActions=$Configuration.WindowsServiceFailureActions}
}
function Assert-ConfigEqual([object]$Expected,[object]$Actual) {
    $left=(Config-Projection $Expected|ConvertTo-Json -Compress -Depth 20);$right=(Config-Projection $Actual|ConvertTo-Json -Compress -Depth 20)
    if($left -ne $right){throw 'SANDBOX_SUPERVISOR_CONFIG_NOT_RESTORED'}
}
function Configure-Logs([string]$Prefix) {
    $out=Join-Path $SandboxPath ('logs\'+$Prefix+'.out.log');$err=Join-Path $SandboxPath ('logs\'+$Prefix+'.err.log')
    Set-SandboxNssm 'AppStdout' $out;Set-SandboxNssm 'AppStderr' $err
    [pscustomobject]@{StdOutLogPath=$out;StdErrLogPath=$err}
}
function Assert-SandboxLaunch([object]$Launch,[string]$ExpectedApp) {
    if(-not$Launch.ProcessId){throw 'SANDBOX_CHILD_PID_MISSING'}
    $listener=Wait-SandboxListener $true
    if([int]$listener.OwningProcess -ne [int]$Launch.ProcessId){throw 'SANDBOX_LISTENER_PID_MISMATCH'}
    $process=Get-CimInstance Win32_Process -Filter ('ProcessId='+$listener.OwningProcess)
    $null=Test-8502ProcessIdentity $listener $process $ExpectedApp '' $Port
    Assert-CurrentLaunchLogs $Launch
    if(-not(Invoke-HealthCheck $Port 10)){throw 'SANDBOX_HEALTH_FAILED'}
}

if(-not$Execute){Say 'MODE' 'DRY_RUN';Say 'MUTATION_EXECUTED' 'NO';exit 0}
try {
    . (Join-Path $Ops 'production_update_common.ps1')
    if(-not(Test-Path $SandboxRoot -PathType Container)){New-Item -ItemType Directory -Path $SandboxRoot -Force|Out-Null}
    for($candidate=18520;$candidate -le 18620;$candidate++){$busy=Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $candidate -ErrorAction SilentlyContinue;if(-not$busy){$Port=$candidate;break}}
    if(-not$Port){throw 'SANDBOX_NO_UNUSED_PORT'}
    $id=[guid]::NewGuid().ToString('N').Substring(0,10);$ServiceName='OTG_Analytics_Sandbox_122_'+$id;$SandboxPath=Join-Path $SandboxRoot $id
    New-Item -ItemType Directory -Path $SandboxPath,(Join-Path $SandboxPath 'logs'),(Join-Path $SandboxPath 'runtime') -Force|Out-Null
    $app=Join-Path $SandboxPath 'app_opensea_sales.py';Set-Content -LiteralPath $app -Value "import streamlit as st`nst.title('NSSM sandbox')`n"
    $Python=(Get-Command python.exe -ErrorAction Stop).Source
    $service=Get-CimInstance Win32_Service -Filter "Name='$($script:ProductionServiceName)'";if(-not$service){throw 'SANDBOX_SOURCE_SERVICE_MISSING'};$Nssm=Get-SupervisorNssmExecutable $service
    Run-Nssm @('install',$ServiceName,$Python);$ServiceCreated=$true
    $parameters=(Get-ProductionStreamlitLaunchParameters).Replace('--server.port 8502','--server.port '+$Port);$null=Assert-StreamlitLaunchContract $parameters $Port
    Run-Nssm @('set',$ServiceName,'AppDirectory',$SandboxPath);Run-Nssm @('set',$ServiceName,'AppParameters',$parameters);Run-Nssm @('set',$ServiceName,'AppRestartDelay','0');Run-Nssm @('set',$ServiceName,'AppThrottle','1500')
    $oldLogs=Configure-Logs 'old_activation';& sc.exe config $ServiceName start= demand|Out-Null
    Start-Service -Name $ServiceName -ErrorAction Stop
    $old=Get-SandboxChild
    Assert-SandboxLaunch ([pscustomobject]@{ProcessId=$old.Process.ProcessId;StdOutLogPath=$old.Configuration.AppStdout;StdErrLogPath=$old.Configuration.AppStderr}) $app
    Say 'SANDBOX_SERVICE_INITIAL_START' 'PASS';Say 'SANDBOX_SERVICE_TO_CHILD_OWNERSHIP' 'PASS'

    $firstPid=$old.Process.ProcessId;Stop-Process -Id $firstPid -Force -ErrorAction Stop
    $respawned=$null;$until=(Get-Date).AddSeconds(20);do{Start-Sleep -Milliseconds 500;try{$respawned=Get-SandboxChild}catch{$respawned=$null}}while(-not$respawned -and (Get-Date)-lt $until)
    if(-not$respawned -or [int]$respawned.Process.ProcessId -eq [int]$firstPid -or (Get-Service -Name $ServiceName).Status -ne 'Running'){throw 'SANDBOX_NSSM_RESPAWN_FAILED'}
    Say 'SANDBOX_NSSM_RESPAWN_REPRODUCTION' 'PASS'

    Stop-ProductionSupervisor $old.Context;Say 'SANDBOX_SUPERVISOR_STOP' 'PASS';Wait-SandboxListener $false|Out-Null;Say 'SANDBOX_PORT_RELEASE' 'PASS'
    $saved=$old.Configuration;$requiredBackupFields=@('ServiceName','ServiceDisplayName','ServiceStartMode','ServiceBinaryPath','NssmExecutable','Application','AppDirectory','AppParameters','AppStdout','AppStderr','AppRestartDelay','AppThrottle','AppExitDefault','AppStopMethodConsole','AppStopMethodWindow','AppStopMethodThreads','AppStopMethodSkip','AppKillProcessTree','AppStdoutShareMode','AppStderrShareMode','AppRotateFiles','AppRotateOnline','AppRotateSeconds','AppRotateBytes','AppTimestampLog','WindowsServiceFailureActions');foreach($field in $requiredBackupFields){if($null -eq $saved.PSObject.Properties[$field]){throw 'SANDBOX_SUPERVISOR_BACKUP_INCOMPLETE'}};Write-AtomicJson (Join-Path $SandboxPath 'SUPERVISOR_BACKUP.json') (Config-Projection $saved);Say 'SANDBOX_SUPERVISOR_BACKUP' 'PASS'
    $invalidParameters=$parameters.Replace('--theme.base="dark"','--theme.base=light');Set-SandboxNssm 'AppParameters' $invalidParameters;$invalidConfiguration=Get-ProductionSupervisorConfiguration $old.Context;$invalidRejected=$false;try{$null=Assert-ProductionSupervisorIdentity $old.Context $invalidConfiguration}catch{if($_.Exception.Message -eq 'SUPERVISOR_THEME_BASE_DARK_REQUIRED'){$invalidRejected=$true}};if(-not$invalidRejected){throw 'SANDBOX_INVALID_THEME_NOT_REJECTED'};Say 'SANDBOX_INVALID_THEME_FAIL_CLOSED' 'PASS';Set-SandboxNssm 'AppParameters' $parameters
    $stale=Join-Path $SandboxPath 'logs\stale_previous_launch.err.log';Set-Content $stale 'Traceback from a previous launch'
    $newLogs=Configure-Logs ('new_activation_'+[guid]::NewGuid().ToString('N'));$newConfig=Get-ProductionSupervisorConfiguration $old.Context
    if($newConfig.AppStdout -ne $newLogs.StdOutLogPath -or $newConfig.AppStderr -ne $newLogs.StdErrLogPath){throw 'SANDBOX_LOG_CONFIGURATION_FAILED'}
    Say 'SANDBOX_SUPERVISOR_RECONFIGURE' 'PASS';Start-Service -Name $ServiceName -ErrorAction Stop
    try{$new=Get-SandboxChild}catch{$cfg=Get-ProductionSupervisorConfiguration $old.Context;$listener=Get-SandboxListener;$debugError='MISSING';if(Test-Path $cfg.AppStderr){$debugError=Get-Content $cfg.AppStderr -Raw};Say 'SANDBOX_DEBUG_NEW_SERVICE_STATE' $cfg.ServiceState;Say 'SANDBOX_DEBUG_NEW_APPLICATION' $cfg.Application;Say 'SANDBOX_DEBUG_NEW_PARAMETERS' $cfg.AppParameters;Say 'SANDBOX_DEBUG_NEW_LISTENER' ($listener|Out-String);Say 'SANDBOX_DEBUG_NEW_STDERR' $debugError;throw};$newLaunch=[pscustomobject]@{ProcessId=$new.Process.ProcessId;StdOutLogPath=$new.Configuration.AppStdout;StdErrLogPath=$new.Configuration.AppStderr};Assert-SandboxLaunch $newLaunch $app
    if(([string]$new.Configuration.AppParameters) -notmatch '(?i)(?:^|\s)--theme\.base(?:\s+|=)(?:"dark"|dark)(?:\s|$)'){throw 'SANDBOX_THEME_CONTRACT_FAILED'};Say 'SANDBOX_SUPERVISOR_START' 'PASS';Say 'SANDBOX_NEW_CHILD_IDENTITY' 'PASS';Say 'SANDBOX_NEW_CHILD_HEALTH' 'PASS';Say 'SANDBOX_CURRENT_LOG_GATE' 'PASS';Say 'SANDBOX_STALE_LOG_IGNORED' 'PASS';Say 'SANDBOX_THEME_CONTRACT' 'PASS'
    $listeners=@(Get-SandboxListener);if($listeners.Count -ne 1){throw 'SANDBOX_DUPLICATE_CHILD'};Say 'SANDBOX_DUPLICATE_CHILD' 'NO'

    Stop-ProductionSupervisor $new.Context;Say 'SANDBOX_ROLLBACK_SUPERVISOR_STOP' 'PASS';Wait-SandboxListener $false|Out-Null
    $rollbackLogs=Join-Path $SandboxPath ('logs\rollback_activation_'+[guid]::NewGuid().ToString('N'));$rollbackOut=$rollbackLogs+'.out.log';$rollbackErr=$rollbackLogs+'.err.log'
    Restore-ProductionSupervisorConfiguration $new.Context $saved $rollbackOut $rollbackErr|Out-Null;Say 'SANDBOX_ROLLBACK_CONFIG_RESTORE' 'PASS';Start-Service -Name $ServiceName -ErrorAction Stop
    $rollback=Get-SandboxChild;$rollbackLaunch=[pscustomobject]@{ProcessId=$rollback.Process.ProcessId;StdOutLogPath=$rollbackOut;StdErrLogPath=$rollbackErr};Assert-SandboxLaunch $rollbackLaunch $app
    Say 'SANDBOX_ROLLBACK_SERVICE_START' 'PASS';Say 'SANDBOX_ROLLBACK_CHILD_IDENTITY' 'PASS';Say 'SANDBOX_ROLLBACK_HEALTH' 'PASS';Say 'SANDBOX_ROLLBACK_LOG_GATE' 'PASS'
    Restore-ProductionSupervisorConfiguration $rollback.Context $saved|Out-Null;Assert-ConfigEqual $saved (Get-ProductionSupervisorConfiguration $rollback.Context);Say 'SANDBOX_ROLLBACK_STATE_RESTORED' 'PASS'

    Stop-ProductionSupervisor $rollback.Context;Wait-SandboxListener $false|Out-Null
    $foreign=Join-Path $SandboxPath 'foreign.py';Set-Content -LiteralPath $foreign -Value "import http.server,sys`nhttp.server.HTTPServer(('127.0.0.1',int(sys.argv[1])),http.server.SimpleHTTPRequestHandler).serve_forever()"
    $foreignProcess=Start-Process -FilePath $Python -ArgumentList @($foreign,[string]$Port) -WorkingDirectory $SandboxPath -WindowStyle Hidden -PassThru
    $ForeignPid=$foreignProcess.Id;Wait-SandboxListener $true|Out-Null
    $foreignFailed=$false;try{$null=Resolve-ProductionSupervisorChild $rollback.Context}catch{if($_.Exception.Message -match 'SUPERVISOR|FOREIGN'){$foreignFailed=$true}}
    if(-not$foreignFailed -or -not(Get-Process -Id $ForeignPid -ErrorAction SilentlyContinue)){throw 'SANDBOX_FOREIGN_LISTENER_GUARD_FAILED'}
    Say 'SANDBOX_FOREIGN_LISTENER_DETECTED' 'YES';Say 'SANDBOX_FOREIGN_PROCESS_UNTOUCHED' 'YES';Say 'SANDBOX_FOREIGN_LISTENER_GATE' 'PASS'
}
finally {
    if($ForeignPid){Stop-Process -Id $ForeignPid -Force -ErrorAction SilentlyContinue}
    if($ServiceCreated){$ErrorActionPreference='Continue';Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue;for($i=0;$i-lt 20;$i++){Start-Sleep -Milliseconds 250;$serviceNow=Get-Service -Name $ServiceName -ErrorAction SilentlyContinue;$listenNow=Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue;if(((-not$serviceNow) -or $serviceNow.Status -eq 'Stopped') -and -not$listenNow){break}};$ownedSandbox=Get-CimInstance Win32_Process -ErrorAction SilentlyContinue|Where-Object {$_.ProcessId -ne $PID -and $_.CommandLine -and $_.CommandLine -match [regex]::Escape($SandboxPath)};foreach($owned in @($ownedSandbox)){Stop-Process -Id $owned.ProcessId -Force -ErrorAction SilentlyContinue};& $Nssm remove $ServiceName confirm|Out-Null;$ErrorActionPreference='Stop'}
    if($SandboxPath -and (Test-Path $SandboxPath)){Remove-Item -LiteralPath $SandboxPath -Recurse -Force -ErrorAction SilentlyContinue}
    $serviceLeft=if($ServiceName){Get-Service -Name $ServiceName -ErrorAction SilentlyContinue}else{$null};$listenerLeft=if($Port){Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue}else{$null};$processLeft=if($SandboxPath){Get-CimInstance Win32_Process -ErrorAction SilentlyContinue|Where-Object {$_.ProcessId -ne $PID -and $_.CommandLine -and $_.CommandLine -match [regex]::Escape($SandboxPath)}}else{$null}
    if($serviceLeft -or $listenerLeft -or $processLeft){Say 'SANDBOX_SERVICE_LEFTOVER' 'YES';Say 'SANDBOX_PROCESS_LEFTOVER' 'YES';Say 'SANDBOX_LISTENER_LEFTOVER' 'YES'}else{Say 'SANDBOX_SERVICE_LEFTOVER' 'NO';Say 'SANDBOX_PROCESS_LEFTOVER' 'NO';Say 'SANDBOX_LISTENER_LEFTOVER' 'NO'}
}
