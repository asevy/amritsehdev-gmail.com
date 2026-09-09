# Data Access Map — Phase 0 of the Validation Sprint

> **Status: OPEN (2026-09-09) — precedes the ten-family deep dives.** A few
> days of focused work determining exactly what can legally be obtained in
> every launch jurisdiction: under what legal basis, by whom, how (online /
> in person / through an agent), at what cost, with what turnaround, how
> far back the records go, and with what restrictions on use. This map is
> the actual research architecture of the company. First-pass cells below
> were seeded by open-web research on 2026-09-09 (sources preserved in the
> per-market notes); every cell needs confirmation with local counsel or a
> live request before it is relied on.

## Why this is the moat

**"Not readily Googleable" is not the same thing as "not public."** The
information exists in corporate registries, shareholder registers,
securities filings, proxy circulars, land registries, mortgage/charge
registries, court records, probate/estate filings, government gazettes,
procurement databases, planning/development records, incorporation
documents and historical filings. Nobody has assembled it into:

> Person → Family → HoldCo → Company → Asset → % economic interest →
> current valuation.

The moat may not be secret information at all. It is public information
that is **fragmented, expensive, multilingual, historical and tedious to
assemble — organized into a living Caribbean ownership graph.** That is an
extremely defensible information business if the underlying records are
sufficiently rich; this map establishes whether they are.

## The standard escalation ladder (per listed/large company)

1. Exchange disclosures (substantial holders, insider filings)
2. Annual report / proxy circular (shareholder analyses, directors'
   interests)
3. Statutory shareholder-list routes (e.g., Barbados Companies Act s.176)
4. Registry company search (officers, filings, charges)
5. Intermediary/holding-company identification
6. Beneficial-ownership tracing (or a precise record of why access is
   restricted)
7. Land, charges, courts, probate, gazettes, procurement, planning

## The intermediary rule (the Neptune method)

A registered holder is the **next node, not the end.** "Neptune
Investments Ltd — 13.9%" means: who owns Neptune?

- Family members → HoldCo → Neptune → target: **calculate through the
  chain.**
- Neptune owned by unrelated institutions: **do not attribute** to the
  family.
- Nominee structure: **investigate the beneficial interest**; never assume
  the registered holder is the economic owner.
- Public shareholder list but restricted beneficial-ownership access:
  **record precisely that limitation** rather than treating the ownership
  question as unknowable.

## Master table

Legend: ✓ = confirmed first-pass · ◐ = partial/limited · ✗ = restricted ·
R = research needed

| Market | Company registry | Shareholder register access | Beneficial owners | Land/property | Charges/debt | Courts | Securities |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Barbados | ✓ CAIPO: free limited name search; paid Company Inquiry (~BBD $5); online since 2021 | ◐ s.176 "basic list of shareholders" route for public companies — conditions to verify | ◐ Records must be maintained; access route to map | R | ✓ CAIPO notes registered mortgages/charges searchable | R | BSE + issuer sites (2025 AR, quarterlies confirmed available) |
| Jamaica | ✓ COJ (orcjamaica.com): account-based free entity search; officer details | ✓ Reverse search by shareholder/director/secretary, incl. their other affiliations | ◐ Subscriber Beneficial Ownership Registry, ≥25% threshold | R | R | R | JSE disclosures |
| Dominican Republic | ◐ Registro Mercantil via chambers of commerce (Cámara Santo Domingo portal, 24/7 consultas); RNC lookup via DGII | R — depth of filed acts (statutes, assemblies, share transfers) via chamber services to map | R | R | R | R | — (no active exchange of consequence; bond filings via SIMV to check) |
| Trinidad & Tobago | R — Companies Registry | R | R | R | R | R | TTSE disclosures |
| Guyana | R — Commercial Registry | R | R | R | R | R | GSE (small) |
| Bahamas | R — Registrar General | R | R | R | R | R | BISX |
| Cayman | ◐ Cayman Business Portal: pay-per-search; basic details + directors | ✗ Shareholders largely not public | ✗ BO register (mandatory since July 2024) confidential; legitimate-interest access only, tied to ML/TF evidence | ◐ Land registry + planning records to map — likely the richest public route | R | R | CSX (minor) |
| Turks & Caicos | R — Financial Services Commission registry | R | R | R | R | R | — |
| Puerto Rico | ◐ Departamento de Estado corporations registry | R | R | ◐ CRIM property records to map | R | Federal PACER + PR courts | SEC/EDGAR for US-listed |
| Panama | R — Registro Público | R | R | R | R | R | Latinex |

## Per-market first-pass notes (2026-09-09)

**Barbados.** The Companies Act (Cap. 308) contains s.176 "Basic list of
shareholders" — heading confirmed in the official Act's arrangement of
sections; the founder's reading: any person can apply to a public company
or its transfer agent for a list of shareholder names and holdings made up
to ≤30 days before the request, with supplemental lists for changes.
Official Act PDFs preserved (CAIPO and Barbados Law Courts sites). **Counsel
question before relying on it editorially:** Cap. 308 descends from the
Canada Business Corporations Act model, where the equivalent provision
requires an affidavit and restricts use of the list to matters relating to
the affairs of the corporation — verify whether Barbados imposes a
permitted-use restriction and whether journalistic/data use is compatible.
CAIPO free search is limited (names, numbers, dates) and one source warns
the free database is not regularly updated; the paid Company Inquiry is
the real record.

**Jamaica — unusually research-rich.** COJ's portal supports reverse
search: find a person and see the entities where they are director,
shareholder or secretary — a graph-builder primitive most registries lack.
A separate subscriber Beneficial Ownership Registry covers beneficial
owners at the 25% threshold (shares, voting rights or other control), with
COJ empowered to verify submissions. Implication: the three Jamaica-linked
sprint cases (Mahfood, Stewart, Lee-Chin) may be substantially more
tractable than assumed, and Jamaica is the best candidate for proving the
full graph methodology end-to-end.

**Dominican Republic.** The Registro Mercantil is decentralized through
the chambers of commerce (Santo Domingo chamber runs a 24/7 online
consulta for status/validity; document-level services exist beyond it);
company formation touches ONAPI (trade names) and DGII (RNC — free
lookup). To map: what filed corporate documents (statutes, assembly
minutes, share transfers) a non-party can obtain from the chamber, cost
and language/legalization requirements.

**Cayman — opacity confirmed, as the stress case intended.** Company
search is pay-per-search with basic details and directors; shareholders
are largely not public; the beneficial-ownership register that all Cayman
companies must maintain since July 2024 is confidential, with
legitimate-interest access narrowly tied to money-laundering/terrorism
evidence. The Dart profile will therefore lean on land/planning records,
press, litigation and non-Cayman filings — and its primary output may be
the precise documentation of what cannot be known, which is itself
Intelligence product content.

**Still to research from scratch:** Trinidad & Tobago, Guyana, Bahamas,
Turks & Caicos, Puerto Rico (registry depth), Panama — same template:
registry access, shareholder routes, BO regime, land, charges, courts,
gazettes, historical depth, cost.

## How the map feeds the sprint

- Execution order of the ten profiles may be re-sequenced by access
  reality (Jamaica up, Cayman explicitly framed as a
  document-the-limitation case).
- Each market's completed row becomes the research playbook and cost model
  for the first 100 families.
- Access regimes change (Cayman's BO regime changed in 2024; Jamaica's BO
  registry is recent): the map needs a standing watch that flags new
  registry access or filing requirements as they emerge — a natural
  recurring monitoring task.
