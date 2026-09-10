# Data Access Map — Phase 0 of the Validation Sprint

> **Status: OPEN — living operational document, not a narrative memo.**
> Precedes the ten-family deep dives. Every cell must eventually answer
> the same operational questions (see the source record template), because
> this map is simultaneously the research architecture, the staffing
> model and the cost model of the company.
>
> Update log: 2026-09-09 created; seeded first-pass rows for Barbados,
> Jamaica, DR, Cayman (sources in per-market notes). 2026-09-09 v2:
> operational restructure — access states, source record template,
> jurisdiction scorecard, entity-status taxonomy, Panama dual role,
> playbook program.

## Why this is the moat

**"Not readily Googleable" is not the same thing as "not public."** The
raw material lives in corporate registries, shareholder registers,
securities filings, proxy circulars, land registries, mortgage/charge
registries, court records, probate/estate filings, government gazettes,
procurement databases, planning/development records, incorporation
documents and historical filings. Nobody has assembled it into
Person → Family → HoldCo → Company → Asset → % economic interest →
current valuation. The moat is public information that is fragmented,
expensive, multilingual, historical and tedious to assemble — organized
into a living Caribbean ownership graph.

## The three access states

Never conflate these; record each separately for every source:

- **O — Obtainable.** The record can legally be acquired.
- **I — Internal-use.** It may inform research and internal graph-building.
- **P — Publishable/reusable.** It may be republished or commercially
  reused (directly or as derived data) without breaching a permitted-use
  restriction.

Obtainable does not imply publishable: a statutory shareholder list may be
legally obtainable yet carry use restrictions (the live Barbados s.176
question). A source's state is O/I/P with a citation for each, or an
explicit "restriction: …" note.

## The source record template

Every source entry in this map must eventually capture:

1. Legal basis (statute/regulation/practice)
2. Access method (online / in person / by post / through agent)
3. Requester eligibility (anyone / account / subscriber / legitimate
   interest / party only)
4. Required documents or formalities (forms, affidavits, IDs)
5. Cost (per search / per document / subscription)
6. Turnaround
7. Historical depth (how far back; digitized vs. paper)
8. Fields returned
9. Use restrictions (the O/I/P determination)
10. Update frequency / data freshness
11. Machine-readability (structured data vs. scans)
12. Bulk or API access (exists / negotiable / none)

## The standard escalation ladder (per listed/large company)

1. Exchange disclosures (substantial holders, insider filings)
2. **Listing documents — IPO prospectuses, rights-issue circulars.**
   Rank these extremely high whenever a listed company emerged from a
   family-controlled private group: the issuer must explain pre-IPO
   ownership, related parties, corporate structure and principal
   shareholders to investors at the listing event, so a prospectus
   often contains a richer ownership snapshot than any later annual
   report. (The Wisynco 2017 prospectus is the type case: one document
   may collapse the WGCL/Evesam/family unknowns at once.)
3. Annual report / proxy circular (shareholder analyses, directors'
   interests)
4. Statutory shareholder-list routes (e.g., Barbados Companies Act s.176)
5. Registry company search (officers, filings, charges)
6. Intermediary/holding-company identification
7. Beneficial-ownership tracing (or a precise record of why access is
   restricted)
8. Land, charges, courts, probate, gazettes, procurement, planning

## The intermediary workflow (mandatory)

A registered holder is the **next node, not the end.** "Neptune
Investments Ltd — 13.9%" means: who owns Neptune?

- Family members → HoldCo → Neptune → target: **calculate through the
  chain.**
- Unrelated institutional owners: **do not attribute** to the family.
- Nominee structure: **investigate the beneficial interest**; never assume
  the registered holder is the economic owner.
- Restricted beneficial-ownership access: **record precisely that
  limitation** rather than treating the question as unknowable.

**Every intermediate entity carries a status** — assigned, sourced and
dated, never left implicit:

> operating company · holdco · nominee · trustee · foundation · SPV ·
> employee share plan · institutional investor · government/state ·
> estate · **unknown**

"Unknown" is an honest status with a follow-up task attached. This
taxonomy exists to stop an analyst mistaking an administrative holder for
a family-controlled vehicle (or the reverse).

## Access matrix (record types × markets)

Cell values are access states (O/I/P) once researched. Interim legend:
✓ = confirmed first-pass · ◐ = partial/limited · ✗ = restricted ·
R = research needed

| Market | Company registry | Shareholder register access | Beneficial owners | Land/property | Charges/debt | Courts | Securities |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Barbados | ✓ CAIPO: free limited search; paid Company Inquiry (~BBD $5); online since 2021 | ◐ s.176 route: obtainable (likely); I and P TBD pending permitted-use review | ◐ Maintained; access route to map | R | ✓ Registered mortgages/charges searchable per CAIPO | R | BSE + issuer sites (2025 AR, quarterlies confirmed) |
| Jamaica | ✓ COJ: account-based free entity search; officer details | ✓ Reverse search by shareholder/director/secretary incl. affiliations | ◐ Subscriber BO Registry, ≥25% threshold | R | R | R | JSE disclosures |
| Dominican Republic | ◐ Registro Mercantil via chambers (Santo Domingo 24/7 consultas); DGII RNC lookup | R — filed-acts depth via chamber to map | R | R | R | R | SIMV filings to check |
| Trinidad & Tobago | R | R | R | R | R | R | TTSE disclosures |
| Guyana | R | R | R | R | R | R | GSE (small) |
| Bahamas | R | R | R | R | R | R | BISX |
| Cayman | ◐ CBP pay-per-search; basics + directors | ✗ Largely not public | ✗ Confidential (since 7/2024); legitimate-interest only, ML/TF-tied | ◐ Land + planning records to map — likely richest public route | R | R | CSX (minor) |
| Turks & Caicos | R | R | R | R | R | R | — |
| Puerto Rico | ◐ Departamento de Estado registry | R | R | ◐ CRIM property records to map | R | Federal PACER + PR courts | SEC/EDGAR for US-listed |
| Panama | R — Registro Público | R | R (private-interest foundations a known opacity layer) | R | R | R | Latinex |

## Jurisdiction scorecard (provisional, first-pass — revise as cells fill)

Friction 1–5: 1 = cheap/easy/fast to maintain a current wealth graph,
5 = expensive/slow/opaque. Combines cost, access difficulty, opacity,
language burden, legal restrictions and turnaround.

| Market | Identity resolution | Historical depth | Automation potential | Friction (1–5) | Note |
| --- | --- | --- | --- | --- | --- |
| Jamaica | **High** — reverse person→entities search is graph-native | To verify | Medium-High — structured portal; API/bulk to confirm | **2** | Best market to prove the methodology end-to-end |
| Barbados | Medium — name-based; paid inquiry is the real record | To verify (free DB staleness flagged) | Medium — online since 2021; bulk unknown | **2–3** | s.176 route pending counsel |
| Dominican Republic | Medium-Low — RNC helps for entities; person-level to map | To verify | Low-Medium — chamber-mediated | **3** | Spanish-language capacity required, not a blocker |
| Cayman | Low on ownership; directors only | To verify | Low for ownership; property/planning possibly better | **4–5** | Split profile: opaque companies, promising land/planning records |
| Trinidad & Tobago | R | R | R | R | |
| Guyana | R | R | R | R | |
| Bahamas | R | R | R | R | |
| Turks & Caicos | R | R | R | R | |
| Puerto Rico | R (expect High where SEC applies) | Deep for SEC filers | High for EDGAR; local registries to map | R | |
| Panama | R | R | R | R | See dual role below |

## Panama — market AND infrastructure layer

Panama holds a dual role in this map:

1. **A market** in the Caribbean Capital Network tier (coverage of
   Panamanian business families under Panama's own franchise).
2. **A cross-border entity-resolution hub:** Panamanian companies,
   private-interest foundations and holding structures sit inside the
   ownership chains of core-Caribbean families. Resolving a Caribbean
   chain will routinely require a Registro Público lookup even when no
   Panamanian family is involved.

So Panama's row is infrastructure: its registry access, foundation regime
and nominee-director conventions get mapped at the same priority as the
launch markets, because chains from every other row terminate there.

## Jurisdiction Research Playbooks — the operational deliverable

Each market gets a compact playbook that makes the process teachable to a
research team rather than founder-dependent. Standard structure, in order:

1. Where to search first
2. How to identify a person
3. How to identify their companies
4. How to pull ownership
5. How to trace intermediaries
6. How to check property
7. How to check charges/debt
8. How to check courts/probate
9. How to preserve the evidence

Playbooks live in `playbooks/`. The canonical structure is
[playbooks/TEMPLATE.md](playbooks/TEMPLATE.md) — expected-outputs boxes,
per-route O/I/P states, friction/automation/depth lines, failure paths,
automation hooks, live-request checklists. Drafted so far:
[playbooks/BARBADOS.md](playbooks/BARBADOS.md) (reference instance;
Profile #1 runs there) and [playbooks/JAMAICA.md](playbooks/JAMAICA.md)
(richest access found). The remaining markets get playbooks as their
Phase 0 research completes — cloned from the template, never invented
from blanks.

## Standing watch

Access regimes change (Cayman's BO regime changed in 2024; Jamaica's BO
registry is recent; Barbados moved online in 2021). The map carries a
standing monitoring task: flag new registry access, filing requirements or
disclosure-regime changes as they emerge, and date-stamp every cell so
stale entries are visible.
