"""Read-only production evidence helpers; emits sanitized aggregate facts only."""
from __future__ import annotations
import csv, json, os, sys
from datetime import datetime
from pathlib import Path

ENV_NAMES = ('POSTGRES_USER','POSTGRES_PASSWORD','POSTGRES_HOST','POSTGRES_PORT','POSTGRES_DB','API_GUNZSCOPE','GUNZSCOPE_SUPPLY_SOURCE','OTG_ANALYTICS_WRITES_ENABLED','OTG_SITE_ANALYTICS_ENABLED','OTG_SITE_ANALYTICS_HMAC_SECRET','OTG_SITE_ANALYTICS_EXCLUDED_VISITOR_HASHES','OTG_SITE_ANALYTICS_INTERNAL_USER_AGENT_PATTERNS','OTG_PRODUCT_EVENTS_ENABLED','OTG_FEEDBACK_WRITES_ENABLED','OTG_FEEDBACK_TELEGRAM_ENABLED','OTG_FEEDBACK_TELEGRAM_BOT_TOKEN','OTG_FEEDBACK_TELEGRAM_CHAT_ID','OTG_LOG_DIR','OTG_INTERNAL_ANALYTICS_PASSWORD')
def env_state(value):
    if value is None: return 'MISSING'
    if not value.strip(): return 'EMPTY'
    if value.lower() in ('true','1','yes'): return 'TRUE'
    if value.lower() in ('false','0','no'): return 'FALSE'
    if value in ('v1','v2','v3'): return value
    return 'PRESENT'
def read_env(path):
    values={}
    if Path(path).exists():
        for line in Path(path).read_text(errors='replace').splitlines():
            if line and not line.lstrip().startswith('#') and '=' in line:
                k,v=line.split('=',1); values[k.strip()]=v.strip()
    return {k:env_state(values.get(k)) for k in ENV_NAMES}
def load_env_values(path):
    values={}
    if Path(path).exists():
        for line in Path(path).read_text(errors='replace').splitlines():
            if line and not line.lstrip().startswith('#') and '=' in line:
                k,v=line.split('=',1); values[k.strip()]=v.strip()
    return values
def csv_meta(directory):
    files=list(Path(directory).rglob('*.csv')) if Path(directory).is_dir() else []
    dates=[]
    for file in files:
        try:
            with file.open(newline='',encoding='utf-8-sig',errors='replace') as fh:
                for row in csv.DictReader(fh):
                    try:
                        value=datetime.fromisoformat((row.get('sale_date') or '').replace('Z','+00:00'))
                        dates.append(value)
                    except (ValueError,TypeError): pass
        except OSError: pass
    return {'FILE_COUNT':len(files),'TOTAL_SIZE_BYTES':sum(f.stat().st_size for f in files),'MAX_VALID_SALE_DATE':max(dates).isoformat() if dates else 'NONE'}
def json_meta(path):
    try: data=json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError): return {'EXISTS':'NO'}
    result={'EXISTS':'YES'}
    if isinstance(data,dict):
        for key in ('schema_version','generated_at','fetched_at','date_max'):
            if key in data: result[key.upper()]=data[key]
        for key in ('item_count','wallet_count','profile_count','count'):
            if isinstance(data.get(key),(int,float)): result[key.upper()]=data[key]
        result['TOP_LEVEL_KEYS']=len(data)
    elif isinstance(data,list): result['ROW_COUNT']=len(data)
    return result
def migration_plan(schema):
    out=[]
    if not all(schema.get(k) for k in ('browser_visitor_hash','identity_version','identity_check','hash_hex_check','identity_v2_check','hash_index')): out.append('add_site_visit_stable_browser_identity.sql')
    if not schema.get('trader_mode'): out.append('add_site_visit_trader_mode.sql')
    if not schema.get('product_events'): out.append('create_site_product_events.sql')
    elif not schema.get('product_events_trader_usd'): out.append('add_site_product_events_trader_usd_toggle.sql')
    if not schema.get('user_feedback'): out.append('create_user_feedback.sql')
    return out
def db_audit(env):
    import psycopg2
    conn=psycopg2.connect(host=env['POSTGRES_HOST'],port=env['POSTGRES_PORT'],dbname=env['POSTGRES_DB'],user=env['POSTGRES_USER'],password=env['POSTGRES_PASSWORD'],options='-c default_transaction_read_only=on -c statement_timeout=5000')
    try:
        cur=conn.cursor(); cur.execute('SHOW transaction_read_only'); readonly=cur.fetchone()[0]
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s",('site_visit_sessions',)); cols={r[0] for r in cur.fetchall()}
        cur.execute("SELECT conname, pg_get_constraintdef(oid) FROM pg_catalog.pg_constraint WHERE connamespace='public'::regnamespace"); constraints={r[0]:r[1] for r in cur.fetchall()}
        cur.execute("SELECT indexname FROM pg_catalog.pg_indexes WHERE schemaname='public'"); indexes={r[0] for r in cur.fetchall()}
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s)",('site_product_events',)); product=cur.fetchone()[0]
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s)",('user_feedback',)); feedback=cur.fetchone()[0]
        schema={'transaction_read_only':readonly,'browser_visitor_hash':'browser_visitor_hash' in cols,'identity_version':'identity_version' in cols,'identity_check':'site_visit_sessions_identity_version_chk' in constraints,'hash_hex_check':'site_visit_sessions_browser_visitor_hash_hex_chk' in constraints,'identity_v2_check':'site_visit_sessions_identity_v2_hash_chk' in constraints,'hash_index':'site_visit_sessions_browser_visitor_started_idx' in indexes,'trader_mode':'trader' in constraints.get('site_visit_sessions_mode_chk','').lower(),'product_events':product,'product_events_trader_usd':False,'user_feedback':feedback,'columns':len(cols)}
        return schema
    finally: conn.close()
def main(root):
    root=Path(root); raw=load_env_values(root/'.env'); print('ENV='+json.dumps({k:env_state(raw.get(k)) for k in ENV_NAMES}));
    try: print('DB='+json.dumps(db_audit(raw)))
    except Exception as exc: print('DB_AUDIT=BLOCKED_'+type(exc).__name__)
    print('SALES='+json.dumps(csv_meta(root/'streamlit_opensea_sales/data_opensea_sales/sales'))); print('SALES_ENRICHED='+json.dumps(csv_meta(root/'streamlit_opensea_sales/data_opensea_sales/sales_enriched')))
    base=root/'streamlit_opensea_sales/data_opensea_sales'
    for name in ('market_overview_enriched_manifest.json','market_period_summaries.json','market_expansion_metrics.json','trader_analytics_snapshot.json','item_class_snapshot.json','gunzscope_supply_snapshot.json','gunzscope_supply_snapshot_v2_shadow.json','gunzscope_supply_snapshot_v3_provider.json','opensea_account_profiles_snapshot.json'):
        path=base/'market_overview_enriched'/name if name in ('market_overview_enriched_manifest.json','market_period_summaries.json','market_expansion_metrics.json') else base/name
        print('JSON_'+name+'='+json.dumps(json_meta(path)))
if __name__=='__main__': main(sys.argv[1] if len(sys.argv)>1 else '.')
