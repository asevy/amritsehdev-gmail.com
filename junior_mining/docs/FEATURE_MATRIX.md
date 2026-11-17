# Feature completion matrix

**Implemented / tested** = code exists and automated tests (or the scripted
demo) exercise it. **Implemented / awaiting validation** = works on synthetic
fixtures but needs expert review, real documents or a pilot to validate.
**Deferred / blocked** = not built, with the reason.

| Area | Feature | Status | Notes |
|---|---|---|---|
| Access | Password auth (scrypt), sessions, lockout, CSRF, security headers | Implemented / tested | Adapted from Vision//Edge; no MFA/SSO |
| Access | Roles admin/analyst/reviewer/read-only, server-side | Implemented / tested | |
| Access | Tenant isolation (store, blobs, search, cache, jobs, exports) | Implemented / tested | Single SQLite file; logical isolation |
| Access | Hash-chained audit, tamper detection | Implemented / tested | Not WORM storage |
| Ingestion | PDF, XLSX, CSV, TXT upload; hashes; immutable versions; dedupe; idempotent runs; retry; failure visibility | Implemented / tested | |
| Ingestion | Table row/column/header/footnote capture; merged cells; footnote markers | Implemented / tested | Ruled PDF tables; unruled tables not detected |
| Ingestion | Unreadable-page detection; page images; text-layer coordinates | Implemented / tested | OCR blocked (no engine) |
| Ingestion | Mirrored-release detection | Implemented / tested | Similarity threshold 0.8 not tuned on real data |
| Extraction | Deterministic rules for ~30 mining/financial metrics, permits, commitments, disclosures | Implemented / awaiting validation | Written against synthetic phrasing; real-document recall unknown |
| Extraction | Claude candidate proposals (structured output, verbatim-quote check, same validation, reviewer approval) | Implemented / tested with fake client | No live call made; precision/recall vs rules unmeasured |
| Q&A | Claude question routing (metrics only; answers from records; refusals first) | Implemented / tested with fake client | Same |
| Memo | Claude claim drafting (validated per claim; withheld if unsupported) | Implemented / tested with fake client | Same |
| Connector | MCP server for Claude Desktop / Claude Code: 9 read-only, tenant-scoped, audited tools; per-user hashed tokens | Implemented / tested (incl. real stdio round trip) | claude.ai web connector (HTTPS + OAuth) not built |
| Validation | Independent re-derivation of entity, dates, value/scale, currency, unit, category, basis, study qualifiers, true width, status | Implemented / tested | |
| Review | Queue, approve/reject/needs-review, corrections as revisions, separation of duties | Implemented / tested | |
| Reconciliation | Equivalence keys, precision-overlap tolerance, conflicts, discrepancy workspace, explicit restatements | Implemented / tested | |
| Calculations | Market cap, EV bridge, dilution, runway, attributable NPV, equity bridge, EV/oz, inferred share, liquidity, FX | Implemented / tested | |
| Calculations | Full DCF, commodity sensitivities, royalty/stream models | Deferred | Brief §11 "deferred advanced models" |
| Lineage | Dependencies, invalidation, stale flags, events | Implemented / tested | |
| Risks | 13-category register, supporting/contrary evidence, attention with reason, finding confirmation | Implemented / tested | Rule set is small (6 rules) |
| Diligence | Stage-aware checklist, gap questions, document requests, commitments and revisions | Implemented / tested | Checklist content needs specialist review |
| Peers | Candidate generation, rationale, approval, snapshots, comparability notes, withholding, sorting | Implemented / tested | Investability uses listing + ADV only |
| Memo | Thesis/counter-thesis/assumptions, claim validation, withholding, approvals, immutable versions | Implemented / tested | |
| Exports | PDF/CSV/JSON with references, status, gaps; recorded with hash | Implemented / tested | |
| Q&A | Constrained answers, refusals, not-found with coverage, passages-only | Implemented / tested | Intent matching is keyword-based |
| Monitoring | Event system, inbox, watchlists, coverage status, notifications (in-app) | Implemented / tested | |
| Portfolio | Holdings, exposures, unknowns, liquidity scenarios | Implemented / tested | |
| Commercial | Tenants with plan/seats/entitlements, seat limit, usage ledger | Implemented / tested (seat limit, ledger) | No payment provider (by design for pilot) |
| Benchmark | Runner, separate measures, intervals, provenance flag; proposal | Implemented / tested | Expert labels unavailable → validation pending |
| Connectors | SEDAR+, EDGAR, market data, registries, insider data | Blocked / not built | See DATA_SOURCES.md |
| Domain rules | Definitions registry | Implemented / awaiting validation | Needs QP / disclosure-specialist review; S-K 1300 and JORC nuances not encoded |
| Competitive recheck | Public pages in brief §4 | Blocked | Hosts not in network allowlist |
| Deployment | TLS, backups off-box, monitoring | Not deployed | DEPLOY.md describes required steps |
