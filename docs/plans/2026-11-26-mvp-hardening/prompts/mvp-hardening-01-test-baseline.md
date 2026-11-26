---
type: prompt
plan: "[[2026-11-26-mvp-hardening]]"
id: 01
unit:
status: todo
model: sonnet
effort: medium
depends_on: []
parallel_group: A
files:
  create:
    - .gitignore
    - sandro-proposal/prototype/.python-version
    - sandro-proposal/prototype/requirements-dev.txt
    - sandro-proposal/prototype/tests/conftest.py
    - sandro-proposal/prototype/tests/test_app.py
  modify:
    - sandro-proposal/prototype/requirements.txt
  delete:
    - sandro-proposal/prototype/__pycache__/app.cpython-315.pyc   # untrack only (git rm --cached)
    - sandro-proposal/.DS_Store                                    # untrack only (git rm --cached)
---
# 01 · Test baseline, pinning, repo hygiene

## Task
Give the prototype a reproducible Python 3.12 environment, pinned dependencies, git hygiene and an offline
pytest suite that pins **today's** behaviour. Don't change `app.py`. Later prompts harden the app against
this baseline.

## Context
- Repo root: `/Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments` (git, branch `main`).
  App dir (`P/`): `sandro-proposal/prototype/`. All commands below run from `P/` unless stated.
- The app is a FastAPI module `app.py` with `app = FastAPI(...)` at module level. Endpoints: `GET /`,
  `GET /status`, `POST /check` (multipart form: `applicant`, `use_samples`, `files`). `mode()` reads env **at
  call time**: `ANTHROPIC_API_KEY` set → `live`; `DEMO_OFFLINE=1` → `offline`; else `none` (`/check` → 503).
- Offline mode reads `samples/<stem>.json` sidecars. `samples/expected.json` holds the expected statuses for
  applicant `"Juan M. Dela Cruz"`. `check_samples.py:23-26` shows the comparison: per-id `status` and a
  sorted `unrecognised` list.
- The current `.venv` is Python 3.15 and is **not** tracked (it has its own `.gitignore`). Vercel and CI will
  use 3.12.
- The repo has no `.gitignore`. Tracked junk: `sandro-proposal/prototype/__pycache__/app.cpython-315.pyc`,
  `sandro-proposal/.DS_Store`.

### Steps
1. **`.gitignore`** at the repo root:
   `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.DS_Store`, `.env`, `.env.*`, `!.env.example`, `.vercel/`.
   Then `git rm --cached sandro-proposal/prototype/__pycache__/app.cpython-315.pyc sandro-proposal/.DS_Store`
   (this untracks the files and leaves them on disk; don't commit).
2. **`P/.python-version`** containing exactly `3.12`.
3. **Rebuild the venv on 3.12:** `rm -rf .venv && uv venv --python 3.12 .venv`.
4. **`P/requirements-dev.txt`:** `-r requirements.txt`, then `pytest`, plus whatever
   `fastapi.testclient.TestClient` needs (install, then run
   `.venv/bin/python -c "from fastapi.testclient import TestClient"` and add the package it asks for, normally `httpx`).
5. Install: `uv pip install --python .venv/bin/python -r requirements-dev.txt`.
6. **Pin `P/requirements.txt`.** Keep the same six packages in the same order (`fastapi`, `uvicorn`,
   `anthropic`, `pyyaml`, `python-multipart`, `pillow`), each pinned `==` to the version now installed in the
   3.12 venv (`uv pip freeze --python .venv/bin/python`). Add no other runtime packages. Pin the dev packages
   in `requirements-dev.txt` the same way.
7. **`P/tests/conftest.py`:**
   - Insert `P/` into `sys.path` so `import app` works.
   - An autouse fixture that uses `monkeypatch` to delete `ANTHROPIC_API_KEY`, `DEMO_OFFLINE`, `VERCEL_ENV`,
     `DATABASE_URL` and `IP_HASH_SALT`, so no test ever hits a real API or database.
   - A fixture `client` that yields `TestClient(app.app)`.
   - A fixture `offline` that sets `DEMO_OFFLINE=1`.
8. **`P/tests/test_app.py`:**
   - `test_sample_set_offline`: with `offline`, POST `/check` with `applicant=expected["applicant"]`,
     `use_samples=1`. Assert 200, every `items[].status` equals `expected["status"][id]`, and sorted
     `unrecognised` equals sorted `expected["unrecognised"]`.
   - `test_blank_applicant_400`, `test_no_files_400` (offline, no files, no `use_samples`), and
     `test_mode_none_503` (no env).
   - `test_unsupported_file_flagged`: offline, upload `("files", ("note.txt", b"hello", "text/plain"))`.
     Expect 200 and `documents["note.txt"]["legible"] is False`, with `"unsupported file type"` in its
     `legibility_note`.
   - `test_status_offline`: `/status` → `mode == "offline"`, and `samples` lists the six `.png` files.
   - `test_names_match` parametrized over `app.names_match(applicant, on_doc)`:
     (`"Juan M. Dela Cruz"`, `"DELA CRUZ, JUAN M."`) True; (`"Juan M. Dela Cruz"`, `"Juan Dela Cruz"`) True;
     (`"José Rizal"`, `"Jose Rizal"`) True; (`"Juan M. Dela Cruz"`, `"Jose M. Dela Cruz"`) False;
     (`"Juan Dela Cruz"`, `None`) False.

## Do not
- Touch files outside the `files` list. In particular, don't edit `app.py`, `check_samples.py` or `samples/`.
- Add runtime dependencies or upgrade beyond what `uv` resolves today.
- Create or switch branches, commit, or push.

## Done when
```bash
cd /Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments/sandro-proposal/prototype
.venv/bin/python --version                        # Python 3.12.x
.venv/bin/python -m pytest -q                     # all pass
.venv/bin/python -m compileall -q -x '\.venv' .
git -C ../.. status --porcelain | grep -E '^D '   # the two untracked files show as staged deletions
grep -c '==' requirements.txt                     # 6
```
- `DEMO_OFFLINE=1 .venv/bin/uvicorn app:app --port 8000` + `.venv/bin/python check_samples.py` still prints PASS.
