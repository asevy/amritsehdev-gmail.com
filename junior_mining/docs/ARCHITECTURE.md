# Architecture decisions

Each decision records context, choice and consequence. Decisions are
reversible unless stated.

## AD-1 Stack: Python stdlib server + SQLite, as in the inspected products

*Context.* The only tested, supported stack among the accessible repositories
is Vision//Edge (stdlib `http.server`, `sqlite3`, scrypt auth, hash-chained
audit; 296 of its checks pass) plus mso-ip-lab (numbered SQL migrations,
pytest; 168 tests pass). See [REUSE_INVENTORY.md](REUSE_INVENTORY.md).

*Choice.* Python 3.13, stdlib HTTP server, one SQLite database in WAL mode,
FTS5 for derived search. Parsing adapters use libraries already present
(pdfplumber, pypdfium2, openpyxl, reportlab).

*Consequence.* No web framework; dependencies are the parsing libraries plus the
Anthropic SDK and MCP SDK used only by the optional Claude features.
Single node; one SQLite connection serialised by a lock (each HTTP request
holds it). Adequate for a pilot; a multi-node deployment would move the
store behind the same `Store` interface to PostgreSQL with row-level security.

## AD-2 Isolated module, adapted (not imported) code

The product lives in `junior_mining/`; the swing toolkit, Vision//Edge and
mso-ip-lab are untouched. Adapted code carries a provenance header (source
repo, commit, path, what changed). A shared library is deferred until a
second product needs the same component — extracting one now would require
changing the clinical product's release checks.

## AD-3 Tenant boundary enforced in the store

Every tenant-owned table has `tenant_id`. `Store.scope()` derives the tenant
from the authenticated actor and **raises** on an unknown role (Vision//Edge
rule). All reads/writes go through `Store.get/find/insert/update`, which add
the tenant predicate; a record of another tenant is `NotFound` → HTTP 404.
Blobs are stored per tenant (`blobs/<tenant>/…`), FTS rows carry `tenant_id`
and every search filters on it, page-image cache keys include the tenant,
background jobs run as `system:<purpose>` principals bound to one tenant.
Same bytes uploaded by two tenants are stored twice (no cross-tenant dedupe).

## AD-4 Evidence model: value and workflow are separate axes

A fact row stores the exact quote, printed token, normalised Decimal, unit,
currency, implied precision interval, every transformation, scope/basis,
period / as-of / effective / publication / retrieval dates, study and
resource qualifiers, attribution, **evidence type** (observed, reported,
calculated, forecast, unknown/disputed) and **workflow state** (candidate,
source-matched, needs-review, conflicting, reviewer-approved, superseded,
rejected). Only workflow state is mutable. Corrections and restatements are
new rows linked by `revision_of` / `relation`; nothing is overwritten.

## AD-5 Propose → re-derive → review

Extraction (deterministic rules; a provider-neutral model boundary exists)
only **proposes**. `validate.py` independently re-reads the cited text and
checks quote presence, entity (including the cited sentence re-derived from
the page), dates (as-at vs other dates), value and scale, currency, unit,
category, basis, study qualifiers, sign, historical status, true width.
Fail → rejected; missing/ambiguous → needs-review; all pass → source-matched.
A reviewer then approves; approval means "matches its source", never
"independently true". Separation of duties: nobody approves their own entry,
correction or memo.

## AD-6 Reconciliation by equivalence key and printed precision

Two reports are compared only when their equivalence key matches (metric
definition + entity + category + basis + study qualifiers + date). They
reconcile when their printed-precision intervals overlap (US$412 million
⇒ [411.5, 412.5] million); otherwise both become conflicting and a
discrepancy opens. A later document supersedes an earlier fact only through
an explicit restatement of the same key. Mirrored releases (Jaccard ≥ 0.8 on
5-word shingles, different document) are linked and not extracted again.

## AD-7 Deterministic calculations with lineage and invalidation

Formulas are versioned pure Decimal functions (`calc.PURE`). Inputs are
reviewer-approved facts and assumptions with rationale (FX needs source and
date). A missing input withholds the result. Results store inputs, warnings,
caveats; `recompute()` reproduces them exactly. A `dependencies` table links
location → fact → calculation → snapshot / memo version / thesis assumption;
corrections, restatements and rejections mark dependents stale.

## AD-8 Memos are claim lists, approval is gated, approved versions immutable

Every memo claim references fact/calculation/risk ids and is validated as a
complete statement (numbers, dates, category, permit status, attribution,
forecast wording, NPV qualifiers, equity-value conflation). Unsupported
claims are withheld from the body. Approval requires reviewer approval of
each claim, inclusion of every open risk (with contrary evidence), a
counter-thesis, no stale inputs, and approver ≠ author. Approved versions are
hashed and never rewritten; later evidence changes are shown as
"changed since approval".

## AD-9 No scoring anywhere

There is no scoring engine, field, label or colour code. `policy.py` scans
schemas, API payloads, pages and exports for score-like fields and values;
the server runs the key check on every JSON response (policy guard) and the
test suite runs the full scan. Retrieval ranking (FTS bm25) orders passages
internally and is never returned. Default orderings are alphabetical.

## AD-10 UI without JavaScript

Server-rendered HTML forms with a session-bound CSRF token; CSP
`default-src 'none'` (no scripts at all). Status in words, not colours.
Quoted document text sits in `<blockquote>`/`<q>` so it is visibly the
source, not the application.

## AD-11 Documents are untrusted data

Document text is stored, displayed and searched; it is never interpreted as
instructions. No component gives document text access to tools, roles or
workflow transitions. The model boundary (`extract.ModelProposer`) passes text
as delimited data and reduces output to a fixed schema; extra keys (workflow
state, role, "approve") are discarded and reported.

## AD-12 Claude is a proposer and a reader, never an authority

Claude (via the Anthropic API) may propose candidates, map questions to metric
ids and draft claims; its output enters through the same doors as rule output
(`ingest.record_candidate`, `answers` assembly from facts, `memo.add_claim`) and
is validated and reviewer-approved like anything else. Per-firm opt-in with the
firm's own key (only the env-var name stored). Calls run off the request thread
with no transaction open. The MCP connector exposes the store to Claude
read-only through per-user tokens whose actor carries only the `read`
capability. See CLAUDE_INTEGRATION.md.

## Module map

| Module | Responsibility |
|---|---|
| `config` | settings, pinned clock |
| `db`, `audit` | SQLite, migrations, transactions, backup/restore; hash-chained audit |
| `auth`, `store` | users/sessions/roles; tenant-scoped access |
| `definitions`, `quantities` | metric registry; Decimal parsing, units, dates |
| `parsers`, `extract`, `validate` | bytes → pages/tables; candidates; independent checks |
| `ingest`, `facts`, `lineage` | upload/runs/mirrors/coverage; fact lifecycle & reconciliation; dependencies |
| `entities` | companies, projects, aliases, listings, ownership history, counterparties |
| `calc`, `peers` | formulas & assumptions; candidate peers, approval, snapshots |
| `risks`, `diligence` | risk register; checklists, questions, commitments |
| `memo`, `answers`, `exports` | thesis, claims, approval, render; constrained Q&A; PDF/CSV/JSON |
| `events`, `monitoring` | one event system; coverage status, inbox, watchlists, portfolio |
| `policy` | no-score guard |
| `server`, `ui` | HTTP routes, actions, HTML |
| `seed`, `bench` | synthetic workspace; benchmark runner |
| `claude`, `mcp_server` | optional Claude API features (opt-in per firm); read-only Claude connector |
