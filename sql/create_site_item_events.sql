CREATE TABLE IF NOT EXISTS public.site_item_events (
    event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at_utc timestamptz NOT NULL,
    parent_session_id uuid NULL,
    browser_visitor_hash char(64) NULL,
    identity_version smallint NOT NULL CHECK (identity_version IN (1, 2)),
    item_key varchar(180) NOT NULL,
    event_type text NOT NULL CHECK (event_type IN ('initial_default', 'initial_explicit', 'item_select')),
    mode text NOT NULL CHECK (mode = 'item'),
    sequence_no integer NOT NULL CHECK (sequence_no > 0),
    created_at_utc timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS site_item_events_time_item_idx
    ON public.site_item_events (occurred_at_utc, item_key);

CREATE INDEX IF NOT EXISTS site_item_events_session_sequence_idx
    ON public.site_item_events (parent_session_id, sequence_no);

CREATE INDEX IF NOT EXISTS site_item_events_browser_time_idx
    ON public.site_item_events (browser_visitor_hash, occurred_at_utc)
    WHERE browser_visitor_hash IS NOT NULL;
