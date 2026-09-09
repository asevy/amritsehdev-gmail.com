# Jurisdiction Research Playbook — Jamaica

> **Status: draft v1 (2026-09-09).** Template-conformant (see
> [TEMPLATE.md](TEMPLATE.md)). Seeded from the Phase 0 first pass (COJ,
> BO Registry, JSE — sourced) plus training-knowledge leads marked
> *verify*. Jamaica is the highest-access market found so far — the best
> candidate to prove the full graph methodology end-to-end.
>
> **Legends.** **O** obtainable · **I** internal-use · **P**
> publishable/reusable (per source; obtainable ≠ publishable). **F**
> friction 1–5 (1 = cheap/easy/fast) · **Auto** H/M/L · **Depth**
> historical coverage.
>
> **Standing legal rule:** the Beneficial Ownership Registry is
> subscriber-gated — its terms of use decide the P state; until reviewed,
> BO-registry output is **I-only**.

## Route summary

| Route | O | I | P | F | Auto | Depth |
| --- | --- | --- | --- | --- | --- | --- |
| COJ entity search (account, free basic) | ✓ | ✓ | ✓ facts | 1 | M–H | TBD |
| COJ reverse person search (director/shareholder/secretary → entities) | ✓ | ✓ | ✓ facts | 1–2 | H — graph-native | TBD |
| Beneficial Ownership Registry (subscriber, ≥25%) | ✓ | ✓ | TBD — terms review | 2 | M | Recent regime; start date to verify |
| JSE disclosures + issuer annual reports | ✓ | ✓ | ✓ with attribution | 1 | H | Years of ARs online; verify span |
| COJ annual returns / filed documents | TBD — contents to verify | TBD | TBD | TBD | TBD | TBD |
| NLA title search (eLand) | likely O — *verify* | TBD | TBD | 2? | M? | TBD |
| Charges via COJ | *verify* | TBD | TBD | TBD | TBD | TBD |
| Courts / probate (Supreme Court; gazette notices) | partial — *verify* | TBD | TBD | TBD | L–M | TBD |
| RGD civil records (births/marriages/deaths — kinship evidence) | O with fees — *verify* | ✓ | restraint per standards | 2–3 | L | Deep |
| Gleaner/Observer press archives | ✓ | ✓ | ✓ with attribution | 1–2 | M | Gleaner archive reputedly very deep — *verify span* |

## 1. Where to search first

- **Expected outputs:** entity confirmed (name, number, type, status,
  officers); person's entity affiliations; latest AR for listed
  companies.
- **Route:** COJ (orcjamaica.com) entity search → **reverse person
  search** → JSE issuer page and AR → BO Registry (subscriber) → press.
- **Failure path:** name variants and aliases → press archive → gazette.

## 2. How to identify a person

- **Expected outputs:** person → all registered affiliations (director /
  shareholder / secretary) with entity details; identity anchors;
  internal ID.
- **Route:** COJ reverse person search — the graph-native primitive that
  makes Jamaica special; corroborate identity via AR bios, press, RGD
  records where kinship must be evidenced (subject to the minors and
  privacy rules).
- **F:** 1–2 · **Auto:** H · **Depth:** TBD.
- **Failure path:** common-name collisions → disambiguate by co-officer
  patterns, addresses-for-service, entity sectors; then press.

## 3. How to identify their companies

- **Expected outputs:** complete per-person entity list with roles; group
  structure sketch; registered-office clusters.
- **Route:** reverse search output → per-entity COJ records → JSE
  subsidiary lists → BO Registry per entity.
- **F:** 1–2 · **Auto:** H · **Depth:** TBD.
- **Failure path:** entities held via non-Jamaican holdcos → cross-border
  handoff (playbook of that jurisdiction; Panama/BVI likely).

## 4. How to pull ownership

- **Expected outputs:** **(Listed)** substantial/top shareholder tables —
  Jamaican issuer ARs commonly disclose top-10 shareholder lists
  (*verify per issuer*: e.g., Wisynco, NCB Financial, Seprod), directors'
  interests, shares outstanding. **(BO Registry)** beneficial owners at
  ≥25% (shares, votes or other control). **(COJ)** share
  capital/member data in annual returns — contents *to verify*.
- **States:** AR/JSE: O/I/P ✓. BO Registry: O/I ✓, **P TBD (terms
  review)**. Annual returns: TBD.
- **F:** 1 (listed) / 2 (BO) · **Auto:** H (JSE), M (BO re-checks) ·
  **Depth:** AR series spans to verify.
- **Failure path:** below-threshold or dispersed holdings → top-10 tables
  year-over-year (sell-down tracing) → charge filings → court records →
  cross-border registries.

## 5. How to trace intermediaries

- **Expected outputs:** per intermediary: COJ record, officers, BO-
  registry answer, entity-status assignment (taxonomy) with evidence, or
  documented unknown.
- **Route:** reverse-search the holdco itself; BO Registry on the holdco;
  officer/registered-office overlap as leads.
- **F:** 2 · **Auto:** M–H · **Depth:** TBD.
- **Failure path:** offshore parent → cross-border handoff; nominee
  suspicion → BO Registry answer vs. registered holder mismatch is
  itself evidence — record both.

## 6. How to check property

- **Expected outputs:** titles per person/entity, transfer history,
  consideration where recorded, encumbrances.
- **Route:** National Land Agency title search (eLand) — *verify* current
  online access, per-search cost, owner-name searchability.
- **F/Auto/Depth:** TBD.
- **Failure path:** no name search → parcel-first from known addresses →
  planning records → press.

## 7. How to check charges/debt

- **Expected outputs:** registered charges per entity (lender, date,
  secured assets) — verified-debt inputs.
- **Route:** COJ charge filings (*verify*); listed-company debt notes.
- **F/Auto/Depth:** TBD.
- **Failure path:** nothing registered → AR notes → estimated/unknown
  debt states, range widened.

## 8. How to check courts/probate

- **Expected outputs:** party-name judgments, probate grants (succession
  evidence — directly relevant to the Stewart case).
- **Route:** Supreme Court published judgments (*verify* search), probate
  registry, gazette notices, press coverage of proceedings.
- **F/Auto/Depth:** TBD.
- **Failure path:** no online access → registry/agent → press.

## 9. How to preserve the evidence

- Standard preservation record per methodology §6. BO Registry and COJ
  outputs are **point-in-time documents** — store response, query, date.
  Respect the BO Registry's terms in what is stored vs. republished
  (P state pending).

## Automation hooks (Daily Wealth Engine ingestion)

- JSE announcements/filings feed (results, substantial-holder notices,
  insider dealings)
- Issuer AR publication watch → year-over-year top-10 shareholder diffs
- BO Registry re-checks on tracked entities
- COJ status/officer-change monitoring
- New charge registrations
- Gazette notices (probate, liquidations)
- NLA transfer monitoring (*if feasible*)
- Press watch (Gleaner, Observer, Loop)

Each hook emits proposed claims into the §9 pipeline — analyst approval
before the graph moves.

## Live-request checklist before marking operational

- [ ] COJ account + one reverse person search — record fields, cost,
      format vs. expected outputs.
- [ ] BO Registry subscription + one query — record fields and **review
      terms of use → set the P state**.
- [ ] Verify top-10 shareholder disclosure practice across 3 issuer ARs
      (Wisynco, NCB Financial, Seprod).
- [ ] One COJ annual-return/document pull — what do returns disclose?
- [ ] One NLA title search — method, cost, owner-name searchability.
- [ ] One charges search; one probate/judgment search.
- [ ] Fill every TBD in the route summary.
