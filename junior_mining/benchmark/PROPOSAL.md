# Expert-review benchmark — proposal (initial scope hypothesis)

Status: **tooling implemented (`jmi/bench.py`); expert labels not available;
production validation pending.** The 26-question set in
`dev_synthetic_questions.jsonl` is developer-written against synthetic
fixtures and tests the tooling only. It is not ground truth.

## Scope (hypothesis, not a sufficiency claim)
About **30 companies and 500 questions**, stratified:

| Stratum | Levels (target companies) |
|---|---|
| Stage | exploration 6 · resource 6 · PEA 6 · PFS/FS 6 · construction/operating 6 |
| Document quality | clean digital PDF · complex tables/footnotes · scanned/OCR · spreadsheet appendices · press-release only |
| Jurisdiction / regime | NI 43-101 · S-K 1300 · JORC (definitions reviewed separately) |
| Failure type (questions) | entity/period/unit/scale/currency/scope · category (M/I/Inf, P/P, historical) · true width · permit status · restatement/supersession · peer incompatibility · unanswerable/absence · out-of-policy |

Question mix (≈500): value-and-context 200 · complete-claim support 100 ·
material fact/risk recall 80 (document-level) · abstention/unanswerable 80 ·
change detection 40.

**Held out:** 8 companies and all their documents are reserved and never
used for rule or prompt development; results are reported separately.

## Labelling protocol
1. Two qualified labellers (mining technical + financial) label independently
   from primary documents, recording page/cell for each label.
2. Disagreements are adjudicated by a third reviewer; the adjudication and
   reason are kept. Label provenance is stored per question
   (`label_source: expert:<labeller>/<adjudicator>`).
3. Absence labels require defined coverage (which documents, which sections).

## Measures (reported separately, never combined)
value-and-context accuracy · complete-claim support · material fact/risk
recall · appropriate abstention · false answer on unanswerable · answerable
coverage · freshness · reviewer effort (timed) · latency · cost. Each with
numerator, denominator, exclusions and a 95% Wilson interval; strata reported
individually. Zero observed errors is reported as an interval, not as
"error-free".

## Release rule
No known material unresolved errors on the agreed release fixtures and
benchmark subset. Structural citation completeness is a software invariant
(tested); semantic validity needs evidence checks and review. Rerun after any
model, prompt, parser, schema, calculation or retrieval change.

## Question file format (JSONL)
```json
{"id": "dev-001", "company_key": "HPG", "question": "What is the after-tax NPV?",
 "expected": {"status": "answered", "value": "412000000", "unit": "USD", "date": "2026-06-01"},
 "stratum": {"stage": "pea", "doc_quality": "clean_pdf", "failure_type": "conflict_resolved"},
 "label_source": "synthetic-dev (developer-written; NOT expert ground truth)", "held_out": false}
```
