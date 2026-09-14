BEGIN;

CREATE TABLE IF NOT EXISTS public.site_product_events (
    event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at_utc timestamptz NOT NULL,
    parent_session_id uuid NOT NULL REFERENCES public.site_visit_sessions(session_id) ON DELETE CASCADE,
    surface text NOT NULL CHECK (surface IN ('item', 'market', 'top_items', 'trader')),
    event_type text NOT NULL CHECK (event_type IN ('surface_open', 'filter_apply', 'filter_clear', 'sort_change', 'period_change', 'view_change', 'toggle_change')),
    control_key varchar(64) NULL,
    value_key varchar(64) NULL,
    sequence_no integer NOT NULL CHECK (sequence_no > 0),
    created_at_utc timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT site_product_events_parent_sequence_key UNIQUE (parent_session_id, sequence_no),
    CONSTRAINT site_product_events_shape_chk CHECK (
        (event_type = 'surface_open' AND surface IN ('item', 'market', 'top_items', 'trader') AND control_key IS NULL AND value_key IS NULL)
        OR (surface = 'item' AND event_type IN ('filter_apply', 'filter_clear') AND control_key = 'wallet_filter' AND value_key IS NULL)
        OR (surface = 'top_items' AND event_type IN ('filter_apply', 'filter_clear') AND control_key = 'item_class_filter' AND value_key IS NULL)
        OR (surface = 'trader' AND event_type IN ('filter_apply', 'filter_clear') AND control_key = 'trader_filter' AND value_key IS NULL)
        OR (surface = 'top_items' AND event_type = 'sort_change' AND control_key = 'sort' AND value_key IN ('market_strength', 'volume', 'liquidity', 'total_supply'))
        OR (surface = 'trader' AND event_type = 'sort_change' AND control_key = 'sort' AND value_key IN ('earned', 'invested', 'sold', 'trades'))
        OR (surface = 'market' AND event_type = 'period_change' AND control_key = 'period' AND value_key IN ('all', '12m', '6m', '3m'))
        OR (surface = 'top_items' AND event_type = 'period_change' AND control_key = 'period' AND value_key IN ('all', '30d', '7d', '1d'))
        OR (surface = 'item' AND event_type = 'view_change' AND control_key = 'view' AND value_key IN ('chart', 'table'))
        OR (surface = 'item' AND event_type = 'toggle_change' AND control_key IN ('usd_price', 'trend_line') AND value_key IN ('on', 'off'))
        OR (surface = 'market' AND event_type = 'toggle_change' AND control_key IN ('usd_price', 'token_price', 'unique_wallets') AND value_key IN ('on', 'off'))
        OR (surface = 'top_items' AND event_type = 'toggle_change' AND control_key = 'usd_price' AND value_key IN ('on', 'off'))
        OR (surface = 'trader' AND event_type = 'toggle_change' AND control_key = 'usd_price' AND value_key IN ('on', 'off'))
    )
);

CREATE INDEX IF NOT EXISTS site_product_events_time_surface_idx
    ON public.site_product_events (occurred_at_utc, surface, event_type);

COMMIT;
