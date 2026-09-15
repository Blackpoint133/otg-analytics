from pathlib import Path

SOURCE = (Path(__file__).parents[1] / 'ops' / 'production' / 'preflight_production.ps1').read_text(encoding='utf-8')
HELPER = (Path(__file__).parents[1] / 'ops' / 'production' / 'preflight_readonly.py').read_text(encoding='utf-8')

def test_preflight_has_safe_defaults_and_read_only_inventory():
    assert "ProductionPort = 8502" in SOURCE
    assert "C:\\VAMBAM\\Projects\\OTG\\data_streamlit\\opensea_sales" in SOURCE
    assert "Get-NetTCPConnection" in SOURCE
    assert "Get-CimInstance Win32_Process" in SOURCE
    assert "status --short" in SOURCE
    assert "GUNZSCOPE_SUPPLY_SOURCE" in SOURCE
    assert "POSTGRES_PASSWORD" in SOURCE
    assert "Get-ScheduledTask" in SOURCE
    assert "Get-ScheduledTaskInfo" in SOURCE
    assert "Caddy" in SOURCE
    assert "default_transaction_read_only=on" in HELPER
    assert "ConvertFrom-Json" in SOURCE
    assert "psycopg2.connect" in HELPER
    assert "information_schema" in HELPER
    assert "pg_catalog" in HELPER
    assert "pg_get_constraintdef" in HELPER
    assert "site_visit_sessions_mode_chk" in HELPER
    assert "C:\\caddy\\Caddyfile" in SOURCE
    assert "WORKING_DIRECTORY" in SOURCE
    assert "MAX_VALID_SALE_DATE" in SOURCE or "MAX_VALID" in SOURCE
    for name in ("OTG_SITE_ANALYTICS_EXCLUDED_VISITOR_HASHES", "OTG_SITE_ANALYTICS_INTERNAL_USER_AGENT_PATTERNS"):
        assert name in SOURCE
    assert "READ_ONLY_DISCOVERY_REQUIRED" not in SOURCE
    assert "ENV_AND_DRIVER_AVAILABLE_ONLY" not in SOURCE
    assert "DB_SCHEMA_AUDIT=COMPLETE_READ_ONLY" in SOURCE

def test_preflight_contains_no_mutation_commands():
    forbidden = ('git pull', 'git merge', 'git reset', 'git clean', 'git checkout', 'git switch', 'git restore',
                 'Stop-Process', 'Start-Process', 'Restart-Service', 'Stop-Service', 'Start-Service',
                 'Set-Content', 'Add-Content', 'Remove-Item', 'Move-Item', 'Copy-Item', 'Rename-Item', 'Set-Item',
                 'schtasks /run', 'schtasks /change', 'ALTER TABLE', 'CREATE TABLE', 'DROP TABLE', 'TRUNCATE',
                 'INSERT INTO', 'UPDATE', 'DELETE FROM')
    for token in forbidden:
        assert token not in SOURCE
