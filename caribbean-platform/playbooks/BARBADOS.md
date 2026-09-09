# Jurisdiction Research Playbook — Barbados

> **Status: draft v2 (2026-09-09).** Template-conformant (see
> [TEMPLATE.md](TEMPLATE.md)). Seeded from the Phase 0 first pass; every
> route needs one live request before this playbook is marked operational.
>
> **Legends.** Access states: **O** obtainable · **I** internal-use ·
> **P** publishable/reusable (each recorded per source — obtainable does
> not imply publishable). **F** = friction 1–5 (1 cheap/easy/fast).
> **Auto** = automation potential H/M/L. **Depth** = historical coverage.
>
> **Standing rule — s.176:** until counsel confirms permitted use, the
> statutory shareholder-list route is a **lead-generation and internal
> verification tool only, never publishable evidence.**

## Route summary

| Route | O | I | P | F | Auto | Depth |
| --- | --- | --- | --- | --- | --- | --- |
| CAIPO free search | ✓ | ✓ | ✓ (bare registry facts) | 1 | M | Online 2021– ; freshness warning |
| CAIPO paid Company Inquiry (~BBD $5) | ✓ | ✓ | ✓ facts; document reuse TBD | 2 | M | TBD |
| BSE + issuer disclosures (ARs, proxies, quarterlies) | ✓ | ✓ | ✓ with attribution | 1 | H | GEL ARs ≥2012 online |
| Companies Act s.176 shareholder list | ✓ likely | ✓ verification only | ✗ pending counsel | 3 | L | Point-in-time snapshots |
| CAIPO charges/mortgages search | ✓ | ✓ | ✓ facts | 2 | M | TBD |
| Land registry (owner-name search) | TBD | TBD | TBD | TBD | TBD | TBD |
| Courts / probate | TBD | TBD | TBD | TBD | TBD | TBD |
| Gazette + press archives | ✓ | ✓ | ✓ with attribution | 2 | M | Deep (paper era TBD) |

## 1. Where to search first

- **Expected outputs:** target entity confirmed (name, number, status,
  dates); latest AR/proxy in hand for listed companies; initial officer
  list.
- **Route:** CAIPO free search → CAIPO paid Company Inquiry → BSE/issuer
  investor pages → gazette/press (Nation News, Barbados Today, Advocate).
- **Failure path:** free DB stale or entity missing → paid inquiry under
  name variants → gazette name-change notices → press archive.

## 2. How to identify a person

- **Expected outputs:** identity anchors (full name with middle
  names/initials, generation suffix, roles with dates, public
  addresses-for-service); internal ID assigned (name-as-key forbidden).
- **Route:** officer lists from company inquiries; AR/proxy director bios;
  press, obituaries, probate notices; professional registries.
- **State:** O/I ✓; P for published facts with attribution.
- **F:** 2 · **Auto:** L · **Depth:** TBD.
- **Failure path:** no reverse person-search at CAIPO (to verify) → work
  company-first: known entities → officers → expand; then press/probate;
  then cross-jurisdiction reverse search (Jamaica-style) where the person
  holds regional roles.

## 3. How to identify their companies

- **Expected outputs:** per-person entity list with roles and dates;
  registered-office/agent clusters flagged as leads.
- **Route:** CAIPO inquiries per known entity; listed-company subsidiary
  lists; registered-office clustering (one law firm's address often
  anchors a family's entities); gazette notices; charge filings naming
  group companies.
- **State:** O/I ✓; P facts.
- **F:** 2–3 · **Auto:** M · **Depth:** TBD.
- **Failure path:** officer-name search unavailable → cluster by
  registered office/agent → charge-filing party names → court records.

## 4. How to pull ownership

- **Expected outputs (per CAIPO Company Inquiry):** entity number, status,
  incorporation date, officers, registered office, filing history,
  charges, and any shareholder data — log immediately when a result
  returns less. **(Listed)** >5% blocks, directors' interests, shares
  outstanding. **(s.176)** full register snapshot: names + holdings.
- **Routes & states:**
  - AR shareholder analysis + directors' interests: O/I/P ✓ (published).
  - BSE disclosures: O/I/P ✓.
  - **s.176 basic list (public companies):** O likely (application to
    company or transfer agent; list made up to ≤30 days prior;
    supplemental lists for changes). **I: verification/leads only. P: ✗
    until counsel** confirms procedure, affidavit wording and permitted
    use (Cap. 308's CBCA lineage suggests a use restriction).
  - Private-company filings/annual returns: contents TBD.
- **F:** 1 (listed) / 3 (s.176) / TBD (private) · **Auto:** H for BSE
  monitoring, L for s.176 · **Depth:** AR series ≥2012 for GEL.
- **Failure path:** no AR table, s.176 unusable → annual returns → charge
  filings (lenders name owners/guarantors) → director/officer overlap →
  court records → cross-border registry handoff.

## 5. How to trace intermediaries

- **Expected outputs:** per intermediary (e.g., Neptune Investments
  Limited): CAIPO record, officers, charges, **entity-status assignment**
  from the taxonomy (operating co / holdco / nominee / trustee /
  foundation / SPV / employee plan / institutional / government / estate /
  unknown) with evidence, and either an ownership conclusion or an
  explicit unknown with a follow-up task.
- **Route:** CAIPO inquiry on the intermediary itself; officer and
  registered-office overlap with known family entities (lead, never
  conclusion); charge filings; press history.
- **State:** O/I ✓; P facts.
- **F:** 2–3 · **Auto:** M · **Depth:** TBD.
- **Failure path:** CAIPO does not reveal the intermediary's owners →
  annual returns → charge filings → director/officer overlap → court
  records → cross-border registry (Panama, BVI… via that jurisdiction's
  playbook). If all fail: status = unknown, documented, with the precise
  limitation recorded.

## 6. How to check property

- **Expected outputs:** parcels/titles per person or entity, transaction
  prices where recorded, encumbrances.
- **Route:** Barbados land registration system — access method, cost, and
  whether owner-name search exists: **TBD (Phase 0 task)**. Interim:
  planning applications, AR property notes, press.
- **State:** TBD.
- **F:** TBD · **Auto:** TBD · **Depth:** TBD.
- **Failure path:** no name search → parcel-first from known addresses →
  planning records → press/AR corroboration.

## 7. How to check charges/debt

- **Expected outputs:** registered charges per entity: lender, date,
  secured assets, amounts where stated (verified-debt inputs for the
  three-state debt rule).
- **Route:** CAIPO charges search (confirmed in principle); listed-company
  debt notes.
- **State:** O/I ✓; P facts.
- **F:** 2 · **Auto:** M (new-charge monitoring) · **Depth:** TBD.
- **Failure path:** nothing registered → AR debt notes → gazette →
  estimated/unknown debt states with range widening.

## 8. How to check courts/probate

- **Expected outputs:** party-name matches, judgments, probate grants and
  estate inventories where public.
- **Route:** Barbados judiciary (barbadoslawcourts.gov.bb) — online
  search availability **TBD**; gazette probate notices as entry point.
- **State:** TBD.
- **F:** TBD · **Auto:** L–M · **Depth:** TBD.
- **Failure path:** no online access → registry visit/agent → gazette
  notices → press coverage of proceedings.

## 9. How to preserve the evidence

- **Expected outputs:** per load-bearing source: original document,
  retrieval date, URL/registry identifier, archive copy/hash where
  legally permissible, passage/page, analyst (methodology §6).
- CAIPO outputs and any s.176 material are **point-in-time records** —
  store the response, request details and date; the register a month
  later is a different document.
- Statute copies preserved: Companies Act Cap. 308 PDFs (CAIPO and
  Barbados Law Courts sites).

## Automation hooks (Daily Wealth Engine ingestion)

Once the baseline graph exists, monitor continuously:

- BSE filings and announcements (substantial holders, results)
- Issuer annual-report/quarterly publication (shareholder analysis and
  directors'-interests diffs year-over-year)
- Director and officer changes (CAIPO status polling — note per-inquiry
  cost in the cost model)
- New registered charges (leverage and deal signals)
- Gazette notices (probate, liquidations, name changes, compulsory
  acquisitions)
- Company-status changes (struck off, restored, amalgamated)
- Press watch (Spanish not required here; regional English dailies)

Each hook emits **proposed claims** into the §9 pipeline — analyst
approval before the graph moves.

## Live-request checklist before marking operational

- [ ] Paid CAIPO Company Inquiry — Goddard Enterprises Limited: record
      fields returned vs. expected outputs, cost, turnaround, format.
- [ ] Paid CAIPO Company Inquiry — Neptune Investments Limited (the
      Profile #1 intermediary).
- [ ] Counsel memo on s.176 → set O/I/P definitively.
- [ ] Land registry: one owner-name search attempt → record method/cost or
      the limitation.
- [ ] Charges search on one known entity.
- [ ] Court/probate access check (one party-name search).
- [ ] Fill every TBD in the route summary from the above.
