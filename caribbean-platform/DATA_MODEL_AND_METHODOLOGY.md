# Data Model & Methodology

> **Status: v1 draft (2026-09-08) — the next build priority, ahead of
> naming.** The purpose of this document is to prove the central moat can
> actually be constructed: define the family/company/person/asset/
> transaction model, set the wealth-estimation rules, and validate both
> against ten real Caribbean families across 4–5 islands. If those ten
> profiles work, the fundamental product is validated and we are no longer
> designing an idea — we are building the Caribbean wealth graph.

## 1. The conceptual architecture

- **The family page is the atomic unit.** Every family has people,
  companies, ownership, estimated wealth, transactions, properties,
  philanthropy, relationships and news.
- **The company page is the second atomic unit.** Ownership, financials,
  executives, transactions, subsidiaries, developments and related
  families.
- **Daily journalism is the update mechanism.** A hotel acquisition isn't
  just an article — it changes a company, a family's estimated wealth, a
  transaction history and perhaps an influence score.
- **Lifestyle reporting enriches the graph.** A new golf development
  connects developer → family → property → club → architect → hotel brand
  → transaction.
- **Rankings are outputs from the graph.** Wealth 100, Influence 50,
  Family Business 100 must never exist as disconnected spreadsheets.
- **Intelligence monetizes the graph.**

Two standing editorial rules feed this architecture: *ownership is
mandatory metadata* on every institution we cover, and *own change before
opinion* — every factual change event (sale, succession, appointment,
financing, opening) is a graph update first and a story second (see
[CONTENT_UNIVERSE.md](CONTENT_UNIVERSE.md)).

## 2. Entity model

### Nodes

| Entity | Core attributes |
| --- | --- |
| **Person** | Names (incl. Spanish double surnames, maiden names, aliases), birth/death dates, nationality(ies), residence(s), generation marker within family, education, roles (current/past) |
| **Family** | Editorial designation — see §3, the family web. Name, origin island(s), founder(s), membership rule, branches, status (active/dispersed/absorbed) |
| **Branch** | Subdivision of a family: descent line, its own holdings and management (see §3) |
| **Company** | Legal name, trade names, jurisdiction, registry ID, sector, status, financials where available, listing (exchange/ticker) |
| **Asset** | Property (parcel/registry ref where public), hotel, brand, land, vessel/aircraft/art only where legitimately public |
| **Transaction** | Type (acquisition, sale, merger, financing, IPO, liquidation, inheritance/succession), parties, date, value + currency, evidence |
| **Institution** | School, club, hospital, foundation, museum, association |
| **Recognition** | Ranking placements, awards, honors — ours and third parties' — by year |
| **WealthEstimate** | Annual snapshot per family/branch/person: range (low–high), point estimate optional, valuation date, FX date, confidence grade, methodology version, analyst notes |
| **Source** | Registry filing, court record, exchange filing, press item, interview, company statement — with date, type, reliability tier |

### Edges (all edges carry valid-from / valid-to dates and at least one Source)

| Edge | Between | Notes |
| --- | --- | --- |
| kinship | Person ↔ Person | parent/child, marriage (incl. dissolved), sibling; marriages between covered families are first-class inter-family connections |
| membership | Person → Family/Branch | with role: founder, principal, heir, spouse-in, exited |
| ownership | Person/Family/Company → Company/Asset | % stake, direct or via named intermediary (holdco, trust, foundation), attribution basis |
| role | Person → Company/Institution | CEO, chair, director, partner, trustee — dated; feeds People & Careers |
| control | Person/Family → Trust/Foundation → holdings | settlor/trustee/beneficiary distinctions matter for attribution (§4) |
| philanthropy | Person/Family/Foundation → Institution | gift, pledge, board seat, patronage |
| affiliation | Person → Institution | education, club membership |
| party-to | Person/Family/Company → Transaction | buyer, seller, lender, advisor |
| coverage | Article → any node | every published story links the nodes it touched — journalism as update mechanism, made literal |

**Temporality is non-negotiable.** Nothing is overwritten: stakes,
roles and estimates are dated intervals, so the graph can be queried "as
of" any year. The longitudinal archive — how ownership and wealth moved
over 5, 10, 20 years — is the part competitors cannot reconstruct later.

**Evidence is fact-level.** Every attribute and edge cites its source(s)
with a reliability tier (§6). An unsourced claim does not enter the graph;
it goes to a research-leads queue.

## 3. The family web — how "family" is modeled

The hardest modeling decision. Three options were considered:

**Option A — family as a fixed surname entity.** Simple; matches how
readers speak ("the Rainieri family"). Breaks quickly: marriages join
fortunes, branches diverge economically, feuds split groups, double
surnames cross, matrilineal wealth is misfiled, and one entity forces one
wealth number onto genuinely separate economic units.

**Option B — no family entity; only persons and kinship edges,** with
"family" computed as a connected subgraph. Purest data model, but
editorially unusable: rankings need stable, named, defensible units, and a
computed cluster boundary becomes an editorial argument with every family
that dislikes its composition.

**Option C — family as a curated overlay on the person graph, with
branches as first-class citizens. This is the chosen model.**

- The **ground truth is the person graph**: people and dated kinship,
  ownership and role edges, each individually sourced.
- A **Family** is an editorial designation layered on top: a named entity
  with an explicit, recorded **membership rule** (e.g., "descendants of
  founder X and their spouses; excludes the line that sold out in 1998")
  rather than an implicit surname match. The rule is published in profile
  methodology notes, so inclusion is defensible.
- A family contains **Branches** — descent lines that can hold their own
  companies, properties and estimates. The web branches the way real
  families do.
- **Branch promotion rule:** a branch becomes separately rankable (or a
  new Family) when its wealth is separately attributable AND independently
  managed — its own holding company or family office, distinct control.
  Promotion is an event in the graph, never a rewrite: history before the
  split stays attached to the original family.
- **Marriages connect, never merge.** A marriage between two covered
  families creates an inter-family edge (and possibly shared holdings both
  sides link to); each family keeps its identity. Spouses-in are members
  by the membership rule; their birth-family remains a linked entity.
- **Aggregation is bottom-up.** Wealth attaches to persons and entities at
  the lowest attributable level, then rolls up person → branch → family.
  Any ranking cut — individuals, branches, whole families — is derived
  from the same underlying stakes, so the Wealth 100 (families) and any
  future individuals list can never contradict each other.
- **Death and succession are events.** A founder's death opens an "estate
  of" holding state; distributions move stakes to heirs as they become
  known, each dated and sourced. Succession Watch is literally a query on
  this state.

Precedents to study while refining this: Forbes runs separate families
and individuals lists with different aggregation rules (and its "Richest
Families" aggregation across hundreds of heirs shows the failure mode of
over-broad families); Bloomberg's Billionaires Index mostly refuses family
aggregation (too narrow for our thesis — Caribbean wealth is
family-structured); Hurun's family lists sit between. Our Option C is
designed to support Forbes-style outputs without Forbes-style ambiguity,
because the membership rule is explicit per family.

## 4. Wealth estimation methodology

Rules set once, applied consistently, versioned when they change. This is
what separates the institution from a magazine making guesses.

1. **Valuation date.** One fixed annual valuation date for the flagship
   ranking; all market prices and FX rates as of that date, stated on
   every estimate.
2. **Public holdings.** Disclosed stakes × market price at valuation
   date. Sources: exchange filings (JSE, TTSE, BSE, ECSE, NYSE/NASDAQ for
   diaspora listings), annual reports.
3. **Private companies.** Sector-appropriate comparable multiples
   (EV/EBITDA, revenue, per-room for hotels, per-hectare/buildable-m² for
   land and development) with a conservative bias; the comp set and
   multiple recorded per estimate. Where financials are unavailable,
   triangulate: capacity × market rates, disclosed investment costs,
   competitor benchmarks, credible reporting.
4. **Attributable ownership.** Only the family's attributable share
   counts, traced through holdcos where registries allow. Where the chain
   is opaque, publish a range and record the assumption.
5. **Debt.** Net of known debt; where leverage is unknown, apply stated
   sector-norm assumptions rather than ignoring debt.
6. **Real estate.** Registry values, comparable transactions, or income
   approach for yielding assets; personal-use property included when
   ownership is legitimately public.
7. **Trusts and foundations.** Attribution follows control and benefit:
   revocable/settlor-controlled → attributed; irrevocable charitable →
   excluded from personal wealth (tracked separately under philanthropy);
   ambiguous structures → range + note. Never speculate beyond sources.
8. **Liquidity discounts.** Private, concentrated or hard-to-sell stakes
   carry a documented discount band (indicatively 10–30%) chosen per case
   and recorded.
9. **Currency.** All estimates in USD; conversion at valuation-date rate;
   material local-currency exposure noted (devaluation can move a fortune
   with no business change — say so).
10. **Family aggregation.** Per the §3 model — bottom-up from attributable
    stakes; branch and family cuts derived, never separately invented.
11. **Deceased founders.** Estate state until distribution is evidenced;
    then stakes move to heirs with dates.
12. **Diaspora wealth.** Counted when the person/family qualifies under
    §5; the estimate notes what portion of wealth sits outside the region.
13. **Confidence grades.** Every estimate carries a grade and a range:
    - **A** — majority of value verified from filings/registries/market
      prices;
    - **B** — mix of verified anchors and modeled components;
    - **C** — largely modeled from indirect evidence.
    Publish the grade. Never publish false precision: ranges first, point
    estimates only where grade A/B supports them.
14. **Right of reply.** Families are contacted before first publication of
    an estimate and offered the chance to correct facts annually
    thereafter; responses (or silence) are recorded. Cooperation can
    improve accuracy but NEVER placement — see
    [EDITORIAL_STANDARDS.md](EDITORIAL_STANDARDS.md).

## 5. Defining "Caribbean" — eligibility rules (to ratify before any ranking)

Proposed, for the founder to ratify:

- **Core region:** the island Caribbean — Greater and Lesser Antilles plus
  the Lucayan Archipelago (Bahamas, Turks & Caicos) and the island
  territories (Cayman, USVI/BVI, the French, Dutch and other territories).
  All eight launch markets are core.
- **Mainland CARICOM (Guyana, Suriname, Belize):** culturally Caribbean;
  proposed treatment — eligible for a defined "wider Caribbean" tier and
  business coverage, included in core rankings only if/when coverage depth
  supports it; flagged either way in methodology notes.
- **Bermuda:** Atlantic, not Caribbean; proposed treatment — excluded from
  core rankings, covered under Caribbean-linked/diaspora franchises where
  relevant.
- **Diaspora and multinational families:** a family/person qualifies for
  core rankings when at least one of: (a) primary residence in the region;
  (b) principal operating businesses or the origin of the fortune in the
  region; (c) substantial, continuing regional holdings with
  self-identified Caribbean family identity. Diaspora figures in
  Miami/New York/Toronto/London without qualifying regional ties are
  covered in Achievement & Culture and diaspora franchises — not the
  Wealth 100. For multinational families, only the Caribbean-linked
  branch's attributable wealth enters core rankings, per the §3 branch
  model.
- Whatever is ratified is published in every ranking's methodology note,
  before the first ranking appears.

## 6. Sources and evidence tiers

Tier 1 — registries, court records, exchange and regulatory filings,
government gazettes, land registries.
Tier 2 — audited/company-published information, verified interviews on
record.
Tier 3 — reputable press, trade publications (attributed).
Tier 4 — background interviews, credible unverified reporting → leads
queue or clearly-labeled context, never load-bearing for an estimate.

Starting inventory to build per market (openness varies; verify per
island): companies registries (e.g., DR mercantile registries/ONAPI; PR
Department of State registry plus US SEC for US-listed; Jamaica COJ and
JSE filings; T&T Companies Registry and TTSE; Barbados CAIPO; Bahamas,
Cayman and TCI registries — expect limited public disclosure offshore and
treat those gaps as a known cost), land/property registries, procurement
portals, court systems, exchange disclosures, historical press archives in
English and Spanish. Registry access, cost and disclosure depth per island
is itself a validation-sprint deliverable.

## 7. The validation sprint — 10 families, 4–5 islands

The go/no-go test for the entire thesis, run before naming and branding.

**Selection (founder to pick the names):** 10 families across the DR,
Puerto Rico, Jamaica, Trinidad & Tobago/Barbados and Bahamas/Cayman —
mixing: at least two anchored in listed companies (easier valuation), at
least four fully private, at least one succession-in-progress, at least
one diaspora-linked, at least one with a known branching structure to
stress-test §3.

**For each family, produce:** the full profile to schema — people,
branches, companies, stakes, assets, transactions, philanthropy,
relationships — plus a wealth estimate with range and confidence grade,
and a log of: hours spent, sources used (and refused/paywalled/absent),
data gaps, and the natural story leads that emerged.

**Success criteria (proposed):**

- ≥7 of 10 profiles reach confidence grade B or better on the majority of
  estimated wealth;
- median build time lands within a budget that scales to 100 families with
  a small research team (target: ≤ ~40 research hours per full profile at
  this stage, falling with tooling);
- every profile generates ≥3 publishable story leads (validates the
  journalism↔database flywheel);
- at least one branch-promotion or marriage-connection case is modeled
  cleanly (validates the family web).

**Output:** a validation memo — what worked, what data exists where, gap
map by island, revised time/cost per profile — and the go decision to
proceed to naming, the first 100 families and the first 100 companies.

## 8. Build notes

- The schema is the contract; tooling can start humble. Structured records
  in anything queryable (even disciplined spreadsheets/Airtable-grade) that
  conform to §2 can migrate later into a proper graph or relational store —
  but every record carries dates and sources from day one, or the archive
  value never accumulates.
- Person/company deduplication needs rules early (double surnames, Jr./Sr.,
  homonyms across islands): stable internal IDs, never name-as-key.
- Privacy and safety by design: the internal graph may hold more than we
  publish (per the ownership-metadata rule), but fields that could
  endanger subjects (home addresses, minors' details, security
  information) follow [EDITORIAL_STANDARDS.md](EDITORIAL_STANDARDS.md)
  restrictions in the database itself, not just in print.
