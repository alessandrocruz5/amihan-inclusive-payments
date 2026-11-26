# PROBLEM: Loan Case Agent for Rural Bank Agri Loans

Confidence tags: **[Certain]** is verified. **[Likely]** is probably true. **[Guessing]** is an assumption. **[To validate]** needs data from the Talino contact or the pilot bank.
Items marked **(interview)** were decided in the scoping interview.

## 1. Problem statement

Rural-bank loan officers build each loan file by hand. They collect paper documents, make a field visit, look records up across systems, guess a cash-flow figure, and compile the file for committee review. Missing items send the borrower back for another trip, and corrections send the file back to the officer. **[Likely]**

Each small loan therefore costs more staff time than it earns. Thin-file borrowers wait, get declined, or stay with informal cash services. **[Guessing]** *[To validate: hours per file and bounce-back rate.]*

Identity is no longer the main barrier. BSP allows simplified KYC for low-risk customers, and the national ID counts as sufficient proof of identity. **[Certain]** The remaining bottleneck is the back office. AI can now read messy documents, cross-check records, and chase gaps, which wasn't practical for thin-IT banks before. **[Likely]**

## 2. Scope of the first version (interview)

| Decision | Choice |
|---|---|
| First segment | **Farmers / agri loans** (seasonal income, harvest-linked repayment) |
| Agent's role | Prepares the file. It makes **no approve/decline recommendation**. |
| Delivery | **Web app: upload, then review.** It does not integrate with the bank's systems in v1. |
| Hardest constraint | **Thin IT / low connectivity** |

Out of scope for v1:
- Micro-enterprise and sari-sari loans. They are a later segment.
- Embedding in the bank's LOS.
- Offline field capture.
- Credit decisioning.
- Borrower-facing messaging.

## 3. Users

| User | Relationship to the problem | Needs from the agent |
|---|---|---|
| **Loan officer** (primary) | Builds the file today and does the rework. | A complete, cross-checked file. A clear list of what's missing. Less re-keying. |
| **Branch manager / credit committee** | Reviews files and sends corrections back. | Consistent file structure. Every claim traceable to a source. A cash-flow estimate based on data. |
| **Thin-file farmer-borrower** (indirect) | Carries documents back and forth and waits. | Fewer trips and a faster answer. They don't use the tool in v1. |
| **Compliance / internal audit** (secondary) | Must be able to examine any file afterwards. | An audit trail of what the agent read, inferred and cited. |

The human still approves, declines, or escalates every loan.

## 4. Inputs

All four input types are expected to be available in the pilot (interview).

1. **Photos and scans of documents.** National ID, business or farm permits, barangay clearance, and similar. They are captured on a phone or scanner, so quality is messy.
2. **GCash / e-wallet statements.** PDF or screenshot statements, plus exchanger and remittance receipts. This is the main evidence of cash flow for thin-file borrowers.
3. **The bank's core / LOS records.** Existing customer data, prior loans, and repayment history. **They arrive as exports or manual uploads, not an API.**
4. **Officer's field-visit notes.** Free text, photos of the farm, and the officer's own estimates.

Assumptions about the inputs:
- Documents vary in format and quality. **[Likely]**
- Agri-specific evidence is likely to include farm size, crop type, harvest cycle, and buyer or cooperative records. **[Guessing]** *[To validate: which documents the pilot bank requires for agri loans.]*
- The bank's written lending policy is also an input, because the agent must cite it. *[To validate: its format and whether it is machine-readable.]*

## 5. Outputs

A **complete case file** for the loan officer, produced before committee review. It contains:

1. **Extracted and normalised data.** Identity, farm and business details, and loan request, with no re-keying.
2. **Cross-check results.** Mismatches across documents, wallet statements, bank records and field notes are flagged. Examples are name, address, amount and date discrepancies.
3. **A cash-flow estimate based on data.** It is built from wallet and bank evidence, adjusted for the seasonal agri cycle, and shows its assumptions and confidence. It replaces the guessed estimate.
4. **A gap list.** Everything missing or unreadable, so the officer can ask for it in **one** borrower contact instead of several.
5. **Policy citations.** Each requirement is checked against the bank's policy and cites the specific clause.
6. **Source traceability.** Every figure or claim in the file links back to the source document or record.

The agent gives **no decision and no suggested decision.** The officer decides alone. This keeps explainability and fair-lending exposure lowest in v1.

## 6. Constraints

**Primary: thin IT and low connectivity.**
- Web app with upload and review. Banks supply exports and files, not integrations.
- No dependency on the bank's APIs, on-prem infrastructure, or heavy IT support.
- It must tolerate weak or intermittent connections. Uploads must be resumable, and pages light.
- Setup and onboarding must be minimal. This is a branch-level tool for non-technical staff.

**Regulatory and risk. [Likely]**
- Data Privacy Act obligations apply. Borrower data is sensitive personal information.
- BSP rules on outsourcing, and on the use of AI in credit processes, may apply. *[To validate with the bank's compliance team.]*
- The simplified-KYC and national-ID provisions are the basis for the identity step. **[Certain]**
- Every agent output must be auditable: sourced, cited, and reproducible.
- **Human-in-the-loop is mandatory.** The agent never decides.

**Economics. [Guessing]**
- The per-file cost of the agent must stay well below the staff time it saves on a small loan. *[To validate: loan sizes and staff cost per hour.]*

## 7. Success measures

Targets are not set yet. *[To validate: set them once the Talino contact provides baselines.]*

- **Fewer bounce-backs.** Rework loops per file, both borrower return trips and corrections sent back to the officer.
- **Fewer hours per file.** Officer and manager time from intake to committee-ready.
- **More thin-file borrowers served.** More farmers reach a decision, and fewer decline or drop out.

## 8. Open questions

1. Which pilot bank, and who is the Talino contact? Baselines depend on them.
2. What are the baseline hours per file and bounce-back rate?
3. Which documents does the bank require for agri loans, and what is the typical loan size?
4. What format are the bank's policy documents and core/LOS exports in?
5. Can borrower data be processed by a cloud-hosted model? What do the bank's compliance and BSP outsourcing rules say?
6. What languages do the documents and notes use (Filipino, regional languages, English)?
7. How is wallet evidence legitimately obtained? The borrower must consent to share their statements.
8. What does the committee need in the file beyond the six outputs above?
