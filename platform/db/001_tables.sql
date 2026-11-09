-- Who the accounts are. Each sync keeps these two tables up to date.
create table users (
  user_id text primary key,
  name text not null,
  title text not null
);

create table accounts (
  account_id text primary key,
  name text not null,
  sub_vertical text not null,
  revenue_eur bigint not null,
  owner_id text not null references users
);

-- One row per sync. The page reads the latest run that succeeded, so a failed sync changes nothing.
create table runs (
  run_id bigint generated always as identity primary key,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running' check (status in ('running', 'succeeded', 'failed')),
  error text
);

-- When each source was exported, for each run.
create table source_exports (
  run_id bigint not null references runs on delete cascade,
  source text not null,
  as_of timestamptz not null,
  primary key (run_id, source)
);

-- Only accounts with at least one signal. Scores stay per run, so past weeks can be compared.
create table scores (
  run_id bigint not null references runs on delete cascade,
  account_id text not null references accounts,
  rank int not null,
  tier text not null,
  score_raw numeric not null,
  score_display int not null,
  formula text not null,
  size_label text not null,
  size_multiplier numeric not null,
  action_text text not null,
  effort_minutes int not null,
  effort_band text not null,
  prepare text[] not null,
  primary key (run_id, account_id),
  unique (run_id, rank)
);

create table signals (
  run_id bigint not null,
  account_id text not null,
  sort_order int not null,
  signal_id text not null,
  label text not null,
  tier text not null,
  points int not null,
  sources text[] not null,
  evidence_text text not null,
  source_record_id text, -- empty when an account has no call or meeting on record
  headline_clause text not null,
  primary key (run_id, account_id, sort_order),
  foreign key (run_id, account_id) references scores on delete cascade
);

-- What the Account Manager did. One row per account, week and kind.
create table account_actions (
  action_id bigint generated always as identity primary key,
  account_id text not null references accounts,
  week text not null,
  kind text not null check (kind in ('logged', 'snoozed', 'flagged')),
  reason text,
  user_id text not null references users,
  created_at timestamptz not null default now(),
  unique (account_id, week, kind)
);
