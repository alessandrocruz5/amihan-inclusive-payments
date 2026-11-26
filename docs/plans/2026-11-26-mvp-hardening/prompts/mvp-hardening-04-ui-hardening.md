---
type: prompt
plan: "[[2026-11-26-mvp-hardening]]"
id: 04
unit:
status: todo
model: sonnet
effort: medium
depends_on: [02]
parallel_group: D
files:
  create: []
  modify:
    - ruri-bot/prototype/static/index.html
    - ruri-bot/prototype/tests/test_hardening.py
  delete: []
---
# 04 · UI hardening

## Task
Update the single page so it works on a public serverless URL over weak connections:
- a required synthetic-data acknowledgement and a data notice
- client-side image downscaling and a total-size precheck
- readable messages for non-JSON errors and HTTP 413/429/503/504
- a reference id when the server returns one

This runs **before** the server enforces the acknowledgement (prompt 05), so it must work against both
server versions. The current server ignores an extra `synthetic_ack` field.

## Context
- Repo root: `/Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments`. File:
  `ruri-bot/prototype/static/index.html`. It's plain HTML with inline `<style>` and `<script>`, no build
  step and no libraries. Keep it that way: pages must stay light (thin IT / low connectivity).
- CSP from prompt 02: `script-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'`.
  No external scripts, fonts or CDNs.
- Landmarks: the intake section `:52-64`, the `/status` banner fetch `:93-99`, `addFiles` `:105`, `run()`
  `:113-129` (builds `FormData` with `applicant`, `use_samples` or `files`), the sample button `:131`,
  `render(j)` `:136-162`. All text goes through `textContent`; keep that, never `innerHTML` with data.
- Server facts: the total upload cap is **4,000,000 bytes** (413 above it). The server downscales images to a
  1568 px long side anyway, so the client doing the same loses no reading quality. After prompt 05,
  `/check` will require form field `synthetic_ack=1` and may return 429 (cap reached; JSON `detail`), 503
  (`detail`) and a `check_id` key. Vercel itself may answer 413/504 with **non-JSON** bodies.

### Changes
1. **Acknowledgement + notice** in the intake card, above the buttons. Add a checkbox `id="ack"` with the label
   "These are synthetic test documents, not real borrower data." Below it, a `.note` paragraph:
   "Documents are sent to Anthropic's Claude API to be read. This app does not store them; Anthropic
   processes them under its API data terms. The applicant name and the extracted results are kept by this app
   for 30 days for audit. Do not upload real borrower documents."
   `run()` refuses to send without `ack` checked (show in `$('err')` "Tick the box to confirm these are
   synthetic test documents."). It always appends `synthetic_ack=1` when checked. The sample button counts too:
   it ticks `ack` and then runs.
2. **Client-side downscale** in a new `async function shrink(file)`. For `image/*` (except `image/gif`), use
   `createImageBitmap(file)`. If the long side is over 1568 or `file.size` is over 600 KB, draw it to a canvas
   with the long side at most 1568 and export `toBlob('image/jpeg', 0.85)`. Return
   `new File([blob], <original base name + ".jpg">, {type: 'image/jpeg'})`. Otherwise, or on any error, return
   the original file. PDFs pass through untouched. Run `shrink` on each picked file in `run()` just before
   building `FormData`. Show "Preparing photos…" on the button meanwhile.
3. **Size precheck:** after shrinking, if the total size is over 4,000,000 bytes, show "These files total X MB
   after shrinking photos. The limit is 4 MB. Split large PDFs into a separate check." and don't send.
4. **Robust response handling:** read `await r.text()`, then try `JSON.parse`. On failure, map the status:
   413 → "Upload too large for one check (4 MB).", 429 → "Usage limit reached. Try again later.",
   504 → "The check took too long. Try fewer files.", otherwise "Server error (HTTP <status>). Try again."
   When the JSON has `detail`, show it.
5. **Guard the `/status` fetch** (`:93-99`, today an unguarded `r.json()`). Use the same text → `JSON.parse`
   handling as change 4. On failure, show a neutral banner "Status unavailable. Checks may still work." and keep
   the sample button visible.
6. **Reference id:** in `render(j)`, if `j.check_id` exists, show `Reference: <check_id>` in a `.note` under the
   summary (new element `id="ref"`, hidden when absent).

### Test (append to `P/tests/test_hardening.py`)
- `GET /` → 200, and the body contains `id="ack"` and `synthetic_ack`.

## Do not
- Add external assets, frameworks or a build step. Don't use `innerHTML` with server or user data.
- Touch files outside the `files` list.
- Create or switch branches, commit, or push.

## Done when
```bash
cd /Users/alessandrocruz/Code/talino-fintech-foundry/amihan-inclusive-payments/ruri-bot/prototype
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q -x '\.venv' .
F="${TMPDIR:-/tmp}/uicheck-$$.js"; .venv/bin/python -c "import re;h=open('static/index.html').read();print(re.search(r'<script>(.*)</script>',h,re.S).group(1))" > "$F" && node --check "$F"; rm -f "$F"
```
- Manual check, offline server (`DEMO_OFFLINE=1 .venv/bin/uvicorn app:app --port 8000`): the sample button
  renders the gap list. With `ack` unticked, "Check file" shows the confirm message. A 5 MB phone JPEG is sent
  as a file under 600 KB (DevTools → Network).
