---
type: prompt
plan: "[[2026-11-26-mvp-hardening]]"
id: 08
unit:
status: todo
model: sonnet
effort: medium
depends_on: [07]
parallel_group: H
files:
  create: []
  modify: []
  delete: []
---
# 08 · Go live via MCPs (interactive ops)

> **Run this in the main session, not as a subagent.** Every step creates or changes cloud resources, sets
> secrets or changes repo settings. Confirm each one with the user before running it. Never print secret
> values (API keys, connection strings, the salt).

## Task
Provision Neon and Vercel, wire GitHub, set the env vars, apply the migration and lock down spend. Then
smoke-test preview and production. Report the live URL and the evidence for each check.

## Context
- Repo: `/Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments`, GitHub
  `alessandrocruz5/amihan-inclusive-payments`, branch `main`. App dir / Vercel Root Directory:
  `ruri-bot/prototype`. `vercel.json` there sets `sin1` and `maxDuration` 120.
- Delivery is `local`: prompts 01–07 leave changes uncommitted. **The user commits and pushes** (or asks
  Claude to). Vercel deploys from GitHub, so nothing goes live until the code is on GitHub.
- MCPs: the **Vercel MCP** is connected in Claude (`mcp__claude_ai_Vercel__*`: `create_git_project`,
  `create_project_env`, `list_deployments`, `get_deployment`, `get_runtime_logs`, `request_rollback`,
  `web_fetch_vercel_url`). The **Neon MCP** is not connected yet. Offer
  `claude mcp add --transport http neon https://mcp.neon.tech/mcp` (OAuth in an interactive session), or
  install Neon through the Vercel Marketplace in the dashboard. The **GitHub MCP** is optional; `gh` is
  installed and authenticated.
- Env vars (names in `.env.example`):

| Var | Production | Preview |
|---|---|---|
| `ANTHROPIC_API_KEY` | set (user pastes it into Vercel; never through chat) | **not set** |
| `DEMO_OFFLINE` | unset | `1` |
| `IP_HASH_SALT` | random 32 bytes | random 32 bytes (different) |
| `DAILY_DOC_CAP` / `IP_HOURLY_DOC_CAP` | 300 / 36 (or the user's numbers) | unset |
| `DATABASE_URL`, `DATABASE_URL_UNPOOLED` | from the Neon integration | from the Neon integration (preview branches) |

### Steps (confirm each)
1. **Code on GitHub:** the user commits 01–07 on a branch and opens a PR (or pushes to `main` if they choose).
   Check that CI runs: `gh run list --workflow ci.yml --limit 1`.
2. **Neon:** create the project in **`aws-ap-southeast-1`**, through the Vercel Marketplace (Neon
   integration, connected to Production + Preview with preview branching) or the Neon MCP. Enable the
   integration's option to delete a preview branch when its Git branch is deleted (Neon free plans cap branches).
3. **Vercel project:** First confirm the plan tier with the user: Hobby is non-commercial only, and a client demo may need
   Pro (D17). Then `create_git_project` from the GitHub repo. Framework FastAPI, Root Directory
   `ruri-bot/prototype`. Connect the Neon resource if it wasn't done in step 2.
4. **Env vars:** set them per the table with `create_project_env`. Generate the salts locally
   (`python3 -c "import secrets;print(secrets.token_urlsafe(32))"`) and pass them straight to the tool without
   echoing them in chat. The user adds `ANTHROPIC_API_KEY` in the Vercel dashboard (Production only).
5. **Migration:** apply `db/001_checks.sql` to the Neon **main** branch. Either the user runs
   `DATABASE_URL_UNPOOLED=<from Neon> .venv/bin/python migrate.py` in a shell (the URL never enters chat), or
   use the Neon MCP `run_sql` with the file's contents and then
   `INSERT INTO schema_migrations(version) VALUES ('001_checks')` (create `schema_migrations` first, as `migrate.py` does).
   Preview branches created after this inherit the schema.
6. **Anthropic spend limit:** the user sets a monthly workspace spend limit in the Anthropic Console for the key's
   workspace (manual; there's no MCP).
7. **Branch protection:** `gh api -X PUT repos/alessandrocruz5/amihan-inclusive-payments/branches/main/protection`
   requiring status check `test`. Use the minimal JSON body:
   `required_status_checks{strict:false,contexts:["test"]}`, `enforce_admins:false`,
   `required_pull_request_reviews:null`, `restrictions:null`. The repo is **private**: on a free GitHub plan this returns 403/404.
   If it does, add the plan Log line "CI advisory, not enforced (D12)". Don't change repo visibility or the GitHub plan
   without the user.
8. **Smoke test the preview** (D13). Previews are behind Vercel Authentication, so use Vercel MCP
   `web_fetch_vercel_url` with **GET** only: `/status` → `mode: offline` and the six `samples` listed (proves
   `samples/` is bundled). `/` → 200 with the CSP header (proves `static/`). `/docs` → 404. Don't run
   `check_samples.py` against the preview; it can't pass the protection.
9. **Production:** after merge, `list_deployments` → READY. `/status` → `mode: live` with `policy_sha`.
   `check_samples.py <prod-url>` → PASS with `mode=live` (spends 6 documents). Check that one `checks` row exists
   (Neon MCP `SELECT status, doc_count, mode FROM checks ORDER BY created_at DESC LIMIT 1`; never select
   `applicant` into chat). `get_runtime_errors` shows none.
10. **Cap proof (cheap):** temporarily set Production `IP_HOURLY_DOC_CAP=1` and redeploy. A sample-set check
    → 429. Then restore and redeploy.

## Do not
- Print or paste any secret. Put the Anthropic key on Preview or Development.
- Change repo files, except that the user may ask you to commit 01–07.
- Create or switch branches yourself. The user does it, or explicitly asks you to.
- Retry a failed cloud write blindly. Check its state first.

## Done when
- The production URL serves the page. `check_samples.py <prod-url>` prints PASS in `mode=live`.
  `/docs` → 404. The CSP header is present.
- The preview reports `mode: offline` and lists the six samples (via `web_fetch_vercel_url`).
- `gh run list --workflow ci.yml --limit 1` → success. Branch protection requires `test` (or its refusal is reported).
- A `checks` row exists for the production smoke test. A cap of 1 gives 429.
- The Anthropic spend limit is confirmed by the user.
