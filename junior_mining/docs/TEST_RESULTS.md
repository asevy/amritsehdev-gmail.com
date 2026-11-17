# Test results — 2026-11-17

Environment: Python 3.13.18, SQLite 3.53.1, pdfplumber 0.11.10, openpyxl 3.1.5,
reportlab 5.0.1, pytest 9.2.0. Command: `python -m pytest` in `junior_mining/`.

**Result: 144 passed, 0 failed, 0 skipped (≈32 s)** — 116 for the core product plus 28 for the Claude integration (`test_claude_integration.py` 15, `test_mcp_connector.py` 9, `test_claude_http.py` 4; no live Anthropic API call — a fake client records each request). All tests use the
synthetic fixtures; each test runs on its own copy of a seeded two-tenant
workspace. Tests assert behaviour on raw payloads (store results, JSON, HTTP
status codes, export bytes), not only on rendered pages.

## Brief §17 required cases

| # | Required case | File | Tests | What is asserted |
|---|---|---|---|---|
| 1 | Correct number, wrong entity/period/currency/scale/scope rejected or flagged | `test_01_identity_period_currency_scale_scope.py` | 10 | crafted model-style claims against real page text: wrong period, currency, scale, value-for-scale, basis → rejected; similarly named project of another company → rejected; expiry-as-as-at → flagged; missing basis/date → needs review |
| 2 | Valid citation not supporting the full claim cannot approve it | `test_02_claim_support.py` | 9 | wrong date, "issued" vs accepted-for-review, reserves vs resources, NPV without tax basis/discount rate, unattributed issuer statement, wrong number, unapproved citation; reviewer approval refused; claim withheld from body |
| 3 | Missing input stays unknown | `test_03_missing_inputs.py` | 8 | undisclosed debt withholds EV; stated "no debt" = 0 with quote; runway withheld without spend; unapproved inputs withhold; absent category not assumed zero; stated nil allows derivation; not-found answer with coverage; OCR value stays unknown |
| 4 | Inferred ≠ reserves; intercept ≠ true width | `test_04_categories_and_true_width.py` | 6 | Inferred row in reserve table rejected; model "inferred reserve" rejected; EV/oz never adds Inferred; intercepts stored as down-hole length with true-width status; model true width rejected; historical estimate separate |
| 5 | Application ≠ issuance | `test_05_permit_status.py` | 7 | applied and accepted-for-review are distinct dated states; forward-looking sentence → commitment; "has not submitted" → not applied; model "issued" rejected; ROD issued recognised; answers and memo claims respect status |
| 6 | Revisions preserve originals and affect only appropriate facts | `test_06_revisions.py` | 6 | restatement supersedes exactly the 4 restated facts; grades/Measured/Inferred untouched; new effective date supersedes nothing; bytes/hash immutable; duplicate upload deduped; new version keeps old and conflicts are preserved; correction is a new revision |
| 7 | NPV ≠ equity value without a bridge | `test_07_npv_not_equity.py` | 6 | attributable NPV caveated; equity bridge withheld until every component specified; unstated NPV basis not bridged; "company is worth NPV" claim rejected; market cap not EV |
| 8 | Peer mismatch exposed; unsupported comparisons withheld | `test_08_peer_mismatch.py` | 7 | candidate reasons/differences; rationale required; study-type, price-assumption and reporting-basis differences exposed; withheld cells with reasons; one market-data date enforced; no winner; alphabetical default; exclusions listed |
| 9 | Disclosed risks and contrary evidence not omitted | `test_09_memo_risks_complete.py` | 5 | rule risks in draft; risk items not removable; new register risk blocks approval; contrary evidence rendered; counter-thesis required |
| 10 | Calculation lineage reproducible, units and rounding | `test_10_calculation_lineage.py` | 7 | every computed result reproduces exactly (≥20); values/units/display rounding; FX rate, source and date recorded; FX without source refused; inputs linked and approved; dilution proceeds hypothetical; runway from cash date |
| 11 | Corrections invalidate dependents | `test_11_invalidation.py` | 5 | correction → calcs and approved memo stale, memo content and hash unchanged, events link outputs; stale approved memo renders unchanged with change notes; rejection invalidates; restatement → snapshot and thesis assumption; commitment revision → thesis |
| 12 | Stale/failed feeds show incomplete coverage | `test_12_stale_and_failed_feeds.py` | 6 | failed run visible, retry increments attempts, feed failed; unreadable pages → incomplete; old disclosure → stale; market data stale with time; outputs carry time, cutoff, gaps; connectors not configured |
| 13 | Prompt injection cannot alter permissions/behaviour | `test_13_prompt_injection.py` | 4 | injected text stored as data, nothing auto-approved, roles unchanged; answers ignore it; obedient fake model's extra keys/unknown metrics/invented quotes discarded and remaining candidates validated; upload form fields cannot set state or role |
| 14 | No cross-tenant retrieval (URLs, search, exports, caches, jobs) | `test_14_tenant_isolation.py` | 6 | 15 direct URLs → 404 with no content; same-name company separate; search scoped both ways; actions on other tenant's records → 404; background job and blob read confined; image cache keyed by tenant |
| 15 | Review/export permissions and approval versioning | `test_15_permissions_versioning.py` | 9 | read-only cannot write/review/export; analyst cannot approve; separation of duties; approved version immutable, versions increment, prior approval superseded with hash intact; CSRF enforced; export hash recorded in audit, draft marked; admin audit only; lockout; audit tamper detected |
| 16 | No investment scores or substitutes | `test_16_no_scores.py` | 6 | scanner sanity; schema fields; 8 API payloads; 13 pages (no badges/traffic lights); JSON/CSV exports; refusal of score/rating/probability/price-target/honesty questions |

Additional: `test_units_quantities.py` (6 — parsing, OCR, intervals, rounding,
dates across line breaks, target windows), `test_bench.py` (3).

## Defects found by tests and checks during development (all fixed)
- Precision interval centred on the unscaled number (412 ± 500 000) hid the 412 vs 432 NPV conflict.
- Dates split across PDF lines were not parsed; an expiry date was taken as an as-at date.
- "May 20" read as the modal "may", dropping a permit status.
- "has not yet submitted an application" classified as "applied".
- A model candidate escaped the wrong-entity check because sentence bounds came from the extractor; the validator now re-derives the sentence itself.
- A fabricated as-at date was flagged instead of rejected.
- `/api/coverage/<id>` returned 200 (empty) for another tenant's company instead of 404; all company-scoped entry points now verify the company first.
- An approved memo rendered its own claims as "withheld" after evidence changed; approved versions now render unchanged with "since approval" notes.
- "unrestricted cash" matched the restricted-cash intent (found by the benchmark run).

## Benchmark tooling run (synthetic development labels — NOT validation)
`python -m jmi.bench benchmark/dev_synthetic_questions.jsonl`, 26 questions:

| Measure | Result | 95% Wilson |
|---|---|---|
| Value-and-context accuracy | 14 / 14 | 0.785 – 1.0 |
| Answerable coverage | 17 / 17 | 0.816 – 1.0 |
| Appropriate abstention | 9 / 9 | 0.701 – 1.0 |
| False answer on unanswerable | 0 / 9 | 0.0 – 0.299 |
| Latency (deterministic, in-process) | p50 0.64 ms, p95 1.25 ms | — |

These numbers show the tooling works on fixtures written by the developer who
wrote the rules. They say nothing about accuracy on real disclosures.
Production validation is pending expert labels (benchmark/PROPOSAL.md).

## End-to-end demonstration
`python scripts/demo.py` — 28 checks over real HTTP, all passing; transcript in
[DEMO_TRANSCRIPT.md](DEMO_TRANSCRIPT.md). Screens captured in `docs/screenshots/`.

## Not tested here
Real issuer documents; OCR; live connectors; a live Anthropic API call (the Claude features are tested with a fake client only); concurrent
multi-user load; TLS deployment; penetration testing; browser accessibility
audit beyond semantic HTML.
