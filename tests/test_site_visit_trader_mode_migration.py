from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_canonical_schema_accepts_trader_mode():
    source = (ROOT / "sql/create_site_visit_sessions.sql").read_text(encoding="utf-8")
    assert "check (mode in ('item', 'market', 'top_items', 'trader'))" in source


def test_trader_mode_migration_is_atomic_and_idempotent():
    source = (ROOT / "sql/add_site_visit_trader_mode.sql").read_text(encoding="utf-8")
    assert source.startswith("BEGIN;")
    assert source.rstrip().endswith("COMMIT;")
    assert "pg_get_constraintdef" in source
    assert "IF current_definition IS NULL" in source
    assert "DROP CONSTRAINT site_visit_sessions_mode_chk" in source
    assert "CHECK (mode IN ('item', 'market', 'top_items', 'trader'))" in source
    assert "site_item_events" not in source
