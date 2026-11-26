---
type: prompt
plan: "[[2026-11-26-mvp-hardening]]"
id: 05
unit:
status: todo
model: opus
effort: high
depends_on: [02, 03, 04]
parallel_group: E
files:
  create:
    - ruri-bot/prototype/tests/test_caps.py
  modify:
    - ruri-bot/prototype/app.py
    - ruri-bot/prototype/check_samples.py
    - ruri-bot/prototype/tests/test_app.py
  delete: []
---
# 05 · Wire acknowledgement, caps, audit log and fail-closed into `/check`

## Task
Make `/check` do the following:
- require the synthetic-data acknowledgement
- enforce the cost caps in live mode
- write one audit row per check to Postgres through `db.py`
- fail closed on Vercel when the DB or the salt is missing
- return the `check_id`

Update the two callers that build the form by hand.

**Why opus:** this is the cost and abuse gate on a public, unauthenticated endpoint that receives personal
data. A wrong branch either spends money without limit or logs data without the guards.

## Context
- Repo root: `/Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments`. App dir `P/` =
  `ruri-bot/prototype/`. Python 3.12 venv `P/.venv`.
- `db.py` (prompt 03), the API to use as-is: `url()`, `connect(dsn=None)` (autocommit, 5 s timeout),
  `reserve_check(conn, *, mode, model, policy_sha, prompt_sha, client_hash, doc_count, applicant, daily_cap, client_cap) -> str`
  (raises `CapExceeded` with `.kind` in `{"daily","client"}`), `finish_check(conn, check_id, *, status, result)`,
  and `purge(conn, days=30)`. `migrate.migrate(url)` applies the schema.
- `app.py` after prompt 02: `mode()`, `MODEL`, `POLICY_SHA`, `PROMPT_SHA`, `today_ph()`, `read_all(blobs)` run via
  `run_in_threadpool`, a `MAX_TOTAL_BYTES` 413, and the JSON 500 handler. `/check` signature today:
  `check(applicant: str = Form(""), use_samples: str = Form(""), files: list[UploadFile] = File(default=[]))`.
- The UI (prompt 04) already sends `synthetic_ack=1` and handles 429/503 `detail` and `check_id`.
- Decisions (locked):
  - **D2.** Public, no login. Caps apply **only in `live` mode**: `DAILY_DOC_CAP` (env, default 300 docs per
    rolling 24 h, all clients) and `IP_HOURLY_DOC_CAP` (env, default 36 docs per rolling hour per client).
    Read the env at request time (`int(os.environ.get(...) or default)`).
  - **D3.** Store no files. The row's `result` = `{"items", "unrecognised", "counts", "documents"}` from the
    response. Purge rows older than 30 days on each check that has a DB connection.
  - **D6 fail closed.** `on_vercel = bool(os.environ.get("VERCEL_ENV"))`. If `on_vercel and mode()=="live"`:
    a missing `db.url()` or missing `IP_HASH_SALT` returns **503** `"Service not configured. Try again later."`.
    So does any exception from `db.connect()`/`reserve_check` other than `CapExceeded`. Off Vercel (local dev):
    no DB URL means run without audit or caps, exactly as today. A DB error locally is logged, and the check
    continues without audit.
  - Offline mode on Vercel (previews): audit if a DB is configured, never cap, never 503 for a missing DB.
- **Client identity:** `client_ip(request)` = `x-real-ip` header, else the first comma-separated value of
  `x-forwarded-for`, else `request.client.host`, else `"unknown"`.
  `client_hash = sha256(f"{IP_HASH_SALT}|{ip}".encode()).hexdigest()[:32]`, with salt `""` off Vercel. Never store
  or log the raw IP.
- **Never hash with an empty salt on Vercel (D15).** On Vercel with no `IP_HASH_SALT`: live → 503 (D6). Offline →
  run the check **without** an audit row (`check_id` None, no `reserve_check`) and `log.warning("IP_HASH_SALT unset; audit skipped")`.

### `/check` flow (order matters)
1. Add params `request: Request` and `synthetic_ack: str = Form("")`.
2. Validate `applicant` (unchanged) → `mode()=="none"` 503 (unchanged) → `synthetic_ack != "1"` returns
   **400** `"Confirm these are synthetic test documents (tick the box)."`
3. Collect the blobs (unchanged limits). `doc_count = len(blobs)`.
4. Resolve the DB per D6. If there's a connection: `purge(conn)`, then
   `check_id = reserve_check(..., daily_cap=<cap> if live else None, client_cap=<cap> if live else None)`.
   - `CapExceeded("daily")` returns **429** `"Today's usage limit for this demo has been reached. Try again tomorrow."`
   - `CapExceeded("client")` returns **429** `"You've reached the hourly limit for this demo. Try again in an hour."`
     with header `Retry-After: 3600`.
   - The reservation happens **before** any model call, so reads are only paid for after the cap check passes.
5. `results = await run_in_threadpool(read_all, blobs)`, then `evaluate(...)`. Wrap steps 5–6 in
   `try/except`. On exception, if there's a `check_id`, run `finish_check(..., status="failed", result=None)`
   (swallow and log a secondary DB error), then re-raise.
6. `finish_check(conn, check_id, status="done", result={...})`. Close the connection in `finally`.
7. Response: the existing keys plus `"check_id": check_id` (`None` when no DB).

Keep the DB calls synchronous and short. Run `connect`/`purge`/`reserve_check`/`finish_check` through
`run_in_threadpool`, so the event loop isn't blocked.

### Callers to update
- `P/check_samples.py:17-18`: add the multipart part `synthetic_ack` = `1` to the hand-built body.
- `P/tests/test_app.py`: every `/check` POST that expects a non-400 result sends `synthetic_ack=1`. Add
  `test_missing_ack_400`.

### Tests: `P/tests/test_caps.py`
Use a fake DB, monkeypatching `app.db` functions so the logic is tested without Postgres. Also add one real-DB
test gated on `TEST_DATABASE_URL`, using `migrate.migrate` first.
- Live mode (`ANTHROPIC_API_KEY=x`, with `app.read_live` monkeypatched to return a valid dict and count calls,
  so nothing hits the network):
  - client cap: `reserve_check` raises `CapExceeded("client")` → 429 + `Retry-After`. Assert that `read_live`
    was **never called**.
  - daily cap → 429.
  - `VERCEL_ENV=production` with no `DATABASE_URL` → 503, and `read_live` not called. The same with
    `DATABASE_URL` set but no `IP_HASH_SALT`.
  - `VERCEL_ENV=production` with `db.connect` raising → 503.
- Off Vercel with no `DATABASE_URL`: offline sample set → 200 and `check_id is None`.
- `evaluate` raising after reserve → `finish_check` called with `status="failed"`, and the response is 500 JSON.
- `VERCEL_ENV=preview`, offline, a `DATABASE_URL` set, no `IP_HASH_SALT` → 200, `check_id is None`, `reserve_check` not called.
- The `client_hash` passed to `reserve_check` differs for `x-real-ip: 1.2.3.4` vs `5.6.7.8`, and never contains the IP.
- Real DB (`TEST_DATABASE_URL`, offline mode, `DATABASE_URL` monkeypatched to it): one check writes exactly
  one `done` row whose `result.counts` match the response and whose `policy_sha`/`prompt_sha` match `/status`.

## Do not
- Change `db.py`'s API. If it's insufficient, stop and report.
- Change rules, `PROMPT`, `policy.yaml` or the 01/02 behaviours beyond the ack requirement.
- Log applicant names, IPs, document content, keys or connection strings.
- Touch files outside the `files` list. Create or switch branches, commit, or push.

## Done when
```bash
cd /Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments/ruri-bot/prototype
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q -x '\.venv' .
TEST_DATABASE_URL=<throwaway> .venv/bin/python -m pytest -q tests/test_db.py tests/test_caps.py   # none skipped
```
- `DEMO_OFFLINE=1 .venv/bin/uvicorn app:app --port 8000` + `.venv/bin/python check_samples.py` prints PASS.
- Same server: the UI sample button works with the box ticked. Unticked, the "Check file" request returns the 400 message.
