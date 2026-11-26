---
type: plan
kind: feature
status: draft
repo: amihan-inclusive-payments
delivery: local
base:
sprint:
epic:
created: 2026-11-26
risk: medium
prompts: 8
graph_built: none
tags: [plan]
---
# MVP hardening: Vercel + Neon + GitHub, operated through MCPs

## Request
> mvp hardening. we will be connecting MCPs to this and deploy a live URL. we will be using github, neon db, vercel

| # | Requirement |
|---|---|
| R1 | Harden the prototype (`sandro-proposal/prototype/`) so it is safe and robust on a public URL. That covers input coercion, upload and time limits, error handling, security headers, no public API docs, and an offline test suite. |
| R2 | Deploy it to a live URL on **Vercel**. |
| R3 | Use **Neon Postgres** for an audit log of each check (no files) and to enforce cost caps. |
| R4 | Use **GitHub** as the deploy source: Vercel Git integration (preview per PR, production on `main`) plus a CI workflow that gates PRs. |
| R5 | "Connect MCPs": run setup and operations (Neon project, migration, Vercel project, env vars, deploy, branch protection) through the GitHub, Neon and Vercel MCP servers or CLIs. The app itself gets **no** MCP code. |
| R6 | Public live access, no login. Abuse and cost are bounded by a global daily cap and a per-client hourly cap (Decision D2). |

## Context used
- `sandro-proposal/PROBLEM.md` §5–6: the outputs must be auditable (sourced, reproducible). Borrower data is sensitive personal information under the DPA. Human-in-the-loop is mandatory. Thin IT and low connectivity is the main constraint (light pages, resumable uploads).
- `sandro-proposal/PROBLEM.md` §8 Q5: whether borrower data may go to a cloud model is **still open**. This is the basis for keeping "synthetic data only".
- `sandro-proposal/prototype/README.md`: run modes `live`, `offline` and `none`. "Not in the prototype: auth, storage, resumable uploads…"
- `sandro-proposal/chat.md` (build session): the model only reads documents and `policy.yaml` decides what is required. Haiku was chosen for cost. The production stack was explicitly not chosen yet.
- Code: `sandro-proposal/prototype/app.py:31-35`: policy loaded at import. `MAX_BYTES=10MB` per file and 12 files, which exceeds Vercel's 4.5 MB request-body limit.
- Code: `app.py:101-108` `read_live`: Anthropic client has no timeout or retry settings.
- Code: `app.py:119-129` `clean`: `bool("false")` is `True`. A non-string `name_on_document` or date passes through, and `names_match`/`parse_date` then raise outside the per-file `try` (`app.py:269`). That is a 500 for the whole check.
- Code: `app.py:236-272` `/check`: `async def` doing blocking thread-pool work on the event loop. Uses `date.today()`, which is UTC on Vercel, not PH time.
- Code: `app.py:55` `FastAPI(...)` exposes `/docs` and `/openapi.json` publicly.
- Code: `static/index.html:113-129` `run()`: calls `r.json()` on every response, so a non-JSON 413/500/504 from Vercel shows "Unexpected token…".
- Code: `check_samples.py:17-18`: builds the `/check` multipart by hand. It's coupled to the form fields.
- Repo: no `.gitignore`. `__pycache__/app.cpython-315.pyc` and `sandro-proposal/.DS_Store` are tracked. Local `.venv` is Python 3.15 and requirements are unpinned.
- Vercel docs (search via the Vercel MCP): FastAPI zero-config detects `app.py` → `app`. `.python-version` sets the runtime. `vercel.json` `functions["app.py"].maxDuration` and `excludeFiles`. `public/` is served by the CDN. The Neon Marketplace integration injects `DATABASE_URL` per environment.
- Tools on this machine: `uv`, `gh` (authenticated) and `psql` are present. The `vercel` and `neonctl` CLIs are not installed. The Vercel MCP is connected in Claude. The Neon and GitHub MCPs are **not** connected yet.
- No graph (`graphify-out/` absent). The repo is ~600 lines, so grep was enough.

## Options
The one real design choice is how uploads get past Vercel's 4.5 MB request body limit.

| Option | Cost | Time | Risk | Maintenance | Compliance |
|---|---|---|---|---|---|
| A. Client-side downscale to 1568 px JPEG + 4 MB total cap, one `/check` request | none | S | Large PDFs rejected with a clear message | Low | Files never stored |
| B. One request per document (`/read`), results kept in Neon, then `/evaluate` | none | M | More endpoints and state; resumable | Medium | Extractions stored mid-flow |
| C. Vercel Blob client uploads, server fetches | Blob storage | M | Larger surface | Medium | **Stores documents at rest**, which contradicts D3 |

**Recommendation:** A. The server already downscales to 1568 px (`app.py:35`), so doing it in the browser changes nothing about reading quality. It also cuts upload size on weak connections, which is the PROBLEM.md constraint. B is the right move when "resumable uploads" becomes a feature; it's deferred. **Chosen:** A (CTO call; one sensible option for hardening. `/audit-plan` may challenge).

## Decisions
- **D1 MCP scope = ops only.** GitHub, Neon and Vercel MCPs (or `gh`/CLI fallbacks) provision and operate. The app exposes no MCP server. *(user, 2026-11-26)*
- **D2 Access = public live, caps only.** No login. *(user, 2026-11-26)* **CTO pushback, recorded:** a public live URL invites real borrower uploads. Those go to a cloud model while PROBLEM.md §8 Q5 is unresolved, and names land in Neon. The cheap guards below keep the user's choice:
  - A required "synthetic test documents only" acknowledgement (UI checkbox and server-enforced `synthetic_ack=1`), plus a visible data notice.
  - A global cap `DAILY_DOC_CAP` (default 300 documents per rolling 24 h) and a per-client cap `IP_HOURLY_DOC_CAP` (default 36 per rolling hour), counted in Neon. Both apply in live mode only.
  - An **Anthropic workspace spend limit** set in the Anthropic Console. It's the hard backstop if the app's cap has a bug.
  - **Preview deployments get no `ANTHROPIC_API_KEY`.** They run `DEMO_OFFLINE=1`, so per-PR public URLs can't spend.
- **D3 Neon stores an audit log, not files.** One `checks` row per check: applicant, per-document extraction, gap result, mode, model, `policy_sha`, `prompt_sha`, salted client hash, doc count, status, timestamp. Rows older than 30 days are purged opportunistically on each check. *(user, 2026-11-26)*
- **D4 Commands** = pytest (offline, TestClient; DB tests skip without `TEST_DATABASE_URL`) + compileall. The same steps run in GitHub Actions with a Postgres service. *(user, 2026-11-26)*
- **D5 Delivery = `local`.** There's no Jira key or TASKS.md, so no units. Prompts run in order on the current branch. Vercel/GitHub PR previews still work whenever the user pushes.
- **D6 Fail closed on Vercel.** When `VERCEL_ENV` is set and mode is `live`, a missing `DATABASE_URL`/`IP_HASH_SALT` or a DB connection failure returns 503. Caps can't be enforced without the DB. Locally (no `VERCEL_ENV`) the app runs without the DB, as today.
- **D7 Exact caps under concurrency.** The usage count and the row insert run in one transaction behind `pg_advisory_xact_lock`, so concurrent requests can't overshoot.
- **D8 Runtime = Python 3.12** via `.python-version`. Pinned `requirements.txt`. Local `.venv` rebuilt on 3.12 with `uv` so local matches Vercel and CI.
- **D9 Region = Vercel `sin1` + Neon `aws-ap-southeast-1` (Singapore)**, the closest to PH users. Keeping both in one region avoids a cross-ocean DB round trip.
- **D10 Time budget.** Anthropic client `timeout=25s, max_retries=1`. Thread pool 6 workers (12 docs = 2 waves). `maxDuration=120` s.
- **D11 Use the PH date for rules.** `date.today()` → today in UTC+8 (fixed offset; PH has no DST, and it needs no tzdata).

**Assumptions:** (for `/audit-plan` to challenge)
- Vercel rejects request bodies above **4.5 MB** before the app runs, so the app caps the total at **4,000,000 bytes** to leave room for multipart overhead.
- On Vercel, `x-real-ip` is set by the platform and can't be spoofed by the client. Fallback order: `x-real-ip` → first `x-forwarded-for` → `request.client.host`.
- The Vercel FastAPI preset bundles `static/` and `samples/` into the function by default (`/` reads `static/index.html` and `use_samples` reads `samples/*.png`). Verified by the preview smoke test in prompt 08.
- Vercel Hobby allows one function region (`"regions": ["sin1"]`) and `maxDuration` 120 under Fluid compute.
- The Neon Marketplace integration exposes `DATABASE_URL` (pooled) and `DATABASE_URL_UNPOOLED`. The app uses the pooled one; `migrate.py` prefers the unpooled one.
- `psycopg[binary]` 3.x has wheels for CPython 3.12 (it does for macOS arm64 and manylinux).
- Rebuilding `sandro-proposal/prototype/.venv` (untracked) on 3.12 is acceptable. The user's current 3.15 venv is replaced.
- The repo will stay **public** on GitHub. Nothing secret is committed. `.env.example` holds names only.

**Non-goals:** auth or login; an MCP server inside the app; storing documents (Blob); resumable or per-document uploads (Option B); cash-flow, cross-checks, LOS data (PROBLEM.md v2); moving the app out of `sandro-proposal/prototype/`; a custom domain; Filipino-language output; a rate-limit WAF rule; changing `policy.yaml` or the extraction prompt text.

## Change list
Paths are relative to the repo root. `P/` = `sandro-proposal/prototype/`.

| File | Action | Why | Req | Prompt |
|---|---|---|---|---|
| `.gitignore` | C | Stop tracking venv, pyc, .DS_Store, .env*, .vercel | R1, R4 | 01 |
| `P/__pycache__/app.cpython-315.pyc`, `sandro-proposal/.DS_Store` | D (untrack) | Build junk in git | R4 | 01 |
| `P/.python-version` | C | Pin the Vercel and CI runtime to 3.12 | R2, D8 | 01 |
| `P/requirements.txt` | M | Pin exact versions (01); add `psycopg[binary]` (03) | R1, R3 | 01, 03 |
| `P/requirements-dev.txt` | C | pytest and the TestClient dependency | R1, D4 | 01 |
| `P/tests/conftest.py`, `P/tests/test_app.py` | C | Offline baseline: sample set, errors, name matching | R1, D4 | 01 |
| `P/app.py` | M | Coercion, PH date, timeouts, upload cap, headers, no docs, JSON 500, hashes, threadpool | R1 | 02 |
| `P/tests/test_hardening.py` | C | Tests for each hardening change | R1 | 02 |
| `P/db/001_checks.sql` | C | `checks` table + indexes | R3 | 03 |
| `P/db.py` | C | Connect, `reserve_check` (lock + caps + insert), `finish_check`, `purge` | R3, R6 | 03 |
| `P/migrate.py` | C | Applies `db/*.sql` in order, records them in `schema_migrations` | R3, R5 | 03 |
| `P/tests/test_db.py` | C | DB tests (skip without `TEST_DATABASE_URL`) | R3 | 03 |
| `P/static/index.html` | M | Ack checkbox + notice, client downscale, size precheck, non-JSON errors, reference id | R1, R6 | 04 |
| `P/app.py` | M | Wire ack, caps, audit and fail-closed into `/check`; return `check_id` | R3, R6, D6 | 05 |
| `P/check_samples.py` | M | Send `synthetic_ack=1` | R6 | 05 |
| `P/tests/test_app.py` | M | Send `synthetic_ack=1` in existing tests | R6 | 05 |
| `P/tests/test_caps.py` | C | Ack, caps (429), fail-closed (503), audit row | R3, R6 | 05 |
| `P/vercel.json` | C | `sin1`, `maxDuration` 120, exclude `tests/**` from the bundle | R2, D9, D10 | 06 |
| `.github/workflows/ci.yml` | C | PR/main CI: Python 3.12, Postgres service, migrate, pytest | R4 | 06 |
| `P/.env.example` | C | Env var names (no values) | R2, R5 | 06 |
| `P/README.md` | M | Deploy, env vars, caps, data handling, ops runbook | R2, R5 | 07 |
| `CLAUDE.md` | C | Project profile: Commands, High-stakes paths, Hidden coupling | D4 (workflow §1) | 07 |
| — (cloud resources, no repo files) | — | Neon project, migration, Vercel project + env, Anthropic limit, branch protection, smoke test | R2–R5 | 08 |

## Blast radius
**Risk:** medium. The codebase is tiny and greenfield, with no existing data. The real exposure is operational: a public, unauthenticated endpoint that spends money and receives personal data (D2).

| Affected | Kind | Via | Breaks? | Mitigation |
|---|---|---|---|---|
| `check_samples.py` | Non-graph (HTTP form contract) | `/check` fields | **Yes** once `synthetic_ack` is required (05) | 05 adds the field |
| `static/index.html` `run()` | Direct (HTTP contract) | `/check` fields and status codes | **Yes** for ack/429/413 | 04 runs **before** 05 and sends `synthetic_ack=1` (ignored until 05) |
| `tests/test_app.py` (from 01) | Direct | `/check` | Yes when ack is required | 05 updates it |
| `/check` response JSON | HTTP contract | Additive `check_id`, `policy_sha`, `prompt_sha` | No: additive. UI and check_samples ignore unknown keys | — |
| Uploads > 4 MB total | Behaviour | `MAX_TOTAL_BYTES` (02) | Rejects large uncompressed photo sets between 02 and 04 (local only) | 04's client downscale; clear 413 message |
| `samples/expected.json` | Non-graph | Rules + PH date | No. Statuses don't depend on a ±1-day date shift. Sidecar booleans are real `true`/`false` | 01 baseline test pins it |
| `clean()` stricter coercion | Direct (`read_one`, `evaluate`) | Model output | No for valid output. Malformed values become `None`/`False` instead of crashing | 02 tests |
| `generate_samples.py` | — | Unchanged | No | — |
| `.venv` (untracked) | Local env | Rebuilt on 3.12 | README commands unchanged (`.venv/bin/...`) | 01 |
| Env keys | Non-graph | `ANTHROPIC_API_KEY`, `DEMO_OFFLINE`, `CASE_MODEL`, new `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `IP_HASH_SALT`, `DAILY_DOC_CAP`, `IP_HOURLY_DOC_CAP`, platform `VERCEL_ENV` | Must match across `app.py`, `db.py`, `.env.example`, README, Vercel env, CI | 06/07 list them; 08 sets them |
| DB table `checks`, `schema_migrations` | Non-graph | `db.py` SQL ↔ `db/001_checks.sql` | New, so nothing else reads them | 03 tests run against the real schema |
| Vercel bundle | Platform | `vercel.json` `excludeFiles` | Excluding `static/` or `samples/` would break `/` and the sample button | 06 excludes only `tests/**`; 08 smoke-tests both |

**Known risks in the touched area:**
- PROBLEM.md §6/§8 Q5: cloud-model processing of borrower data is **unapproved**. The live URL must stay synthetic-only (D2 guards).
- Extraction accuracy on real photos is untested (chat.md: "the live Claude call… untested"). The first live run is the real test.
- `policy.yaml` clause IDs are placeholders and must not be presented as real policy. The UI note stays.

## Prompts
| # | Title | Unit | Model | Effort | Depends | Group | Files |
|---|---|---|---|---|---|---|---|
| 01 | Test baseline, pinning, repo hygiene | — | sonnet | medium | — | A | `.gitignore`, `P/.python-version`, `P/requirements*.txt`, `P/tests/conftest.py`, `P/tests/test_app.py`; untrack 2 files |
| 02 | App hardening (no DB) | — | sonnet | high | 01 | B | `P/app.py`, `P/tests/test_hardening.py` |
| 03 | Neon data layer + migration | — | sonnet | high | 01 | C | `P/db/001_checks.sql`, `P/db.py`, `P/migrate.py`, `P/tests/test_db.py`, `P/requirements.txt` |
| 04 | UI hardening | — | sonnet | medium | 02 | D | `P/static/index.html`, `P/tests/test_hardening.py` |
| 05 | Wire ack, caps, audit, fail-closed into `/check` | — | **opus** | high | 02, 03, 04 | E | `P/app.py`, `P/check_samples.py`, `P/tests/test_app.py`, `P/tests/test_caps.py` |
| 06 | Vercel config + GitHub CI | — | sonnet | medium | 05 | F | `P/vercel.json`, `.github/workflows/ci.yml`, `P/.env.example` |
| 07 | Docs + project profile | — | haiku | low | 06 | G | `P/README.md`, `CLAUDE.md` |
| 08 | Go live via MCPs (interactive ops) | — | sonnet | medium | 07 | H | none (cloud resources) |

Every prompt runs sequentially: they share `app.py`, `requirements.txt`, the tests and the venv. 02 and 03 have disjoint files but share the venv and test run, so they stay in separate groups.

- **05 → opus:** it's the cost and abuse gate and the fail-closed logic on a public, unauthenticated endpoint that receives personal data. A wrong branch spends money or logs PII without the guards.
- **08 is interactive:** run it in the main session, not as a subagent. Every outward action (creating cloud resources, setting secrets, branch protection) needs the user's confirmation.

## End-to-end verification
```bash
cd sandro-proposal/prototype
# ## Commands (D4)
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q -x '\.venv' .

# R1: offline sample set end to end through a real server
DEMO_OFFLINE=1 .venv/bin/uvicorn app:app --port 8000 &  SERVER=$!; sleep 2
.venv/bin/python check_samples.py                 # PASS
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/docs           # 404
curl -sI localhost:8000/ | grep -i -e content-security-policy -e x-content-type-options
kill $SERVER

# R3/R6: DB-backed tests against a throwaway Postgres (local, or a Neon dev branch)
TEST_DATABASE_URL="$TEST_DATABASE_URL" .venv/bin/python -m pytest -q tests/test_db.py tests/test_caps.py   # none skipped

# R4: CI green on the PR, and required on main
gh run list --workflow ci.yml --limit 1
gh api repos/alessandrocruz5/amihan-inclusive-payments/branches/main/protection --jq '.required_status_checks.contexts'

# R2/R5: live URL (after 08)
.venv/bin/python check_samples.py https://<prod-domain>            # PASS, mode=live
curl -s https://<prod-domain>/status                              # mode live, policy_sha present
curl -s -o /dev/null -w '%{http_code}\n' https://<prod-domain>/docs   # 404
curl -s https://<preview-domain>/status                           # mode offline (no key on previews)
```

## Rollback
- **App:** Vercel instant rollback to the previous production deployment (Vercel MCP `request_rollback`). Or `git revert` the commits and push.
- **Stop spending immediately:** remove `ANTHROPIC_API_KEY` from Production and set `DEMO_OFFLINE=1`, then redeploy. The app falls back to offline mode. The Anthropic Console spend limit is the backstop.
- **DB:** `DROP TABLE checks; DROP TABLE schema_migrations;` Nothing else uses them. Or delete the Neon project.
- **Repo hygiene (01):** revert `.gitignore` and re-add the untracked files if ever needed.

## Log
- 2026-11-26: planned
