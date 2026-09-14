from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "sql/create_site_product_events.sql").read_text(encoding="utf-8")
MIGRATION = (ROOT / "sql/add_site_product_events_trader_usd_toggle.sql").read_text(encoding="utf-8")


def test_schema_is_transactional_idempotent_and_append_only():
    assert SCHEMA.startswith("BEGIN;")
    assert SCHEMA.rstrip().endswith("COMMIT;")
    assert "CREATE TABLE IF NOT EXISTS public.site_product_events" in SCHEMA
    assert "CREATE INDEX IF NOT EXISTS site_product_events_time_surface_idx" in SCHEMA
    assert "site_product_events_parent_sequence_key UNIQUE (parent_session_id, sequence_no)" in SCHEMA


def test_schema_has_parent_fk_allowlists_and_shape_defense():
    assert "parent_session_id uuid NOT NULL REFERENCES public.site_visit_sessions(session_id) ON DELETE CASCADE" in SCHEMA
    assert "surface IN ('item', 'market', 'top_items', 'trader')" in SCHEMA
    assert "event_type IN ('surface_open', 'filter_apply', 'filter_clear', 'sort_change', 'period_change', 'view_change', 'toggle_change')" in SCHEMA
    assert "sequence_no > 0" in SCHEMA
    assert "site_product_events_shape_chk CHECK" in SCHEMA
    assert "item_select" not in SCHEMA
    assert "visitor_hash" not in SCHEMA
    assert "browser_visitor_hash" not in SCHEMA
    assert "metadata" not in SCHEMA
    assert "json" not in SCHEMA.lower()


def test_trader_usd_toggle_contract_and_migration():
    assert "surface = 'trader' AND event_type = 'toggle_change' AND control_key = 'usd_price'" in SCHEMA
    assert "value_key IN ('on', 'off')" in SCHEMA
    assert MIGRATION.startswith("BEGIN;") and MIGRATION.rstrip().endswith("COMMIT;")
    assert "pg_get_constraintdef" in MIGRATION
    assert "DROP CONSTRAINT IF EXISTS site_product_events_shape_chk" in MIGRATION
    assert "site_product_events_time_surface_idx" not in MIGRATION
