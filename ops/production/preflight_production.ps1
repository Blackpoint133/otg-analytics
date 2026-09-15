param(
    [string]$ProductionRoot = 'C:\VAMBAM\Projects\OTG\data_streamlit\opensea_sales',
    [int]$ProductionPort = 8502
)
$ErrorActionPreference = 'Stop'
function State($v) { if ($null -eq $v -or "$v" -eq '') { 'MISSING' } elseif ("$v" -match '^(true|1|yes)$') { 'TRUE' } elseif ("$v" -match '^(false|0|no)$') { 'FALSE' } elseif ("$v" -in @('v1','v2','v3')) { "$v" } else { 'PRESENT' } }
Write-Output "PRODUCTION_ROOT=$ProductionRoot"
Write-Output "ROOT_EXISTS=$(Test-Path -LiteralPath $ProductionRoot)"
if (!(Test-Path -LiteralPath $ProductionRoot)) { exit 2 }
$RuntimeRoot=if(Test-Path (Join-Path $ProductionRoot 'streamlit_opensea_sales')){Join-Path $ProductionRoot 'streamlit_opensea_sales'}else{$ProductionRoot}
foreach ($p in @('.git','.env','.venv')) { Write-Output "PATH_$($p.Replace('.','_').Replace('\\','_'))=$(Test-Path -LiteralPath (Join-Path $ProductionRoot $p))" }
foreach ($p in @('app_opensea_sales.py','data_opensea_sales')) { Write-Output "RUNTIME_PATH_$($p.Replace('.','_').Replace('\\','_'))=$(Test-Path -LiteralPath (Join-Path $RuntimeRoot $p))" }
Push-Location $ProductionRoot
try { Write-Output "HEAD=$(git -c safe.directory=$ProductionRoot rev-parse HEAD)"; Write-Output "BRANCH=$(git -c safe.directory=$ProductionRoot branch --show-current)"; Write-Output 'GIT_STATUS_BEGIN'; git -c safe.directory=$ProductionRoot status --short; Write-Output 'GIT_STATUS_END' } finally { Pop-Location }
$conn = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $ProductionPort -State Listen -ErrorAction SilentlyContinue
Write-Output "PORT_${ProductionPort}_LISTENING=$([bool]$conn)"
if ($conn) { foreach ($c in $conn) { $p=Get-CimInstance Win32_Process -Filter "ProcessId=$($c.OwningProcess)"; Write-Output "PID=$($c.OwningProcess)"; Write-Output "PROCESS_PATH=$($p.ExecutablePath)"; Write-Output "PROCESS_COMMAND_ROOT=$($p.CommandLine -like "*$ProductionRoot*")"; Write-Output "PROCESS_COMMAND_APP=$($p.CommandLine -like '*app_opensea_sales.py*')" } }
$envPath=Join-Path $ProductionRoot '.env'; $values=@{}
if (Test-Path -LiteralPath $envPath) { foreach($line in Get-Content -LiteralPath $envPath){ if($line -match '^\s*([^#=]+)=(.*)$'){$values[$matches[1].Trim()]=$matches[2].Trim()}} }
foreach($n in @('POSTGRES_USER','POSTGRES_PASSWORD','POSTGRES_HOST','POSTGRES_PORT','POSTGRES_DB','API_GUNZSCOPE','GUNZSCOPE_SUPPLY_SOURCE','OTG_ANALYTICS_WRITES_ENABLED','OTG_SITE_ANALYTICS_ENABLED','OTG_SITE_ANALYTICS_HMAC_SECRET','OTG_SITE_ANALYTICS_EXCLUDED_VISITOR_HASHES','OTG_SITE_ANALYTICS_INTERNAL_USER_AGENT_PATTERNS','OTG_PRODUCT_EVENTS_ENABLED','OTG_FEEDBACK_WRITES_ENABLED','OTG_FEEDBACK_TELEGRAM_ENABLED','OTG_FEEDBACK_TELEGRAM_BOT_TOKEN','OTG_FEEDBACK_TELEGRAM_CHAT_ID')) { Write-Output "ENV_$n=$(State $values[$n])" }
$py=Join-Path $ProductionRoot '.venv\Scripts\python.exe'; if(Test-Path $py){ & $py -c "import sys; print('PYTHON_VERSION='+sys.version.split()[0]); import streamlit, pandas, plotly, numpy, psycopg2; print('STREAMLIT_VERSION='+streamlit.__version__); print('PANDAS_VERSION='+pandas.__version__); print('PLOTLY_VERSION='+plotly.__version__); print('NUMPY_VERSION='+numpy.__version__); print('PSYCOPG2_VERSION='+psycopg2.__version__.split()[0])"; & $py -m pip check }
foreach($rel in @('items_index.json','current_price.csv','sales','sales_enriched','market_overview','market_overview_enriched','market_overview_enriched\market_overview_enriched_manifest.json','market_overview_enriched\market_period_summaries.json','market_overview_enriched\market_expansion_metrics.json','trader_analytics_snapshot.json','opensea_account_profiles_snapshot.json','item_class_snapshot.json','gunzscope_supply_snapshot.json','gunzscope_supply_snapshot_v2_shadow.json','gunzscope_supply_snapshot_v3_provider.json')) { $f=Join-Path (Join-Path $RuntimeRoot 'data_opensea_sales') $rel; if(Test-Path $f){$i=Get-Item $f; Write-Output "ARTIFACT=$rel|EXISTS|SIZE=$($i.Length)|MTIME=$($i.LastWriteTime.ToString('o'))"}else{Write-Output "ARTIFACT=$rel|MISSING"} }
foreach($name in @('run_enriched_pipeline.py','run_indexer.py','import_opensea_sales.py','import_opensea_sales_market_overview.py','import_opensea_sales_gun_usd_price_history.py','import_gun_usd_price_history_from_postgres.py','build_enriched_market_overview.py','build_gun_price_history.py','market_item_rankings.py','start.bat')) { Write-Output "PRIVATE_$name=$(Test-Path (Join-Path $ProductionRoot $name))" }
Write-Output 'SCHEDULED_TASK_AUDIT=READ_ONLY_DISCOVERY_REQUIRED'
Write-Output 'PROXY_AUDIT=READ_ONLY_DISCOVERY_REQUIRED'
Write-Output 'DB_SCHEMA_AUDIT=ENV_AND_DRIVER_AVAILABLE_ONLY'
