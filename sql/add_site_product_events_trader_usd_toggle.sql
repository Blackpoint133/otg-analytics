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
     WHERE c.conname = 'site_product_events_shape_chk'
       AND n.nspname = 'public'
       AND t.relname = 'site_product_events';

    IF current_definition IS NULL OR position('surface = ''trader'' AND event_type = ''toggle_change'' AND control_key = ''usd_price''' IN lower(current_definition)) = 0 THEN
        ALTER TABLE public.site_product_events DROP CONSTRAINT IF EXISTS site_product_events_shape_chk;
        ALTER TABLE public.site_product_events ADD CONSTRAINT site_product_events_shape_chk CHECK (
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
        );
    END IF;
END $$;

COMMIT;
