-- Each service gets only what it needs. Their logins are set by app/migrate.py from the environment.

-- The API reads everything and can only change what the Account Manager does.
create role priority_api login;
grant select on users, accounts, runs, source_exports, scores, signals, account_actions to priority_api;
grant insert, update, delete on account_actions to priority_api;

-- The sync writes the scores and never sees the actions.
create role priority_sync login;
grant select, insert, update on users, accounts, runs, source_exports, scores, signals to priority_sync;
