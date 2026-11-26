---
type: prompt
plan: "[[2026-11-26-mvp-hardening]]"
id: 02
unit:
status: todo
model: sonnet
effort: high
depends_on: [01]
parallel_group: B
files:
  create:
    - sandro-proposal/prototype/tests/test_hardening.py
  modify:
    - sandro-proposal/prototype/app.py
  delete: []
---
# 02 · App hardening (no database)

## Task
Make `app.py` safe to run on a public serverless URL. Coerce model output strictly, use the PH date, bound
the Anthropic time budget, cap the total upload size, hide the API docs, add security headers, return JSON
on unexpected errors, expose policy and prompt hashes, and stop blocking the event loop. Add tests for each
change. Keep every existing behaviour that `tests/test_app.py` checks.

## Context
- Repo root: `/Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments`. App dir `P/` =
  `sandro-proposal/prototype/`. Python 3.12 venv at `P/.venv`. Tests: `P/tests/` (`conftest.py` gives
  `client` and `offline` fixtures and clears `ANTHROPIC_API_KEY`/`DEMO_OFFLINE`/`VERCEL_ENV`).
- Design rule (keep it): **the model only reads documents. Plain code + `policy.yaml` decides.** Don't
  change `PROMPT` text, `policy.yaml`, `evaluate`, `problems_for` or `gap_text`.
- `app.py` landmarks (line numbers as of plan time):
  - `:29-35` constants: `MAX_FILES = 12`, `MAX_BYTES = 10 * 1024 * 1024`, `MAX_SIDE = 1568`.
  - `:55` `app = FastAPI(title="Agri loan gap list (prototype)")`.
  - `:101-108` `read_live`: `anthropic.Anthropic()` with no timeout.
  - `:119-129` `clean(x)`.
  - `:132-140` `read_one`: per-file try/except.
  - `:230-233` `/status`.
  - `:236-272` `/check`: `async def`. Runs `ThreadPoolExecutor(max_workers=4)` inline. Calls
    `evaluate(applicant, docs, date.today())`.

### Changes (all in `app.py`)
1. **Strict `clean()`.** `legible` is `True` only if the value `is True` (today `bool("false")` is `True`).
   `doc_type` must be a `str` in `DOC_TYPES`, else `"other"`. `name_on_document` is a stripped non-empty `str`,
   else `None`. A non-str becomes `None`. `issue_date`/`expiry_date` keep only a `str` matching
   `^\d{4}-\d{2}-\d{2}$` that `date.fromisoformat` accepts, else `None`. `legibility_note` is `str(...)`
   truncated to 200 characters. Also guard `x` not being a dict: treat it as `{}`. Today a non-str name
   crashes `names_match` outside the per-file try (`/check` → `evaluate`), which makes the whole check a 500.
2. **PH date:** `PH_TZ = timezone(timedelta(hours=8))` (fixed offset, no tzdata). `def today_ph(): return datetime.now(PH_TZ).date()`.
   `/check` uses `today_ph()` instead of `date.today()`.
3. **Time budget:** in `read_live` use `anthropic.Anthropic(timeout=25.0, max_retries=1)`. Thread pool
   `max_workers=6`. Keep the lazy import.
4. **Upload cap:** replace `MAX_BYTES` with `MAX_TOTAL_BYTES = 4_000_000`. Vercel rejects bodies above
   4.5 MB, so this leaves room for multipart overhead. While reading uploads, keep a running total. If it
   exceeds the cap, raise `HTTPException(413, "Files total more than 4 MB. Photos are shrunk automatically in the page; split large PDFs into separate checks.")`.
   Keep `MAX_FILES` (400 when exceeded).
5. **No public API docs:** `FastAPI(title=..., docs_url=None, redoc_url=None, openapi_url=None)`.
6. **Security headers:** an `@app.middleware("http")` that sets these on every response:
   `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`,
   `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`.
   `'unsafe-inline'` is needed because `static/index.html` has inline `<script>` and `<style>`.
7. **JSON on unexpected errors:** `@app.exception_handler(Exception)` returns
   `JSONResponse(status_code=500, content={"detail": "Something went wrong on the server. Try again."})`,
   and logs with `logging.getLogger("app").exception(...)`. HTTPException keeps FastAPI's own handler.
   In `read_one`'s except, add `log.warning("read failed: %s", type(e).__name__)`. Never log document
   content, names or keys.
8. **Audit hashes:** at import, `POLICY_SHA = sha256(policy.yaml bytes).hexdigest()[:12]` and
   `PROMPT_SHA = sha256(PROMPT.encode()).hexdigest()[:12]`. Add both to the `/status` JSON and to the `/check`
   response (additive keys `policy_sha`, `prompt_sha`).
9. **Don't block the event loop:** move the thread-pool read into a sync helper
   `read_all(blobs) -> list[dict]` and call it with `await run_in_threadpool(read_all, blobs)`
   (`from starlette.concurrency import run_in_threadpool`).

### Tests: `P/tests/test_hardening.py`
- `clean`: `{"legible": "false"}` → `legible False`. `name_on_document: 123` → `None`.
  `issue_date: 20240101` → `None`. `issue_date: "2024-13-40"` → `None`. `doc_type: ["x"]` → `"other"`.
  Non-dict input → all defaults.
- `/check` offline with a monkeypatched `app.read_offline` returning
  `{"doc_type":"national_id","legible":True,"name_on_document":123}` → 200 (not 500), and the identity row is `problem`.
- `today_ph()`: with time frozen at 2026-01-01T17:00Z (monkeypatch a module-level clock or `app.datetime`),
  it returns 2026-01-02.
- Upload over the cap: two files of 2,100,000 bytes → 413.
- `GET /docs` and `GET /openapi.json` → 404.
- `GET /` has the CSP, `nosniff` and `X-Frame-Options` headers.
- `/status` has 12-hex `policy_sha` and `prompt_sha`.
- Unexpected error → JSON 500. Monkeypatch `app.evaluate` to raise, use
  `TestClient(app.app, raise_server_exceptions=False)`, and assert `r.json()["detail"]`.

## Do not
- Touch files outside the `files` list (`tests/test_app.py` must keep passing unmodified).
- Change `PROMPT`, `policy.yaml`, `evaluate`, `problems_for`, `gap_text`, `names_match` or `DOC_TYPES`.
- Add dependencies (`starlette`, `logging` and `hashlib` are already available).
- Create or switch branches, commit, or push.

## Done when
```bash
cd /Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments/sandro-proposal/prototype
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q -x '\.venv' .
```
- `DEMO_OFFLINE=1 .venv/bin/uvicorn app:app --port 8000` + `.venv/bin/python check_samples.py` prints PASS.
