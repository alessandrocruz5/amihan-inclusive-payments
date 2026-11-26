---
type: prompt
plan: "[[2026-11-26-mvp-hardening]]"
id: 07
unit:
status: todo
model: haiku
effort: low
depends_on: [06]
parallel_group: G
files:
  create:
    - CLAUDE.md
  modify:
    - ruri-bot/prototype/README.md
  delete: []
---
# 07 · Docs + project profile

## Task
Update the prototype README for the deployed MVP, and create the repo's `CLAUDE.md` project profile so future
`/plan-feature`, `/audit-plan` and `/build-unit` runs have commands and constraints. Write docs only. Copy
facts from this prompt; don't invent any.

## Context
- Repo root: `/Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments`. App dir:
  `ruri-bot/prototype/`. The README today has sections `# Agri loan gap-list prototype`, `## Run`,
  `## Sample set` and `## Not in the prototype`. Keep its terse style: short sentences, code blocks for commands.
- Facts to document:
  - Hosting: Vercel (FastAPI preset), Root Directory `ruri-bot/prototype`, region `sin1`,
    `maxDuration` 120 s. Deploys: every PR gets a preview (offline mode, no Anthropic key). `main` is production.
  - Database: Neon Postgres (`aws-ap-southeast-1`) through the Vercel Marketplace integration
    (`DATABASE_URL`, `DATABASE_URL_UNPOOLED`). Schema in `db/*.sql`. Apply with
    `DATABASE_URL_UNPOOLED=... .venv/bin/python migrate.py`.
  - Data handling: synthetic documents only (the PROBLEM.md §8 Q5 cloud-processing question is still open).
    Documents are sent to Anthropic's Claude API and processed under its API data terms; this app does not store them. Each check writes one `checks` row (applicant, extractions, gap result, mode,
    model, `policy_sha`, `prompt_sha`, salted client hash, doc count). Rows are deleted after 30 days. The page
    requires a "synthetic documents" tick.
  - GitHub: the repo is private. If the GitHub plan can't enforce required checks, CI is advisory (say so plainly).
  - Cost controls: live mode only, `DAILY_DOC_CAP` (default 300 docs per rolling 24 h) and
    `IP_HOURLY_DOC_CAP` (default 36 docs per rolling hour per client) → HTTP 429. On Vercel, live mode
    without DB or `IP_HASH_SALT` → 503 (fail closed). Backstop: an Anthropic Console workspace spend limit.
  - Limits: 12 files and 4 MB total per check. The page shrinks photos to 1568 px before upload.
  - Env vars: point to `.env.example` (don't duplicate values).
  - Tests: `.venv/bin/python -m pytest -q`. DB tests need `TEST_DATABASE_URL` (a throwaway Postgres, never prod).
    CI: `.github/workflows/ci.yml` on every PR and on `main`.
  - Ops through MCPs: the Vercel MCP (project, env vars, deployments, logs, rollback), the Neon MCP (branches, SQL)
    and the GitHub MCP or `gh` (PRs, branch protection).
  - Rollback: Vercel instant rollback. To stop spend, remove `ANTHROPIC_API_KEY` from Production, set
    `DEMO_OFFLINE=1`, and redeploy.

### README changes (`ruri-bot/prototype/README.md`)
- Retitle the intro line to mention it's deployed as an MVP. Keep the "Synthetic data only" paragraph and extend
  it with the data-handling facts above.
- `## Run`: replace the venv bootstrap with `uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements-dev.txt`.
  Keep the live/offline run commands. `check_samples.py` stays, and now also takes a URL argument
  (`.venv/bin/python check_samples.py https://<domain>`).
- New sections: `## Tests`, `## Deploy (Vercel + Neon)`, `## Cost and abuse controls`, `## Operations and rollback`.
- `## Not in the prototype`: remove "auth" → keep it but say "login (public, capped)". Remove "storage" →
  "document storage (only the audit log is kept)". Keep the rest.

### `CLAUDE.md` (repo root), exactly these headings
```markdown
# amihan-inclusive-payments

## Project
Prototype → MVP of a loan-file gap-list agent for rural-bank agri loans (Talino Fintech Foundry branding).
App: `ruri-bot/prototype/` (FastAPI + one HTML page). Problem: `ruri-bot/PROBLEM.md`.
No Jira key.

## Workflow
Delivery: local
Plans: docs/plans

## Commands
Run from `ruri-bot/prototype`:
- `.venv/bin/python -m pytest -q`
- `.venv/bin/python -m compileall -q -x '\.venv' .`

## Review constraints
- The model only reads documents; `policy.yaml` + plain code decide what is required. No approve/decline output.
- Synthetic data only until cloud processing of borrower data is approved (PROBLEM.md §8 Q5).
- Never store uploaded documents. Never log applicant names, IPs, document content, keys or connection strings.
- Caps and fail-closed checks on `/check` must run before any model call.

## High-stakes paths
- ruri-bot/prototype/app.py
- ruri-bot/prototype/db.py
- ruri-bot/prototype/db/**
- ruri-bot/prototype/migrate.py
- ruri-bot/prototype/vercel.json

## Hidden coupling
- `/check` form fields ↔ `static/index.html` `run()` ↔ `check_samples.py` ↔ `tests/`.
- `DOC_TYPES` in `app.py` ↔ `accepts:` lists in `policy.yaml` ↔ `samples/*.json` sidecars.
- `samples/expected.json` ↔ `generate_samples.py` (dates relative to generation day).
- Env var names: `app.py`, `db.py`, `migrate.py` ↔ `.env.example` ↔ README ↔ Vercel project env ↔ CI.
- `db/*.sql` columns ↔ SQL strings in `db.py`.
- Vercel bundle must include `static/`, `samples/`, `policy.yaml` (`vercel.json` `excludeFiles`).
```

## Do not
- Change code, tests or config. Put no secret values or real URLs in the docs (use `<domain>` placeholders).
- Touch files outside the `files` list. Create or switch branches, commit, or push.

## Done when
```bash
cd /Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments
grep -c '^## ' CLAUDE.md                                  # 6
grep -n -e 'DAILY_DOC_CAP' -e 'migrate.py' -e 'Rollback\|rollback' ruri-bot/prototype/README.md
cd ruri-bot/prototype && .venv/bin/python -m pytest -q
```
