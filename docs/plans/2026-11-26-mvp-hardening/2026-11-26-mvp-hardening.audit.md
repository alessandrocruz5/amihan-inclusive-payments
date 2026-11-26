# Audit log · 2026-11-26-mvp-hardening

## Audit 2026-11-26: PASS-WITH-CHANGES
Auditor: Claude `/audit-plan` (Opus 5.5), **same session as the planner**. That's a bias risk, so a Codex second opinion is still recommended.
Graph built: none (no `graphify-out/`; the repo is ~600 LOC, so grep was used) · Symbols traversed: 9 (`/check`, `clean`, `read_live`, `read_one`, `evaluate`, `names_match`, `parse_date`, `MAX_BYTES`, `index.html run()`) · Missed blast-radius items: 4

The independent grep confirms the planner's main coupling:
- `/check` form fields: `app.py:237`, `check_samples.py:17-18`, `static/index.html:119-120`.
- Env keys: `app.py:32,59,61` only.
- `MAX_BYTES` is used only at `app.py:34,254-255`.
- `date.today()` is called at `app.py:269` (also `generate_samples.py:19`, which is unaffected).

The non-str crash path is real: `names_match`/`parse_date` are reached through `evaluate` (`app.py:173,176,180`), outside the per-file `try` (`app.py:139`).

| Sev | Check | Finding | Evidence | Fix |
|---|---|---|---|---|
| FIX | Breakage (ops) | The plan assumes the GitHub repo is **public**. It is **private**. Branch protection and rulesets on a private repo need a paid GitHub plan, so prompt 08 step 7 and the E2E `gh api …/protection` line will likely fail. | `gh repo view … --json visibility` → `PRIVATE main` | Correct the assumption. In 08 step 7 and the E2E line, make branch protection conditional ("if the plan allows; otherwise record it as a known gap: CI is advisory, enforced by habit"). Add a Decisions line. Don't flip visibility without the user. |
| FIX | Usability | The preview smoke test can't work as written. New Vercel projects protect preview deployments (Vercel Authentication) by default, so `check_samples.py <preview-url>` and `curl <preview>/status` get 401/redirect, and `check_samples.py` can't send a bypass header. | Vercel docs: "MCP server accessing a protected deployment" and `x-vercel-protection-bypass`. `check_samples.py:19-20` sends no custom headers. | 08 step 8: smoke-test previews with Vercel MCP `web_fetch_vercel_url` (it handles protection), using **GET** only. `/status` lists `samples` (proves `samples/` is bundled, `app.py:233`). `/` returns 200 + CSP (proves `static/`). `/docs` → 404. Run the POST `check_samples.py` against **production** only. Fix the matching E2E line. |
| FIX | Notes & constraints (DPA) | The data notice in 04 says documents "are not stored". They aren't stored **by this app**, but they are sent to and processed by Anthropic under its API data terms. A notice that overstates what happens to personal data is a DPA transparency risk (PROBLEM.md §6: "Data Privacy Act obligations apply"). | `prompts/mvp-hardening-04-ui-hardening.md` change 1 text. The same claim is in 07's README facts. | Reword in 04 and 07: "Documents are sent to Anthropic's Claude API to be read. This app does not store them. Anthropic processes them under its API data terms. The applicant name and the extracted results are kept by this app for 30 days for audit. Don't upload real borrower documents." |
| FIX | Usability | 07's Done-when expects `grep -c '^## ' CLAUDE.md` = **7**, but the specified template has **6** `##` headings (Project, Workflow, Commands, Review constraints, High-stakes paths, Hidden coupling). The prompt would fail its own check. | `prompts/mvp-hardening-07-docs-profile.md` template vs the Done-when block | Change it to `# 6`. |
| FIX | Prompt independence | 05 is underspecified for **offline mode on Vercel with no `IP_HASH_SALT`** (preview). It only defines salt `""` "off Vercel" and 503 for live. The executor has to invent a branch, and an unsalted IPv4 hash can be brute-forced back to the IP. | `prompts/mvp-hardening-05-caps-and-audit.md` §Client identity and D6 bullets | Add: "On Vercel with no `IP_HASH_SALT`: live → 503 (as D6). Offline → skip the audit row entirely (`check_id` None) and log a warning. Never hash with an empty salt on Vercel." Add a test. |
| NOTE | Breakage (missed) | `static/index.html:93` `fetch('/status').then(r => r.json())` has no error path. A 500 or non-JSON `/status` (cold-start DB error, protection page) leaves the banner hidden and the sample button state unknown, silently. | `static/index.html:93-99` | Fold into 04 change 4: guard the `/status` fetch with the same text→JSON parse, and on failure show a neutral banner. |
| NOTE | Breakage (missed) | Security headers from an `@app.middleware("http")` won't be on the 500 responses produced by the `Exception` handler. Starlette's `ServerErrorMiddleware` is outermost and re-raises after responding. | `.venv/.../starlette/middleware/errors.py:127,186` | Accept it (a JSON error body has low exposure), or set the headers inside the 500 handler too. One line in 02. |
| NOTE | Optimization | psycopg 3 server-side prepares a statement after 5 executions. Through Neon's PgBouncer (transaction mode) that is supported now, but it's a classic footgun. Per-request connections make it unlikely to trigger. | `prompts/mvp-hardening-03-neon-data-layer.md` `connect()` | Add `prepare_threshold=None` to `psycopg.connect(...)` in 03. It's free insurance. |
| NOTE | Notes & constraints | PROBLEM.md §6 wants outputs "reproducible". D3 stores model id + `policy_sha` + `prompt_sha` + extraction, but not the files. Exact re-runs are impossible, by the user's choice. | PROBLEM.md §6; plan D3 | Record it as an accepted trade-off in Decisions (no change). |
| NOTE | Business | Vercel **Hobby** is for non-commercial use. A Talino Fintech Foundry client demo may count as commercial, which means Vercel Pro (it also unlocks preview password protection and more). | Plan doesn't name a plan tier; D9 relies on Hobby facts | Decide the tier before go-live (08 step 3). |
| NOTE | Ops | Neon free plans cap branches. The integration's branch-per-preview can exhaust them. | Plan D-list / 08 step 2 | In 08, enable the integration's "delete branch when the Git branch is deleted" option, or turn preview branching off and give previews a separate small DB. |
| NOTE | Usability | 04's Done-when `F="$(mktemp -t uicheck).js"` makes an empty temp file and writes to a different `.js` path, leaving a stray file. | `prompts/mvp-hardening-04-ui-hardening.md` Done when | Use `F=$(mktemp -t uicheck-XXXXXX.js)` or the scratch dir. |
| NOTE | Usability | 02's `today_ph()` test leaves the freezing technique to the executor ("module-level clock or `app.datetime`"). | `prompts/mvp-hardening-02-app-hardening.md` Tests | Specify `def today_ph(now: datetime \| None = None)` so the test passes a fixed UTC datetime. |

**Assumptions checked:**
- Hobby allows any **single** region, so `sin1` is OK. *(Vercel docs: "Hobby plans can select any single region".)*
- Vercel overwrites `x-forwarded-for`, and `x-real-ip` is identical, so neither can be spoofed on Vercel. *(Vercel docs, request headers.)*
- Not re-verified from the docs index:
  - the 4.5 MB body limit (widely documented; the 4 MB cap is conservative, and the UI handles a non-JSON 413 anyway)
  - the Neon integration's variable names (`migrate.py` falls back to `DATABASE_URL`, so a wrong name for the unpooled URL is harmless)
  - Hobby `maxDuration` 120 (verify in 08 with `get_deployment` / the function config)

**Requirements coverage:** R1 → 01, 02, 04 · R2 → 06, 08 · R3 → 03, 05 · R4 → 06, 08 · R5 → 07, 08 · R6 → 04, 05. All are verified by E2E lines (after the preview/branch-protection fixes above).

**Unit shape:** n/a (`local` delivery).

**Bloat estimate:** planned ~17 files / ~850 LOC (about 350 of that is tests). Minimal viable ~11 files / ~450 LOC (without the CLAUDE.md profile, the hardening test file and the concurrency test). The extras trace to D4 (Commands), workflow §1 (profile) and D7 (exact caps), so this is proportionate. No new dependency other than `psycopg[binary]` (needed for R3) and the pytest/httpx dev deps (D4).

**Model cost:** fit is right. 05 on opus is justified (cost and abuse gate plus fail-closed on a public endpoint). 07 on haiku is OK (docs only, verbatim template). 03 on sonnet is acceptable because the lock and cap SQL are fully specified. No downgrades recommended.

Status: applied 2026-11-26: 12 applied (5 FIX + 7 NOTE), 0 disputed; D16 recorded as a decision
