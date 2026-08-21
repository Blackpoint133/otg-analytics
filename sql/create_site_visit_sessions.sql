create table public.site_visit_sessions (
    id bigserial primary key,
    session_id uuid not null,
    visitor_hash char(64) not null,
    started_at_utc timestamptz not null default now(),
    last_seen_at_utc timestamptz not null default now(),
    mode text not null,
    item_key text null,
    path text not null default '/',
    referrer_host text null,
    traffic_source text not null default 'direct',
    utm_source varchar(100) null,
    utm_medium varchar(100) null,
    utm_campaign varchar(150) null,
    utm_content varchar(150) null,
    utm_term varchar(150) null,
    device_type text not null default 'unknown',
    browser_family text not null default 'unknown',
    locale varchar(35) null,
    timezone varchar(64) null,
    is_bot boolean not null default false,
    bot_reason text null,
    is_internal boolean not null default false,
    internal_reason text null,
    created_at_utc timestamptz not null default now(),

    constraint site_visit_sessions_session_id_key
        unique (session_id),

    constraint site_visit_sessions_visitor_hash_hex_chk
        check (visitor_hash ~ '^[0-9a-f]{64}$'),

    constraint site_visit_sessions_mode_chk
        check (mode in ('item', 'market', 'top_items')),

    constraint site_visit_sessions_device_type_chk
        check (device_type in ('desktop', 'mobile', 'tablet', 'unknown')),

    constraint site_visit_sessions_browser_family_chk
        check (
            browser_family in (
                'edge',
                'chrome',
                'safari',
                'firefox',
                'headless_chrome',
                'bot',
                'unknown'
            )
        ),

    constraint site_visit_sessions_traffic_source_chk
        check (
            traffic_source in (
                'direct',
                'x',
                'youtube',
                'tiktok',
                'instagram',
                'discord',
                'telegram',
                'google',
                'self',
                'other'
            )
        ),

    constraint site_visit_sessions_item_key_len_chk
        check (item_key is null or length(item_key) <= 180),

    constraint site_visit_sessions_referrer_host_len_chk
        check (referrer_host is null or length(referrer_host) <= 255),

    constraint site_visit_sessions_path_len_chk
        check (length(path) <= 255),

    constraint site_visit_sessions_bot_reason_len_chk
        check (bot_reason is null or length(bot_reason) <= 120),

    constraint site_visit_sessions_internal_reason_len_chk
        check (
            internal_reason is null
            or length(internal_reason) <= 120
        )
);

create index site_visit_sessions_started_at_idx
    on public.site_visit_sessions (started_at_utc);

create index site_visit_sessions_visitor_started_idx
    on public.site_visit_sessions (
        visitor_hash,
        started_at_utc
    );

create index site_visit_sessions_mode_started_idx
    on public.site_visit_sessions (
        mode,
        started_at_utc
    );

create index site_visit_sessions_campaign_started_idx
    on public.site_visit_sessions (
        utm_campaign,
        started_at_utc
    )
    where utm_campaign is not null;

create index site_visit_sessions_human_started_idx
    on public.site_visit_sessions (
        is_bot,
        is_internal,
        started_at_utc
    );

comment on table public.site_visit_sessions is
    'First-party OTG OpenSea Sales visitor analytics sessions. No raw IP, cookies, full URLs, or full headers.';

comment on column public.site_visit_sessions.visitor_hash is
    'HMAC-SHA256 of normalized trusted client IP and normalized User-Agent.';
