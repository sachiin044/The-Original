-- Optional performance table for lightweight metadata caching.
-- Safe additive migration (does not alter existing endpoint behavior).

create table if not exists workflow_runs_cache (
    id uuid primary key default gen_random_uuid(),
    repo_id text not null,
    workflow_id text not null,
    run_id text not null,
    status text,
    conclusion text,
    duration_seconds integer,
    payload jsonb not null,
    fetched_at timestamptz not null default now(),
    unique (repo_id, run_id)
);

create index if not exists idx_workflow_runs_cache_repo_workflow
    on workflow_runs_cache (repo_id, workflow_id, fetched_at desc);
