---
type: prompt
plan: "[[2026-11-26-mvp-hardening]]"
id: 06
unit:
status: todo
model: sonnet
effort: medium
depends_on: [05]
parallel_group: F
files:
  create:
    - ruri-bot/prototype/vercel.json
    - .github/workflows/ci.yml
    - ruri-bot/prototype/.env.example
  modify: []
  delete: []
---
# 06 · Vercel config + GitHub CI

## Task
Add the Vercel project config for the FastAPI app, a GitHub Actions workflow that gates PRs and `main`, and an
`.env.example` listing every env var by name.

## Context
- Repo root: `/Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments`. GitHub remote:
  `alessandrocruz5/amihan-inclusive-payments`, default branch `main`.
- The Vercel project's **Root Directory** will be `ruri-bot/prototype` (set in prompt 08). Vercel's
  FastAPI preset auto-detects `app.py` → `app`. The Python version comes from `.python-version` (`3.12`). Deps
  come from `requirements.txt`. `vercel.json` `functions` keys are relative to the root directory, so the key
  is `app.py`.
- `/` serves `static/index.html` from the function, and the sample button reads `samples/*.png` at runtime.
  Both directories **must stay in the function bundle**.
- Locked decisions: region `sin1` (Singapore, next to Neon `aws-ap-southeast-1`). Time budget: Anthropic
  25 s × 2 attempts, 6 parallel workers, so `maxDuration` 120.
- Test commands (D4): `python -m pytest -q` and `python -m compileall -q -x '\.venv' .`, run from
  `ruri-bot/prototype`. DB tests run when `TEST_DATABASE_URL` is set and skip otherwise. `migrate.py`
  reads `DATABASE_URL_UNPOOLED` or `DATABASE_URL`.
- Env vars used by the code: `ANTHROPIC_API_KEY`, `CASE_MODEL`, `DEMO_OFFLINE`, `DATABASE_URL`,
  `DATABASE_URL_UNPOOLED`, `IP_HASH_SALT`, `DAILY_DOC_CAP`, `IP_HOURLY_DOC_CAP`, plus the platform-set
  `VERCEL_ENV`. Confirm the list with
  `grep -hoE "environ(\.get)?[\[(]\"[A-Z_]+\"" app.py db.py migrate.py | sort -u` and include every hit.

### `ruri-bot/prototype/vercel.json`
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "regions": ["sin1"],
  "functions": {
    "app.py": { "maxDuration": 120, "excludeFiles": "{tests/**,.pytest_cache/**}" }
  }
}
```
Don't exclude `static/**`, `samples/**`, `policy.yaml` or `db/**`.

### `.github/workflows/ci.yml`
- `on: pull_request` and `push: branches: [main]`. `permissions: contents: read`. One job `test` on `ubuntu-latest`.
- `services.postgres`: image `postgres:16`, env `POSTGRES_PASSWORD: postgres`, ports `5432:5432`, health
  options (`--health-cmd pg_isready --health-interval 5s --health-timeout 5s --health-retries 10`).
- `defaults.run.working-directory: ruri-bot/prototype`.
- Steps:
  - `actions/checkout@v4`.
  - `actions/setup-python@v5` with `python-version-file: ruri-bot/prototype/.python-version`,
    `cache: pip`, `cache-dependency-path: ruri-bot/prototype/requirements*.txt`.
  - `pip install -r requirements-dev.txt`.
  - `python migrate.py` with env `DATABASE_URL: postgresql://postgres:postgres@localhost:5432/postgres`.
  - `python -m pytest -q` with env `TEST_DATABASE_URL` set to the same URL.
  - `python -m compileall -q -x '\.venv' .`.
- No secrets are needed. Tests never call the real Anthropic API.

### `ruri-bot/prototype/.env.example`
One line per variable, `NAME=` with **no values**, and a short `#` comment above each. Mark which are set by the
Neon integration (`DATABASE_URL`, `DATABASE_URL_UNPOOLED`) and by Vercel (`VERCEL_ENV`). Note that
`ANTHROPIC_API_KEY` is **Production only** and previews use `DEMO_OFFLINE=1`. Show the defaults
`DAILY_DOC_CAP` 300 and `IP_HOURLY_DOC_CAP` 36 in comments only. `IP_HASH_SALT`: a random 32+ byte string,
required on Vercel in live mode.

## Do not
- Put any secret value anywhere. Don't add a deploy workflow (Vercel's Git integration deploys).
- Touch app code or files outside the `files` list.
- Create or switch branches, commit, or push.

## Done when
```bash
cd /Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments/ruri-bot/prototype
.venv/bin/python -c "import json;json.load(open('vercel.json'))"
.venv/bin/python -c "import yaml;d=yaml.safe_load(open('../../.github/workflows/ci.yml'));assert 'test' in d['jobs']"
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q -x '\.venv' .
grep -vE '^\s*(#|$)' .env.example | grep -E '=.+' && echo "FAIL: value present" || echo "ok: no values"
```
- The first PR run in prompt 08 is the CI proof.
