# Data Model & Methodology

> **Status: v1.1 (2026-09-09) — founder review applied; the validation
> sprint is now the active workstream** (see
> [VALIDATION_SPRINT.md](VALIDATION_SPRINT.md)). The purpose of this
> document is to prove the central moat can actually be constructed:
> define the claim/family/company/person/asset/transaction model, set the
> wealth-estimation rules, and validate both against ten real Caribbean
> families chosen to stress the model. The abstract design phase is over.
>
> The system in one line:
> **Sources → Claims → Entities → Relationships → Transactions →
> Valuations → Wealth Estimates → Family Profiles → Journalism → Rankings
> → Intelligence** — and journalism feeds new sources and claims back into
> the beginning.

## 1. The conceptual architecture

- **The claim is the data atomic unit; the family page is the editorial
  atomic unit.** Everything the system believes is stored as an auditable
  claim (§2a); the family page is the flagship editorial projection of
  those claims — people, companies, ownership, estimated wealth,
  transactions, properties, philanthropy, relationships and news.
- **The company page is the second editorial atomic unit.** Ownership,
  financials, executives, transactions, subsidiaries, developments and
  related families.
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

### 2a. The claim ledger — the atomic unit of data

Every fact the system holds is a **Claim**:

> **Subject → Predicate → Object/value → Valid-from/valid-to → Source(s) →
> Evidence strength → Analyst → Verification date → Status → Superseded-by**

Example: *Family X → economic ownership → Company Y → 62% → valid from
2019 → [registry filing, annual report] → Tier 1 → analyst MR → verified
2026-03-14 → approved → (later) superseded by claim #4812 (54%)*.

The graph's edges and attributes are **projections of approved claims** —
nothing enters the graph except through a claim. Claim statuses: proposed
→ approved → superseded / retracted. Claims are never deleted: when the
62% stake turns out to be 54% three years later, the ledger shows not just
that the profile once said 62%, but *why we believed it*, which evidence
supported it, when it applied and what superseded it.

This is the audit trail that makes estimates defensible under challenge,
and it is itself a sellable Intelligence asset: professional subscribers
can see the evidentiary basis of every number.

**The Extraction object sits between Source and Claim.** One source
supports many claims, so the exact fragment supporting each claim is
preserved separately: Source → Extraction (page/section, exact passage,
table row/cell, extraction method, verifying analyst, OCR/AI confidence
where applicable) → Claim. When a claim is challenged, the answer is the
fragment — never a reopened 180-page report. A verified extraction
satisfies the evidence-path passage requirement for its source.

**The block invariant (deduplication).** Every countable holding carries
a unique underlying economic block ID, and the same block can never be
counted twice merely because an issuer attributes it to multiple
connected persons. Aggregation without block IDs is refused by the
engine, not discouraged by a note.

Two discipline rules for registry-derived claims:

- **The graph preserves exactly what the registry says.** "Person →
  registered shareholder → Company" is evidence of a registered
  relationship as of a date — not, by itself, of current beneficial
  ownership or an economic percentage. The interpretation is a separate,
  labeled analyst claim built on it.
- **Absence is only what the statute makes it.** A "not found" in a
  beneficial-ownership register never becomes "owns below the threshold"
  unless the regime's actual test (shares / voting rights / control), its
  threshold, its version/date and the search's scope support that
  inference — all of which are recorded on the claim, because BO regimes
  change.

### Nodes

| Entity | Core attributes |
| --- | --- |
| **Claim** | See §2a — subject, predicate, object/value, validity dates, sources, evidence strength, analyst, verification date, status, supersession chain |
| **Person** | Names (incl. Spanish double surnames, maiden names, aliases), birth/death dates, nationality(ies), residence(s), generation marker within family, education, roles (current/past) |
| **Family** | Editorial designation — see §3, the family web. Name, origin island(s), founder(s), membership rule, branches, status (active/dispersed/absorbed) |
| **Branch** | Subdivision of a family: descent line, its own holdings and management (see §3) |
| **Company** | Legal name, trade names, jurisdiction, registry ID, sector, status, financials where available, listing (exchange/ticker) |
| **Asset** | Property (parcel/registry ref where public), hotel, brand, land, vessel/aircraft/art only where legitimately public |
| **Transaction** | Type (acquisition, sale, merger, financing, IPO, liquidation, inheritance/succession), parties, date, value + currency, evidence |
| **Institution** | School, club, hospital, foundation, museum, association |
| **Recognition** | Ranking placements, awards, honors — ours and third parties' — by year |
| **WealthEstimate** | Snapshot per family/branch/person: range (low–high), point estimate optional, valuation date, FX date, evidence confidence + valuation confidence (two dimensions, §4.13), valuation-state mix (§9), methodology version, analyst notes |
| **Source** | Registry filing, court record, exchange filing, press item, interview, company statement — with date, type, reliability tier |

### Edges (all edges carry valid-from / valid-to dates and at least one Source)

| Edge | Between | Notes |
| --- | --- | --- |
| kinship | Person ↔ Person | parent/child, marriage (incl. dissolved), sibling; marriages between covered families are first-class inter-family connections |
| membership | Person → Family/Branch | with role: founder, principal, heir, spouse-in, exited |
| ownership | Person/Family/Company → Company/Asset | **Legal owner ≠ beneficial owner ≠ economic interest ≠ voting/control interest — all four recorded separately**, plus attribution status and evidence basis. Direct or via named intermediary (holdco, trust, foundation). A person may economically own 40%, vote 60%, hold nothing directly, and control the company through another entity — in the offshore Caribbean this distinction is routine, and capturing it is one of the reasons professional subscribers will pay |
| role | Person → Company/Institution | CEO, chair, director, partner, trustee — dated; feeds People & Careers. **A board seat or executive role is never evidence of economic ownership** |
| heritage | Person/Family → Company/Institution | Founder, historical owner, name-origin — a documented founding/historical relationship that implies NO current economic stake. Lets the graph say "Goddard family → founders of → Goddard Enterprises" while current ownership is recorded separately from whoever demonstrably holds it |
| control | Person/Family → Trust/Foundation → holdings | settlor/trustee/beneficiary distinctions matter for attribution (§4) |
| philanthropy | Person/Family/Foundation → Institution | gift, pledge, board seat, patronage |
| affiliation | Person → Institution | education, club membership |
| party-to | Person/Family/Company → Transaction | buyer, seller, lender, advisor |
| coverage | Article → any node | every published story links the nodes it touched — journalism as update mechanism, made literal |

**Temporality is non-negotiable.** Nothing is overwritten: stakes,
roles and estimates are dated intervals, so the graph can be queried "as
of" any year. The longitudinal archive — how ownership and wealth moved
over 5, 10, 20 years — is the part competitors cannot reconstruct later.

**Evidence is fact-level — and the system has two layers.** Every
attribute and edge in the **verified graph** cites its source(s) with a
reliability tier (§6); only verified-graph claims are eligible to support
publication or valuation. Beneath it sits a **research layer** — tips,
hypotheses, unresolved entity matches, potential ownership connections —
where analysts (and AI ingestion, §9) can work without sources being
settled. Research-layer material can NEVER flow automatically into
published products; promotion to the verified graph happens only through
an approved claim.

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
4. **Attributable ownership — traverse, don't stop.** Only the family's
   attributable share counts, traced through intermediaries. A registered
   holder is the next node, not the end: a holdco stake is calculated
   through the chain when the chain leads to the family; not attributed
   when it leads to unrelated institutions; investigated for beneficial
   interest when it is a nominee; and where beneficial-ownership access is
   legally restricted, the precise limitation is recorded rather than the
   question treated as unknowable. Where the chain is opaque, publish a
   range and record the assumption.
5. **Debt — three states, stored distinctly.** **Verified debt** (filings,
   registries, disclosed facilities), **estimated debt** (reported or
   modeled, labeled as such) and **unknown debt**. Estimates net verified
   and clearly-labeled estimated debt. Sector-leverage norms may inform
   the scenario range but are never recorded as if they were fact — and
   where unknown debt could materially affect the result, widen the
   published range rather than inventing a deduction.
6. **Real estate.** Registry values, comparable transactions, or income
   approach for yielding assets; personal-use property included when
   ownership is legitimately public.
7. **Trusts and foundations.** Attribution follows control and benefit:
   revocable/settlor-controlled → attributed; irrevocable charitable →
   excluded from personal wealth (tracked separately under philanthropy);
   ambiguous structures → range + note. Never speculate beyond sources.
8. **Marketability and control adjustments — never automatic.** Applied
   only when justified by the valuation method and the specific holding.
   A blanket private-company discount double-counts whenever the
   comparable transactions or multiples already embed illiquidity. Any
   discount or premium must be explicitly recorded with its rationale and
   cannot duplicate an adjustment already embedded in the comparable
   valuation.
9. **Currency.** All estimates in USD; conversion at valuation-date rate;
   material local-currency exposure noted (devaluation can move a fortune
   with no business change — say so).
10. **Family aggregation.** Per the §3 model — bottom-up from attributable
    stakes; branch and family cuts derived, never separately invented.
11. **Deceased founders.** Estate state until distribution is evidenced;
    then stakes move to heirs with dates.
12. **Diaspora wealth.** Counted when the person/family qualifies under
    §5; the estimate notes what portion of wealth sits outside the region.
13. **Confidence — two dimensions, never one grade.** A single grade hides
    the difference between knowing what a family owns and knowing what it
    is worth. Every estimate carries both:
    - **Evidence confidence** (High / Moderate / Low): how certain are we
      about ownership, assets and debt?
    - **Valuation confidence** (High / Moderate / Low): how certain are we
      about what those holdings are worth?
    A family can have excellent evidence of 70% ownership and poor
    private-company financial disclosure — say so. Published form:
    *US$420–520M — ownership evidence: High; valuation confidence:
    Moderate.* Never publish false precision: ranges first, point
    estimates only where both dimensions support them.
14. **Right of reply.** Families are contacted before first publication of
    an estimate and offered the chance to correct material facts before
    each ranking's valuation date; responses are recorded. Subjects are
    never shown final ranks, competitors' estimates, scores or unpublished
    ranking results. Cooperation can improve accuracy but NEVER placement —
    see [EDITORIAL_STANDARDS.md](EDITORIAL_STANDARDS.md).
15. **Methodology-change governance.** Methodology versions are published;
    a change (say, v1.4 altering treatment of private-company control
    premiums) is announced and explained, never applied silently. History
    is never rewritten: original-vintage estimates are preserved as
    published ("2029 fortune under 2029 methodology: $600–750M"), with any
    recast series under current methodology shown alongside, clearly
    labeled — both series preserved.

16. **Freshness is separate from validity.** *Facts can be true as of a
    date without being currently verified.* A point-in-time disclosure
    (an annual-report shareholding, a price, an FX rate) is valid as of
    its date — never "current forever" — and carries a computed
    freshness state: **current / aging / stale / superseded**, with
    thresholds by claim type (indicative: market prices age in a day and
    go stale in a week; listed shareholdings age after 90 days and go
    stale after 365 unless refreshed by filings; roles are slower).
    Freshness is derived at read time, never stored as fact, and the
    Daily Wealth Engine displays it on every input it uses. **A stale
    mark never invalidates an approved ownership chain**: ownership
    approval and mark freshness are independent — the block can be
    APPROVED while its daily valuation waits on a current price.

### Influence is never derived from wealth

Stated now, before either index exists: **net worth is not an input that
converts into an influence score.** Influence gets its own methodology on
its own dimensions — corporate reach, employment and economic footprint,
institutional positions, philanthropy, cultural reach, cross-island
presence and demonstrated network significance. Wealth and influence will
correlate in reality; the methodologies must remain independent, or the
Influence 50 eventually becomes the Wealth 100 in a different order and
one of the two franchises is redundant.

## 5. Defining "Caribbean" — eligibility rules (to ratify before any ranking)

Proposed, for the founder to ratify:

The coverage universe is defined institutionally, not purely
geographically, in two tiers:

- **Core Caribbean:** the sovereign states and territories conventionally
  regarded as Caribbean — the island Caribbean (Greater and Lesser
  Antilles, the Lucayan Archipelago, and the island territories: Cayman,
  USVI/BVI, the French, Dutch and other territories) — **including the
  CARICOM mainland members Guyana, Suriname and Belize from the
  beginning**, with methodology identifying island Caribbean and mainland
  Caribbean where relevant. Guyana in particular is too important to
  Caribbean capital — CARICOM membership, a rapidly transforming energy
  economy — to relegate to a secondary tier; core status also avoids the
  future absurdity of an enormous Guyanese fortune being ineligible for a
  list purporting to describe Caribbean wealth. All eight launch markets
  are core.
- **Caribbean Capital Network:** the core region **plus Panama and other
  external financial/business hubs when materially connected to Caribbean
  capital** — banking, shipping, logistics, corporate structures, real
  estate, family offices, cross-border wealth. Panama is in the database
  from Day 1 (tracing Caribbean ownership will surface Panamanian entities
  whether we intend it or not), and Panamanian families can carry their own
  Panama coverage and eventually a broader Caribbean & Central American
  Capital product. But a purely Panamanian fortune with no Caribbean
  connection does not enter the flagship Caribbean Wealth 100 — the
  definition of "Caribbean" is never distorted to admit it.
- **Bermuda:** Atlantic, not Caribbean; proposed treatment — excluded from
  core rankings, covered under Caribbean-linked/diaspora franchises and the
  Capital Network where relevant.
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

**Coverage tiers follow evidence, not ambition.** Jurisdictional
disclosure quality varies enormously (see
[DATA_ACCESS_MAP.md](DATA_ACCESS_MAP.md)), so the institution does not
pretend to launch every country at equal depth. **Tier 1 coverage
markets** carry deeply modeled, continuously updated fortunes; **Tier 2
coverage markets** carry less complete estimates, explicitly labeled as
such. A $900M estimate in an opaque jurisdiction and a $900M estimate in
a rich-disclosure jurisdiction do not have equivalent evidentiary
foundations, and the product never implies they do. A market's tier is
set by its Data Access Map row and can rise as access improves.

## 6. Sources and evidence tiers

Tier 1 — registries, court records, exchange and regulatory filings,
government gazettes, land registries.
Tier 2 — audited/company-published information, verified interviews on
record.
Tier 3 — reputable press, trade publications (attributed).
Tier 4 — background interviews, credible unverified reporting → leads
queue or clearly-labeled context, never load-bearing for an estimate.

**"Not readily Googleable" is not the same thing as "not public."** The
raw material lives in corporate registries, shareholder registers,
securities filings, proxy circulars, land registries, mortgage/charge
registries, court records, probate/estate filings, government gazettes,
procurement databases, planning/development records, incorporation
documents and historical filings — fragmented, expensive, multilingual and
tedious to assemble. Assembling it into the living ownership graph is the
moat. What each jurisdiction actually provides, under what legal basis and
at what cost, is mapped in [DATA_ACCESS_MAP.md](DATA_ACCESS_MAP.md) —
Phase 0 of the validation sprint, completed before the family deep dives.

**Source-document preservation (the 20-year rule).** Web pages disappear,
registries change systems, companies delete annual reports — and in 2038
someone may challenge why we estimated their family at $680M in 2029.
Every load-bearing source therefore preserves: original document →
retrieval date → URL/registry identifier → archive copy or hash where
legally permissible → the relevant passage/page → the analyst who reviewed
it. A consequential claim must be reconstructable from its preserved
evidence years later, without depending on the live web.

Starting inventory to build per market (openness varies; verify per
island): companies registries (e.g., DR mercantile registries/ONAPI; PR
Department of State registry plus US SEC for US-listed; Jamaica COJ and
JSE filings; T&T Companies Registry and TTSE; Barbados CAIPO; Bahamas,
Cayman and TCI registries — expect limited public disclosure offshore and
treat those gaps as a known cost), land/property registries, procurement
portals, court systems, exchange disclosures, historical press archives in
English and Spanish. Registry access, cost and disclosure depth per island
is itself a validation-sprint deliverable.

## 7. The validation sprint — deliberately trying to break the model

The go/no-go test for the entire thesis, run before naming and branding.
The roster, protocol and running log live in
[VALIDATION_SPRINT.md](VALIDATION_SPRINT.md).

**The exercise is not "estimate the wealth of these ten families." It is:
determine what these ten families actually own today, then determine
whether a defensible wealth estimate follows.** Ownership first, valuation
second — a family's conventional reputation is a hypothesis, never an
input. Some supposedly major families may have sold down decades ago while
obscure holding companies or other families actually own the capital
today; discovering that is the product working, and the editorial output
("Who owns X today?") is often stronger than the fortune piece would have
been.

**We are testing where the product breaks, not trying to collect ten
passing grades.** The ten families are chosen as stress cases, not
conveniences:

| Stress case | Why |
| --- | --- |
| Listed-company dynasty | Establish the easy baseline |
| DR private conglomerate | Spanish-language, private-company research |
| Jamaican listed/private hybrid | Mixed valuation |
| Trinidad industrial family | Conglomerate complexity |
| Bahamian private family | Disclosure scarcity |
| Cayman-linked structure | Offshore opacity |
| Guyanese emerging fortune | Rapidly changing wealth |
| Succession case | Estate/inheritance mechanics |
| Multi-branch dynasty | Family boundary test (§3) |
| Diaspora-linked family | Eligibility/attribution test (§5) |

If the Cayman case proves almost impossible, that is a finding, not a
failure.

**For each family, produce:** the full profile to schema — people,
branches, companies, stakes (legal/beneficial/economic/voting), assets,
transactions, philanthropy, relationships — as approved claims with
preserved sources; a wealth estimate with range and both confidence
dimensions; and a log of hours spent, sources used (and
refused/paywalled/absent), data gaps, and the natural story leads that
emerged.

**Every case lands in one of four legitimate outcomes — all four are
successful database outcomes:**

1. **Rankable** — ownership and valuation sufficiently attributable.
2. **Rankable with wide range** — economic ownership reasonably
   established but valuation uncertain.
3. **Known but presently unrankable** — evidence insufficient for a
   responsible fortune estimate.
4. **Historical/influential, not economically rankable** — popular
   perception of family ownership isn't supported by current evidence;
   the graph records the heritage relationship and, separately, whoever
   demonstrably owns the capital today.

**Primary KPI: for at least 8 of 10 cases, the research process reaches a
defensible ownership conclusion — rankable, unrankable, historical or
unresolved — and documents why.** This tests whether we can build the
Caribbean wealth graph, not merely whether we can manufacture a Caribbean
rich list. We do not require any minimum count of high-confidence wealth
estimates — that incentivizes analysts to become overconfident. Where an
estimate is produced, the standard is **defensible uncertainty**: a
genuinely researched *US$300–600M — valuation confidence: Low* is a
successful research product if we can explain precisely why the range
cannot responsibly be narrowed. That explanation is part of the
institution's credibility.

Secondary measurements (learning metrics, not pass/fail): research hours
per profile (does this scale to 100 families with a small team?); story
leads per profile (does the journalism↔database flywheel turn?); whether
the branch/marriage cases model cleanly in §3's structure.

**And the reproducibility test, applied to every completed profile:
could another competent researcher reproduce our conclusion from our
evidence trail?** If yes, the methodology is validated in that market.
If no, the profile is not done, whatever its confidence labels say.

**Output:** a validation memo — what worked, what broke, what data exists
where, gap map by island, revised time/cost per profile — and the go
decision to proceed to naming, the first 100 families and the first 100
companies.

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

## 9. Continuous Valuation Engine & Daily Wealth Index

The graph makes possible something no annual list can be: **a living
financial model of Caribbean family wealth that reacts to markets,
ownership disclosures, transactions and regulatory filings as they
happen.** This is the signature product that turns the company from a
media startup into an information company — the Bloomberg Billionaires
Index model, applied where Bloomberg doesn't systematically go.

The engine's valuable intellectual property is not the arithmetic —
computers multiply a stock price by 44.43% effortlessly. It is
**establishing that 44.43% is actually the correct attributable economic
interest, and continuously monitoring that it stays correct.** Once the
ownership graph is established and maintained, everything downstream
becomes dramatically easier.

### The public product

Daily estimated wealth of the Caribbean's major business families:

| Rank | Family | Country | Fortune | Today | YTD |
| --- | --- | --- | --- | --- | --- |
| 1 | Family A | DR | $4.82B | +$73M | +8.4% |
| 2 | Family B | Jamaica | $2.16B | −$41M | +2.1% |
| 3 | Family C | Trinidad | $1.74B | +$12M | −3.7% |

Every daily change is clickable and decomposes into its audit trail:

> +$73M today = Public Company A +4.1% → +$51M · Public Company B +1.7% →
> +$18M · USD/DOP movement → +$4M · private holdings → model-held.

That decomposition is the difference between clickbait ("Family X made
$73 million today") and a **mark-to-model estimate with an audit trail.**

Per-family history charts: 1D | 1M | YTD | 1Y | 5Y | MAX.

The graph's public face is the **interactive relationship map** on every
family, company, property and institution page — approved claims only,
unknowns rendered honestly, restricted fields never rendered (see
[DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md)).

### How the engine works

- **Graph traversal for attributable value.** The family owns 62.4% of
  HoldCo A, which owns 71.2% of Listed Company B → effective economic
  interest 44.43%. The engine computes attributable stakes by traversing
  verified ownership claims (economic interest, not voting interest, for
  valuation), then marks them against market feeds.
- **Every fortune component carries a valuation state:**

| State | Meaning |
| --- | --- |
| LIVE | Publicly traded / security-priced |
| FX-LINKED | Recalculated from currency movements |
| MODELLED | Private-company valuation (§4), periodically refreshed |
| TRANSACTION-MARKED | Latest financing/acquisition establishes the mark |
| PROPERTY-MARKED | Valuation/index/comparable based |
| STALE | Insufficient recent evidence |
| UNDER REVIEW | Material new information detected |

- **Transparency of the mix is mandatory in the UI:** *"Estimated fortune:
  $2.84B · Daily change: +$31M (+1.1%) · 43% of estimated wealth marked to
  live market prices; remaining assets use periodically updated
  private-market estimates."* A $2.84B fortune where only $1.2B is
  observable is not worth $2.84B to the nearest $10M, and the product must
  visually say so. Private companies do not pretend to change value daily.

### The ingestion pipeline

Continuous monitoring of regulatory and primary sources: SEC, Jamaica
Stock Exchange, Trinidad & Tobago Stock Exchange, Barbados Stock Exchange,
Eastern Caribbean Securities Exchange, Puerto Rico/US disclosures, company
registries, annual reports, material-change announcements, insider
filings, prospectuses, M&A filings, court records, government gazettes.

> **Source detected → document parsed → entities resolved → claims
> extracted → graph impact calculated → confidence assigned → analyst
> review → graph updated → wealth recalculated → story suggested**

Worked example: a filing shows a family-controlled vehicle disposed of
2.4M shares. The system creates a **proposed claim** — *Family → economic
ownership → Company X → 31.7% → proposed 29.9% · Source: regulatory filing
· Tier 1 · Confidence: High* — and computes the impact (attributable value
$481M → $454M, estimated fortune −$27M). **An analyst approves the graph
change.** Then the index updates, and the CMS generates a story lead:
*"Family X's stake in Company Y falls following $27 million share
disposal."* The flywheel becomes almost mechanical.

**Automation tiers.** Closing market prices and FX: automatic — the
underlying ownership claim was already verified. A filing that alters
beneficial interests through Trust A → Foundation B → HoldCo C: human
review, always. AI is used aggressively for detection, parsing, entity
resolution and impact calculation — and never allowed to move a published
fortune by $400M on an unverified interpretation. (Binding rules in
[EDITORIAL_STANDARDS.md](EDITORIAL_STANDARDS.md), AI section.)

### Editorial products the engine generates

Daily: Biggest Wealth Gainers • Biggest Wealth Decliners • Largest YTD
Gains • New Highs • New Billionaires • Fortunes Under Review • Major
Ownership Changes — plus alerts: *"WEALTH WATCH — Jamaica: the estimated
fortune of Family X rose approximately $86M today after shares in its
principal listed holding gained 7.2%,"* with the calculation one click
away. Habit-forming in a way an annual rich list is not.

### What Intelligence subscribers get

Not just "Family X ≈ $1.8B" but: current estimate • defensible range •
valuation-state mix (e.g., 37% live-priced, 41% privately modeled, 15%
property, 7% other) • currency exposure • the ownership graph • valuation
history • source documents • material filings • alerts • transactions •
related families • board relationships. A professional product.

### The three publication surfaces

The same graph feeds three deliberately different surfaces:

1. **Public publication** — narrative, approved facts only, ranges,
   accessible methodology.
2. **Intelligence product** — deeper ownership trees, historical
   estimates, valuation components, sources, confidence dimensions,
   downloadable data.
3. **Analyst environment** — claims, source and extraction IDs, evidence
   paths, rejected/superseded claims, unresolved leads, provenance,
   internal notes, the research queue.

The analyst environment is allowed to be technical; the public surface
never is. An internal preview is an analyst-surface artifact and is
labeled as such.

### The two-product rule

- **The annual Wealth 100** is authoritative and deliberately slow: deep
  research, fixed valuation date, right of reply.
- **The Daily Wealth Index** is dynamic and explicitly mark-to-model: the
  best current estimate given live markets and the latest verified
  information.

**Never silently substitute one for the other.** Each is labeled as what
it is, everywhere it appears.
