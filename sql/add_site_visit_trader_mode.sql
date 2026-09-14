BEGIN;

DO $$
DECLARE
    current_definition text;
BEGIN
    SELECT pg_get_constraintdef(c.oid)
      INTO current_definition
      FROM pg_constraint c
      JOIN pg_class t ON t.oid = c.conrelid
      JOIN pg_namespace n ON n.oid = t.relnamespace
     WHERE c.conname = 'site_visit_sessions_mode_chk'
       AND n.nspname = 'public'
       AND t.relname = 'site_visit_sessions';

    IF current_definition IS NULL THEN
        ALTER TABLE public.site_visit_sessions
            ADD CONSTRAINT site_visit_sessions_mode_chk
            CHECK (mode IN ('item', 'market', 'top_items', 'trader'));
    ELSIF position('trader' IN lower(current_definition)) = 0 THEN
        ALTER TABLE public.site_visit_sessions
            DROP CONSTRAINT site_visit_sessions_mode_chk;
        ALTER TABLE public.site_visit_sessions
            ADD CONSTRAINT site_visit_sessions_mode_chk
            CHECK (mode IN ('item', 'market', 'top_items', 'trader'));
    END IF;
END $$;

COMMIT;
