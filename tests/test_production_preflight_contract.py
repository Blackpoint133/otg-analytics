from pathlib import Path

SOURCE = (Path(__file__).parents[1] / 'ops' / 'production' / 'preflight_production.ps1').read_text(encoding='utf-8')

def test_preflight_has_safe_defaults_and_read_only_inventory():
    assert "ProductionPort = 8502" in SOURCE
    assert "C:\\VAMBAM\\Projects\\OTG\\data_streamlit\\opensea_sales" in SOURCE
    assert "Get-NetTCPConnection" in SOURCE
    assert "Get-CimInstance Win32_Process" in SOURCE
    assert "status --short" in SOURCE
    assert "GUNZSCOPE_SUPPLY_SOURCE" in SOURCE
    assert "POSTGRES_PASSWORD" in SOURCE
    assert "SCHEDULED_TASK_AUDIT=READ_ONLY_DISCOVERY_REQUIRED" in SOURCE

def test_preflight_contains_no_mutation_commands():
    forbidden = ('git pull', 'git merge', 'git reset', 'git clean', 'git checkout', 'git switch', 'git restore',
                 'Stop-Process', 'Start-Process', 'Restart-Service', 'Stop-Service', 'Start-Service',
                 'Set-Content', 'Add-Content', 'Remove-Item', 'Move-Item', 'Copy-Item', 'Rename-Item', 'Set-Item',
                 'schtasks /run', 'schtasks /change', 'ALTER TABLE', 'CREATE TABLE', 'DROP TABLE', 'TRUNCATE',
                 'INSERT INTO', 'UPDATE', 'DELETE FROM')
    for token in forbidden:
        assert token not in SOURCE
