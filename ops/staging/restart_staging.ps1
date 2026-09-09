[CmdletBinding()]
param([string]$ExpectedHead)
$ErrorActionPreference = 'Stop'
$EXPECTED_ROOT = 'C:\VAMBAM\Projects\OTG\staging\opensea_sales'
$EXPECTED_APP = "$EXPECTED_ROOT\streamlit_opensea_sales\app_opensea_sales.py"
$EXPECTED_VENV = "$EXPECTED_ROOT\.venv"
$EXPECTED_STREAMLIT = "$EXPECTED_VENV\Scripts\streamlit.exe"
$EXPECTED_PYTHON = "$EXPECTED_VENV\Scripts\python.exe"
$EXPECTED_PORT = 8504
$FORBIDDEN_PRODUCTION_PORT = 8502
$FORBIDDEN_PRODUCTION_ROOT = 'C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales'
$LOG_ROOT = 'C:\VAMBAM\Projects\OTG\DEV\staging_runtime'
if (!(Test-Path -LiteralPath $EXPECTED_ROOT) -or !(Test-Path -LiteralPath $EXPECTED_APP) -or !(Test-Path -LiteralPath $EXPECTED_STREAMLIT) -or !(Test-Path -LiteralPath $EXPECTED_PYTHON)) { throw 'Staging preflight path check failed.' }
if ($EXPECTED_PORT -eq $FORBIDDEN_PRODUCTION_PORT -or $EXPECTED_ROOT -eq $FORBIDDEN_PRODUCTION_ROOT) { throw 'Production guard failed.' }
$head = (& git -C $EXPECTED_ROOT rev-parse HEAD).Trim()
if ($ExpectedHead -and $head -ne $ExpectedHead) { throw "ExpectedHead mismatch: $head" }
& $EXPECTED_PYTHON -c "import streamlit,plotly,pandas,numpy,psycopg2; print('IMPORT_GATE_PASS')" | Out-Null
New-Item -ItemType Directory -Force -Path $LOG_ROOT | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$out = Join-Path $LOG_ROOT "streamlit_8504_${stamp}_stdout.log"
$err = Join-Path $LOG_ROOT "streamlit_8504_${stamp}_stderr.log"
$listener = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $EXPECTED_PORT -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
    if (!$proc.CommandLine.Contains($EXPECTED_ROOT) -or !$proc.CommandLine.Contains('app_opensea_sales.py')) { throw '8504 is occupied by an unexpected process.' }
    Stop-Process -Id $listener.OwningProcess
    Start-Sleep -Seconds 2
}
$p = Start-Process -FilePath $EXPECTED_STREAMLIT -ArgumentList 'run',$EXPECTED_APP,'--server.port','8504','--server.address','127.0.0.1','--server.fileWatcherType','poll','--server.headless','true' -WorkingDirectory $EXPECTED_ROOT -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
$deadline = (Get-Date).AddSeconds(60)
do { Start-Sleep -Milliseconds 500; $new = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $EXPECTED_PORT -State Listen -ErrorAction SilentlyContinue } while (!$new -and (Get-Date) -lt $deadline)
if (!$new) { throw 'Staging listener did not start within 60 seconds.' }
$actual = Get-CimInstance Win32_Process -Filter "ProcessId=$($new.OwningProcess)"
if (!$actual.CommandLine.Contains($EXPECTED_ROOT) -or !$actual.CommandLine.Contains('.venv\Scripts\streamlit.exe')) { throw 'New process failed staging command guard.' }
$combined = ((Get-Content -LiteralPath $out -ErrorAction SilentlyContinue) + (Get-Content -LiteralPath $err -ErrorAction SilentlyContinue)) -join "`n"
if ($combined -match 'Traceback|ModuleNotFoundError|ImportError|Uncaught app exception') { throw 'Staging application log contains an exception.' }
"STAGING_RESTART_RESULT=PASS"
"STAGING_HEAD=$head"
"STAGING_PID=$($new.OwningProcess)"
"STAGING_PYTHON=$EXPECTED_STREAMLIT"
"STAGING_APP=$EXPECTED_APP"
"STAGING_PORT=$EXPECTED_PORT"
