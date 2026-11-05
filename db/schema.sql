-- The week after scoring. db/seed.sql fills these tables.

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

-- One row per source: when its data was last exported.
create table sync_runs (
  source text primary key,
  as_of timestamptz not null
);

-- Only accounts with at least one signal: 34 of the 42 are healthy and have no row here.
create table scores (
  account_id text primary key references accounts,
  rank int not null unique,
  tier text not null,
  score_raw numeric not null,
  score_display int not null,
  formula text not null,
  size_label text not null,
  size_multiplier numeric not null,
  action_text text not null,
  effort_minutes int not null,
  effort_band text not null,
  prepare text[] not null
);

create table signals (
  account_id text not null references scores,
  sort_order int not null,
  signal_id text not null,
  label text not null,
  tier text not null,
  points int not null,
  sources text[] not null,
  evidence_text text not null,
  source_record_id text not null,
  headline_clause text not null,
  primary key (account_id, sort_order)
);

-- The project's public API keys get nothing: these tables are read through /api/week only.
revoke all on users, accounts, sync_runs, scores, signals from anon, authenticated;
alter table users enable row level security;
alter table accounts enable row level security;
alter table sync_runs enable row level security;
alter table scores enable row level security;
alter table signals enable row level security;

-- The only access the website has. It can read these 5 tables and nothing else.
-- No password here: it is set by hand, and the role cannot log in until then.
create role week_reader login;
grant usage on schema public to week_reader;
grant select on users, accounts, sync_runs, scores, signals to week_reader;
create policy week_reader_reads on users for select to week_reader using (true);
create policy week_reader_reads on accounts for select to week_reader using (true);
create policy week_reader_reads on sync_runs for select to week_reader using (true);
create policy week_reader_reads on scores for select to week_reader using (true);
create policy week_reader_reads on signals for select to week_reader using (true);
