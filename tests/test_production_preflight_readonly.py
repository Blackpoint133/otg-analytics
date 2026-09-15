import json
from pathlib import Path

from ops.production import preflight_readonly as p

def test_csv_and_json_metadata_are_aggregate_only(tmp_path):
    d=tmp_path/'sales'; d.mkdir()
    (d/'a.csv').write_text('sale_date,buyer\n2026-01-01T00:00:00Z,secret\n2026-01-03T00:00:00Z,secret\n')
    assert p.csv_meta(d)['MAX_VALID_SALE_DATE'].startswith('2026-01-03')
    f=tmp_path/'x.json'; f.write_text(json.dumps({'schema_version':3,'item_count':4,'wallet':'must not emit'}))
    result=p.json_meta(f); assert result['SCHEMA_VERSION']==3 and 'wallet' not in result

def test_migration_plan_is_derived_from_schema_state():
    s={'browser_visitor_hash':True,'identity_version':True,'identity_check':True,'hash_hex_check':True,'identity_v2_check':True,'hash_index':True,'trader_mode':True,'product_events':False,'user_feedback':False}
    assert p.migration_plan(s)==['create_site_product_events.sql','create_user_feedback.sql']

def test_env_state_redacts_values():
    assert p.env_state('true')=='TRUE'; assert p.env_state('v3')=='v3'; assert p.env_state('secret')=='PRESENT'

def test_db_audit_source_is_select_only():
    source=Path(p.__file__).read_text()
    assert 'psycopg2.connect' in source and 'SHOW transaction_read_only' in source
    assert 'information_schema.columns' in source and 'pg_get_constraintdef' in source
    for token in ('INSERT','UPDATE','DELETE','ALTER TABLE','CREATE TABLE','DROP TABLE'):
        assert token not in source
