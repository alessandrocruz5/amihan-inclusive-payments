# RuriBot: agri loan gap-list prototype

Upload a farmer's documents, get one list of what is missing or wrong, cited to the checklist.
The model only reads documents. `policy.yaml` and plain code decide what is required.

**Synthetic data only.** Whether borrower data may go to a cloud model is still an open question
(PROBLEM.md section 8). Clause IDs in `policy.yaml` are placeholders.

## Run

```bash
cd prototype
.venv/bin/python generate_samples.py          # (re)creates samples/ with relative dates

# Live: documents are read by Claude
export ANTHROPIC_API_KEY=...                   # your key
.venv/bin/uvicorn app:app --port 8000

# Offline demo: no key, answers come from samples/*.json sidecars (sample set only)
DEMO_OFFLINE=1 .venv/bin/uvicorn app:app --port 8000
```

Open http://127.0.0.1:8000 and press **Use the synthetic sample set**.

Check the result against the expected gaps (server running):

```bash
.venv/bin/python check_samples.py
```

`CASE_MODEL` overrides the reading model (default `claude-haiku-5-5`).

## Sample set

Applicant `Juan M. Dela Cruz`; six synthetic documents with these planted gaps:
expired driver's licence (problem), barangay clearance for a different person (problem),
no loan application form (missing), one unrelated photo (unmatched).

## Not in the prototype

Cash flow, wallet-statement analysis, cross-document checks, LOS data, auth, storage,
borrower messaging, resumable uploads, Filipino-language output.
