# Junior Mining Intelligence — scripted demonstration (SYNTHETIC data)

Server: http://127.0.0.1:42291 · analysis clock pinned to 2026-11-17 15:00 UTC · data dir: (temporary)

- [x] analyst, reviewer and other-tenant analyst sign in

## 1. Create the company/project workspace
- [x] 5 synthetic companies with projects, listings and ownership created
- [x] the other tenant creates its own record of a same-named company

## 2. Upload documents (PDF, XLSX, CSV, TXT) — ingestion runs on upload
  - HPG_PEA_Technical_Report_Summary_2026.pdf: HTTP 200, ingestion succeeded
  - HPG_Q3_2026_MDA.pdf: HTTP 200, ingestion succeeded
  - HPG_NR_2026-10-08_drilling.txt: HTTP 200, ingestion succeeded
  - SynthWire_HPG_2026-10-08.txt: HTTP 200, ingestion succeeded
  - HPG_resource_by_zone.xlsx: HTTP 200, ingestion succeeded
  - HPG_Investor_Presentation_2026-09.pdf: HTTP 200, ingestion succeeded
  - market_snapshot_2026-11-13.csv: HTTP 200, ingestion succeeded
  - TVG_Corporate_Summary_2026-10.pdf: HTTP 200, ingestion succeeded
  - OBR_Corporate_Summary_2026-09.pdf: HTTP 200, ingestion succeeded
  - QRC_Corporate_Summary_2026-10.pdf: HTTP 200, ingestion succeeded
  - BWM_Corporate_Summary_2025-03.pdf: HTTP 200, ingestion succeeded
  - HPG_corrupt_upload.pdf: HTTP 200, ingestion failed
  - OtherFund_private_term_sheet.txt: HTTP 200, ingestion succeeded
- [x] corrupt PDF is a visible failed run, not silently skipped
- [x] mirrored press release detected and not re-extracted — similarity 0.884

## 3. Inspect and review extracted facts
  Workflow states after extraction: {"conflicting": 2, "needs_review": 2, "rejected": 1, "source_matched": 116}
- [x] number about a similarly named project of another company rejected (wrong entity)
- [x] OCR-style '2O1' kept unread and sent to review
- [x] an analyst cannot approve facts (server-side role check) — HTTP 403
- [x] reviewer approved 116 source-matched records (approval = matches source, not independent truth)
- [x] OCR correction stored as a new revision and approved by a different person

## 4. Surface a discrepancy and non-financial risks
  Discrepancy: Net present value (study): '412' vs '432' (technical report vs investor presentation)
- [x] reviewer resolves the conflict with a recorded reason; both sources preserved
  Open question (engineering_construction): Project economics are from a PEA (preliminary; may rely on Inferred resources)
  Open question (permitting_environment): environmental approval (EIS): not issued in documents reviewed
  Open question (financing_shareholder): Warrants outstanding: potential dilution if exercised
  Open question (financing_shareholder): Issuer discloses a material uncertainty about its ability to continue as a going concern
- [x] permitting and going-concern items opened as QUESTIONS, not findings or grades
- [x] analyst records an evidence-quality discrepancy with citations and an attention reason

## 5. Approve a justified peer set and compare supported metrics
  Brightwater Minerals Ltd.: broader_comparator → approved (gold asset; differences recorded and shown)
  Orrin Basin Resources Ltd.: strict_peer → approved (gold asset; differences recorded and shown)
  Quillon Ridge Copper Corp.: broader_comparator → excluded (copper porphyry — different commodity)
  Tamsin Vale Gold Inc.: strict_peer → approved (gold asset; differences recorded and shown)
  > EV per M&I oz (100% basis): Halvard Peak Gold Corp. vs Brightwater Minerals Ltd. — not compared (total debt (silence is not zero): not established in documents reviewed).
  > Under these inputs, Orrin Basin Resources Ltd. has a higher EV per M&I oz (100% basis) than Halvard Peak Gold Corp. (CAD/oz 271.12 vs CAD/oz 75.93). Differences that remain unresolved: different jurisdiction (Quebec, Canada); 70% joint venture interest — attributable basis needed for company-level comparison.
  > Under these inputs, Tamsin Vale Gold Inc. has a higher EV per M&I oz (100% basis) than Halvard Peak Gold Corp. (CAD/oz 308.39 vs CAD/oz 75.93). Differences that remain unresolved: stage differs: Feasibility vs Preliminary economic assessment — study maturity is not like-for-like; different jurisdiction (Nevada, USA); process route differs (heap leach vs CIL).
  > EV per attributable M&I oz: Halvard Peak Gold Corp. vs Brightwater Minerals Ltd. — not compared (total debt (silence is not zero): not established in documents reviewed).
  comparability [attributable_npv]: Attributable NPV is the ownership share of a reported project NPV. It is not company equity value.
  comparability [ev_per_mi_oz_100]: Resource reporting bases differ (inclusive vs exclusive of reserves) — None: Halvard Peak Gold Corp., Orrin Basin Resources Ltd.; inclusive: Tamsin Vale Gold Inc.
  comparability [ev_per_mi_oz_attr]: Resource reporting bases differ (inclusive vs exclusive of reserves) — None: Halvard Peak Gold Corp., Orrin Basin Resources Ltd.; inclusive: Tamsin Vale Gold Inc.
  comparability [initial_capex]: Not like-for-like: study types differ — PEA: Halvard Peak Gold Corp., Orrin Basin Resources Ltd.; FS: Tamsin Vale Gold Inc.
  comparability [irr_after_tax]: Not like-for-like: study types differ — PEA: Halvard Peak Gold Corp., Orrin Basin Resources Ltd.; FS: Tamsin Vale Gold Inc.
  comparability [npv_after_tax]: Not like-for-like: study types differ — PEA: Halvard Peak Gold Corp., Orrin Basin Resources Ltd.; FS: Tamsin Vale Gold Inc.
- [x] comparisons are per specified measure with unresolved differences; no overall winner

## 6. Draft, review and approve a cited memo
- [x] unsupported claim citing a real source is withheld — the claim states the authorization was issued/approved; the cited status is 'Application accepted for review'; an issuer statement is presented as established fact; attribute it (e.g. 'the company reports')
- [x] restated claim with correct status and attribution is supported
- [x] reviewer approves the memo version (author ≠ approver; all register risks included) — {"ok": true, "result": {"approved_at": "2026-11-17T15:00:00Z", "approved_by": "reviewer.a", "author": "analyst.a", "body": {"peer_set_id": "pset_78d63eeffd249dfa", "removed": [{"at": "2026-11-17T15:00
- [x] evidence-preserving PDF export recorded with its SHA-256 — 68cdf5da669fd644

## 7. Ingest an update; show affected assumptions and stale outputs
  inbox: commitment_revised: Target explicitly revised: complete the pre-feasibility study — in Q2 2027 → in Q4 2027
  inbox: restatement: Restated: Mineral resource contained metal (Measured & Indicated 2026-04-30) 920 → 893
  inbox: restatement: Restated: Mineral resource tonnage (Measured & Indicated 2026-04-30) 22.8 → 22.1
  inbox: restatement: Restated: Mineral resource contained metal (Indicated 2026-04-30) 724 → 697
  inbox: restatement: Restated: Mineral resource tonnage (Indicated 2026-04-30) 18.6 → 17.9
  inbox: thesis_assumption_affected: Thesis assumption affected: M&I resource of about 920 koz (effective 2026-04-30) supports scale
  inbox: new_document: New document: Halvard Peak Gold Corp. news release: Halvard Peak Project resource update (2026-11-16)
  inbox: ingestion_failed: Ingestion failed: Corrupt upload (SYNTHETIC failure case) — ParseError: unreadable PDF: PdfminerException
- [x] approved memo flagged stale, status and content unchanged — source fact fact_f4c753161143c923 restated by fact fact_d2120d0c14847209
- [x] thesis assumption marked affected by the restatement — new mineral resource contained metal disclosed (893, 2026-04-30); assumption needs re-review
- [x] comparison snapshot marked stale
- [x] PFS target recorded as an explicit issuer revision (not inferred as 'missed')

## 8. Unsupported answers are withheld
  Q: What is the probability the project reaches production?
    → declined: This system does not estimate probabilities of success or of any outcome.
  Q: Should we buy Halvard Peak?
    → declined: This system does not make buy, sell or hold recommendations.
  Q: What is the 2027 production guidance?
    → not_found: Not found in documents reviewed. No defined metric matches this question and no passage contains its terms. This does not establish that it 
  Q: What is the true width of hole HP-26-041?
    → not_found: True width is not established in documents reviewed. Reported intercepts are down-hole lengths; true-width status stated: issuer estimate: a
  Q: What is the after-tax NPV?
    → answered: Answer assembled from reviewer-approved, cited facts.
    → Halvard Peak Gold Corp. reports net present value (study) of US$412 million (after-tax, 5% discount rate, 100% basis), effective 2026-06-01 [Halvard Peak Gold C

## 9. Cross-tenant access is denied
- [x] other tenant GET doc/… → 404 — HTTP 404
- [x] other tenant GET api/… → 404 — HTTP 404
- [x] other tenant GET export/… → 404 — HTTP 404
- [x] other tenant GET company/… → 404 — HTTP 404
- [x] other tenant search finds none of this tenant's passages
- [x] database integrity ok and audit chain verifies — 254 audited events

_Generated by `python scripts/demo.py`. Identifiers differ per run; all data is synthetic._
