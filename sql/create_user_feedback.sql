CREATE TABLE IF NOT EXISTS public.user_feedback (
    feedback_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id uuid NOT NULL UNIQUE,
    created_at_utc timestamptz NOT NULL DEFAULT now(),
    feedback_type text NOT NULL CHECK (feedback_type IN ('bug','suggestion','data_issue','other')),
    message text NOT NULL CHECK (char_length(message) BETWEEN 10 AND 2000),
    source_mode text NOT NULL CHECK (source_mode IN ('item','market','top_items','trader','unknown')),
    source_item_key varchar(180) NULL,
    source_context jsonb NOT NULL DEFAULT '{}'::jsonb,
    status text NOT NULL DEFAULT 'new' CHECK (status IN ('new','reviewed','planned','resolved','rejected'))
);
CREATE INDEX IF NOT EXISTS user_feedback_created_idx ON public.user_feedback (created_at_utc DESC);
CREATE INDEX IF NOT EXISTS user_feedback_status_created_idx ON public.user_feedback (status, created_at_utc DESC);
CREATE INDEX IF NOT EXISTS user_feedback_source_created_idx ON public.user_feedback (source_mode, created_at_utc DESC);
