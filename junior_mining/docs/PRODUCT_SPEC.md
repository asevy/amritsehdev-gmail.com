# Product specification (as built)

Users: mining private equity, resource funds, project financiers,
royalty/streaming teams. Roles: administrator (users, audit, usage), analyst
(create, extract, correct, draft, export), reviewer (analyst rights plus
approve/reject facts, resolve discrepancies, confirm findings, approve
memos), read-only (view). Enforced server-side.

The application answers six questions — what was disclosed, what changed,
what could undermine the investment, which alternatives look stronger on
specified measures and why, what is missing or contradictory, and how to keep
an evidence-backed memo — through six workspaces sharing one set of records.

## A. Company & Projects
Company identity with recorded names, aliases and validity dates; exchange-
qualified listings; projects modelled separately from issuers (commodity,
jurisdiction, stage, deposit, process, infrastructure); ownership history as
dated rows; counterparties (royalty, stream, offtake, lender, JV) linked to a
citation. Fact tables grouped by capital structure, resources/reserves,
study economics (forecasts), metallurgy/drilling/permits/disclosures, each
listing what was *not found in documents reviewed*.
Screens: `/company/<id>`, `/project/<id>`, `/company/<id>/documents`.

## B. Evidence & Discrepancies
Upload with content hash, immutable versions, per-tenant blob storage,
idempotent ingestion runs with visible failures and retry; document viewer
with page text, highlighted cited characters or table cell, footnotes, page
image (PDF), coordinates only from the PDF text layer; extraction review
queue; fact record with checks, review history, revisions, downstream
outputs, corroboration note; discrepancy workspace showing both sources side
by side with a reviewer resolution. Screens: `/doc/<v>`, `/review`,
`/fact/<id>`, `/discrepancies`, `/discrepancy/<id>`.

## C. Risks & Alternatives
One register over 13 categories (brief §9). Each item: neutral title,
company/project, dated supporting and contrary evidence (facts or analyst
citations), consequence, dependencies, mitigants, unresolved questions,
monitoring trigger, owner, reviewer, status, history. Rules may open
*questions* from specific disclosures (going concern, permit not issued, PEA
economics, warrant overhang, historical estimate); a *documented finding*
requires supporting evidence and a reviewer who is not the author. Attention
flags carry the analyst's reason. No scores or grades. Screen: `/risks/<id>`.

## D. Peer Comparison & Scenarios
Candidate generation by commodity, stage/stage group, jurisdiction, deposit,
process, ownership and investability, each with reasons and differences;
strict peer vs broader comparator; analyst approve/exclude/override with
rationale; set approval. Snapshots on one market-data date: market cap, EV
(explicit bridge), EV per M&I oz (100% and attributable), EV per P&P oz,
reported after-tax NPV/IRR/capex/gold price, attributable NPV (not equity
value), permit status, ADV, balance-sheet date gap. Incompatibilities
(study type, price assumptions, reporting basis, effective dates) are shown;
unsupported cells are withheld with reasons; observations are per-measure
("under these inputs … differences that remain unresolved"); explanations
list subject disadvantages, peer advantages and missing evidence. Scenario
calculations: dilution, runway, ownership bridge, equity bridge (only when
fully specified), liquidity days. Screens: `/peers/<id>`, `/peerset/<id>`,
`/snapshot/<id>`, `/calcs/<id>`, `/calc/<id>`.

## E. Diligence & Investment Memo
Stage-aware checklist (16 items gated by stage) linked to evidence; missing
required metrics create specific questions and document requests; never a
"complete diligence" label. Management commitments as attributed statements
with original wording, target window (only for unambiguous forms), explicit
revisions; a passed window is described as an observation, not "missed".
Thesis with counter-thesis and tracked assumptions. Memo versions built from
approved records; claim-level validation; withheld claims listed; reviewer
approval per claim; approval gates; immutable approved versions; PDF / CSV /
JSON export with references, dates, definitions, status and gaps.
Screens: `/diligence/<id>`, `/memos/<id>`, `/memo/<id>`, `/ask/<id>`.

## F. Monitoring & Portfolio
One event system (new document, mirrored release, restatement, discrepancy,
commitment recorded/revised, thesis assumption affected, outputs
invalidated, ingestion failed, unreadable pages) feeding the change inbox
with review/dismiss-with-reason; in-app notifications only; watchlists with
coverage status (fresh / stale / incomplete / ingestion failed, with
reasons); portfolio exposures grouped by commodity, jurisdiction, stage,
counterparty and funding dependency, with unknowns listed as "not
established"; liquidity scenarios. Screens: `/`, `/inbox`, `/portfolio`.

## Excluded by design (brief §16)
Scores, ratings, grades, confidence or probability figures, price targets,
recommendations, "complete diligence" labels, sentiment-based management
judgements, fraud labels, universal exit estimates, free-form factual answers,
autonomous trading or messaging, geological modelling, clinical features,
certification claims, competitor-superiority claims.

## Commercial benchmark baseline (unverified)
The brief's November 2026 table of public product descriptions (Hudson Labs,
AlphaSense, S&P Capital IQ Pro Metals & Mining, Junior Mining Intelligence,
Premissive, MineAnalyst, Lonmining) was used as feature context only. A
recheck of the nine public pages was attempted on 2026-11-17 and **failed**:
every host is outside this environment's network allowlist (DNS failure). No
competitor capability, accuracy or adoption claim is made anywhere in this
product or its documents.
