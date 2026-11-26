---
type: prompt
plan: "[[2026-11-26-mvp-hardening]]"
id: 03
unit:
status: todo
model: sonnet
effort: high
depends_on: [01]
parallel_group: C
files:
  create:
    - ruri-bot/prototype/db/001_checks.sql
    - ruri-bot/prototype/db.py
    - ruri-bot/prototype/migrate.py
    - ruri-bot/prototype/tests/test_db.py
  modify:
    - ruri-bot/prototype/requirements.txt
  delete: []
---
# 03 · Neon data layer + migration

## Task
Add a small, synchronous Postgres data layer for the audit log and cost caps. Add a migration file, a migration
runner, and tests that run against a real Postgres when `TEST_DATABASE_URL` is set (skipped otherwise). Don't
wire it into `app.py`; prompt 05 does that.

## Context
- Repo root: `/Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments`. App dir `P/` =
  `ruri-bot/prototype/`. Python 3.12 venv `P/.venv`. Install with
  `uv pip install --python .venv/bin/python -r requirements-dev.txt` (it includes `-r requirements.txt`).
- Database: **Neon Postgres** (PG 16+, so `gen_random_uuid()` is built in). The Neon Vercel integration injects
  `DATABASE_URL` (pooled, PgBouncer transaction mode) and `DATABASE_URL_UNPOOLED`. The app uses the pooled
  URL; migrations prefer the unpooled one.
- Decisions (locked):
  - Store **no files**. One `checks` row per check. Purge rows older than 30 days.
  - Caps count **documents** in live mode, over a rolling 24 h globally and a rolling 1 h per client.
  - Count and insert happen in **one transaction behind an advisory lock**, so concurrent requests can't
    overshoot. The pooler is in transaction mode, so use `pg_advisory_xact_lock` (transaction-scoped), never
    session locks.
- Use **psycopg 3**: add `psycopg[binary]==<version uv resolves>` to `requirements.txt`. Keep pins exact,
  matching the file's existing `==` style.

### `P/db/001_checks.sql`
```sql
CREATE TABLE IF NOT EXISTS checks (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at  timestamptz NOT NULL DEFAULT now(),
  mode        text NOT NULL,                 -- live | offline
  model       text,
  policy_sha  text NOT NULL,
  prompt_sha  text NOT NULL,
  client_hash text NOT NULL,
  doc_count   integer NOT NULL CHECK (doc_count >= 0),
  applicant   text NOT NULL,
  status      text NOT NULL DEFAULT 'started' CHECK (status IN ('started','done','failed')),
  result      jsonb
);
CREATE INDEX IF NOT EXISTS checks_created_at_idx ON checks (created_at);
CREATE INDEX IF NOT EXISTS checks_client_created_idx ON checks (client_hash, created_at);
```

### `P/migrate.py` (CLI, ~40 lines)
- URL = `DATABASE_URL_UNPOOLED` or `DATABASE_URL` (exit 2 with a message if neither is set). Never print the URL.
- `CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())`.
- For each `db/*.sql` (relative to the file's directory) sorted by name whose stem isn't recorded: run it and
  insert the version in **one transaction**. Print `applied <stem>` or `up to date`.
- Expose `def migrate(url: str) -> list[str]` (returns the applied stems) so tests can call it. `if __name__ == "__main__":` wraps it.

### `P/db.py` (public API; type-hinted, sync)
```python
class CapExceeded(Exception):
    def __init__(self, kind: str): ...          # kind: "daily" | "client"; store as self.kind

def url() -> str | None                          # os.environ.get("DATABASE_URL") or None
def connect(dsn: str | None = None)              # psycopg.connect(dsn or url(), connect_timeout=5, autocommit=True, prepare_threshold=None)  (no server-side prepares through Neon's PgBouncer)
def reserve_check(conn, *, mode: str, model: str | None, policy_sha: str, prompt_sha: str,
                  client_hash: str, doc_count: int, applicant: str,
                  daily_cap: int | None, client_cap: int | None) -> str
def finish_check(conn, check_id: str, *, status: str, result: dict | None) -> None
def purge(conn, days: int = 30) -> int           # DELETE ... WHERE created_at < now() - make_interval(days => %s); returns rowcount
```
`reserve_check` runs in `with conn.transaction():`
1. `SELECT pg_advisory_xact_lock(727001)` (a constant for the "checks cap" lock).
2. If `daily_cap` is not None: `SELECT COALESCE(SUM(doc_count),0) FROM checks WHERE mode='live' AND created_at > now() - interval '24 hours'`.
   If `used + doc_count > daily_cap`, raise `CapExceeded("daily")`.
3. If `client_cap` is not None: the same over `interval '1 hour'` and `client_hash = %s`. If over, raise
   `CapExceeded("client")`.
4. `INSERT ... RETURNING id`. Return `str(id)`.

`finish_check` updates `status` and `result` (`psycopg.types.json.Jsonb(result)` when not None). Always use
parameterized queries, never f-string SQL.

### `P/tests/test_db.py`
- Module-level: `pytest.importorskip("psycopg")`. Skip the module if `TEST_DATABASE_URL` is unset.
- Module fixture: run `migrate.migrate(TEST_DATABASE_URL)` twice (the second run returns `[]`, so it's idempotent).
- Each test uses a unique `client_hash` (`uuid4().hex`) so tests don't interfere. Global-cap tests read the
  current global live usage first and set `daily_cap = used + N`.
- Cases: reserve then finish round-trips `status`/`result`. Client cap blocks the 2nd reserve when
  `doc_count` sums past the cap (raises `CapExceeded("client")`). Daily cap raises `CapExceeded("daily")`.
  Offline-mode rows don't count toward caps. `purge` deletes a row whose `created_at` was backdated 31 days
  (via `UPDATE`) and keeps a fresh one.
- A concurrency test: 2 threads, each with its own connection, reserving against a `client_cap` that allows
  only one. Exactly one succeeds.

To run DB tests locally, use any throwaway Postgres: a Neon dev branch, or local `postgres` (`psql` is installed).
For example `TEST_DATABASE_URL=postgresql://localhost/postgres`. Never use the production database.

## Do not
- Touch `app.py` or any file outside the `files` list.
- Add an ORM, a pool library or async drivers.
- Print or log connection strings.
- Create or switch branches, commit, or push.

## Done when
```bash
cd /Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments/ruri-bot/prototype
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m pytest -q                                          # DB tests skipped without TEST_DATABASE_URL
.venv/bin/python -m compileall -q -x '\.venv' .
TEST_DATABASE_URL=<throwaway> .venv/bin/python -m pytest -q tests/test_db.py   # all pass, none skipped
```
- `DATABASE_URL=<throwaway> .venv/bin/python migrate.py` prints `applied 001_checks`, then `up to date` on the second run.
