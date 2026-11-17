# Data contracts

Machine-readable contracts are generated from the code by
`python scripts/export_contracts.py`:

- [`contracts/schema.json`](contracts/schema.json) — every table and column,
  type, nullability, whether tenant-scoped, JSON-encoded, or mutable after insert
- [`contracts/api.json`](contracts/api.json) — GET routes, POST actions, auth and error semantics
- [`contracts/definitions.json`](contracts/definitions.json) — metric registry and formulas, with versions

Schema migrations: `jmi/migrations/NNN_*.sql`, applied in order, each with its
marker in one transaction (`jmi/db.migrate`).

## Entities (brief §6) → tables

| Brief entity | Table(s) |
|---|---|
| Organization/Tenant, User, Role, Workspace | `tenants`, `users`, `sessions`, `workspaces` (roles are code: `auth.CAPS`) |
| Company, Listing, Project, OwnershipInterest, Counterparty | `companies`, `entity_aliases`, `listings`, `projects`, `ownership_interests`, `counterparties`, `counterparty_links` |
| Document, DocumentVersion, SourceLocation, IngestionRun | `documents`, `document_versions`, `pages`, `doc_tables`, `source_locations`, `ingestion_runs`, `passages_fts` (derived) |
| FactCandidate, FactRevision | `facts` (candidates become rows with a workflow state; revisions via `revision_of`/`relation`) |
| Calculation, Assumption, ReviewDecision | `calculations`, `assumptions`, `review_decisions` |
| RiskFinding, DiligenceQuestion, Commitment | `risk_findings`, `risk_evidence`, `risk_history`, `diligence_items`, `diligence_questions`, `commitments`, `commitment_updates` |
| Event, ThesisVersion | `events`, `event_links`, `notifications`, `theses`, `thesis_versions`, `thesis_assumptions` |
| PeerSet, ComparisonSnapshot, MemoVersion, AuditEvent | `peer_sets`, `peer_members`, `comparison_snapshots`, `memos`, `memo_versions`, `audit` |
| (lineage) | `dependencies` (from_kind, from_id → to_kind, to_id) |
| (operations) | `source_feeds`, `usage_ledger`, `exports`, `watchlists`, `watchlist_members`, `holdings`, `meta` |

## Fact contract (brief §6 "Every fact must preserve")

| Requirement | Columns |
|---|---|
| Entity and metric definition | `company_id`, `project_id`, `metric_id`, `definition_version` |
| Source value/text, normalised value, transformations | `raw_text` (exact quote), `raw_value`, `normalized_value` (Decimal text or enum; NULL = unknown), `transformations[]`, `precision_lo/hi` |
| Units, scale, currency, scope | `unit`, `currency`, scale recorded in `transformations`, `scope_basis`, `reporting_basis` |
| Period, effective, publication, retrieval dates (distinct) | `period_start`, `period_end`, `as_of_date`, `effective_date`, `publication_date`, `retrieved_at` |
| Study, category, ownership basis, qualifiers | `study_type`, `tax_basis`, `discount_rate`, `resource_category`, `estimate_status`, `qualifiers{}` |
| Exact document version and location | `version_id`, `location_id` → `source_locations` (page, table/row/col/cell or char range, quote, context, footnotes, bbox only from the PDF text layer) |
| Evidence type | `evidence_type` ∈ observed, reported, calculated, forecast, unknown_disputed; `attribution` |
| Workflow state, reviewer decisions, lineage | `workflow_state`, `checks[]`, `missing_reason`, `review_decisions`, `revision_of`, `relation`, `dependencies` |

Rules: Decimal only; explicit NULL with `missing_reason`; a stated zero is
`'0'` with its quote; value columns are immutable (only `workflow_state`,
`checks`, `updated_at` change — see `store.MUTABLE`).

## Equivalence keys

`definitions.MetricDef.key_fields` defines "the same metric" for
reconciliation (e.g. NPV: company, project, metric, effective date, study
type, tax basis, discount rate, basis, price case). Stored on each fact as
`equivalence_key` (canonical JSON).
