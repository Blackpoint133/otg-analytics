begin;

alter table public.site_visit_sessions
    add column if not exists browser_visitor_hash char(64) null,
    add column if not exists identity_version smallint not null default 1;

do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'site_visit_sessions_identity_version_chk'
          and conrelid = 'public.site_visit_sessions'::regclass
    ) then
        alter table public.site_visit_sessions
            add constraint site_visit_sessions_identity_version_chk
            check (identity_version in (1, 2));
    end if;
    if not exists (
        select 1 from pg_constraint
        where conname = 'site_visit_sessions_browser_visitor_hash_hex_chk'
          and conrelid = 'public.site_visit_sessions'::regclass
    ) then
        alter table public.site_visit_sessions
            add constraint site_visit_sessions_browser_visitor_hash_hex_chk
            check (browser_visitor_hash is null or browser_visitor_hash ~ '^[0-9a-f]{64}$');
    end if;
    if not exists (
        select 1 from pg_constraint
        where conname = 'site_visit_sessions_identity_v2_hash_chk'
          and conrelid = 'public.site_visit_sessions'::regclass
    ) then
        alter table public.site_visit_sessions
            add constraint site_visit_sessions_identity_v2_hash_chk
            check (identity_version <> 2 or browser_visitor_hash is not null);
    end if;
end
$$;

create index if not exists site_visit_sessions_browser_visitor_started_idx
    on public.site_visit_sessions (browser_visitor_hash, started_at_utc)
    where browser_visitor_hash is not null;

comment on column public.site_visit_sessions.browser_visitor_hash is
    'Domain-separated HMAC-SHA256 of the random first-party browser V2 identifier.';

commit;
