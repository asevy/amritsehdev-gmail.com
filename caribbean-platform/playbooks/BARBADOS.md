# Jurisdiction Research Playbook — Barbados

> **Status: draft v1 (2026-09-09).** Seeded from the Phase 0 first pass;
> every step needs live confirmation (one real request per route) before
> this playbook is marked operational. Legal questions flagged inline go
> to Barbados counsel. Access states: O = obtainable, I = internal-use,
> P = publishable/reusable — see
> [../DATA_ACCESS_MAP.md](../DATA_ACCESS_MAP.md).

## 1. Where to search first

1. **CAIPO** (caipo.gov.bb) — free limited search for entity names,
   registration numbers, dates (freshness warning on the free database);
   the paid **Company Inquiry** (~BBD $5) is the real record. Online
   registry since 2021.
2. **BSE + issuer investor pages** for listed companies — annual reports,
   proxy circulars, quarterly results (GEL's 2025 AR and 2026 quarterlies
   confirmed available).
3. **Official gazette and press archives** (Nation News, Barbados Today,
   Advocate) for appointments, transactions, obituaries.

## 2. How to identify a person

- No confirmed reverse person→entities search at CAIPO (unlike Jamaica) —
  identification runs through: directorships in company inquiries, annual
  report/proxy disclosures, professional registries, press archives,
  obituaries and probate notices.
- Disambiguation: middle names/initials, generation suffixes, board
  affiliations; assign internal IDs immediately (name-as-key forbidden).
- To verify: whether CAIPO paid searches can be run against an officer
  name rather than an entity name.

## 3. How to identify their companies

- CAIPO Company Inquiry per known entity; harvest officers, registered
  office, status, filing history.
- Cross-reference: annual reports of listed companies (subsidiary lists),
  registered-office clustering (one law firm's address often anchors a
  family's entities), gazette notices, charge filings naming group
  companies.
- To verify: whether CAIPO inquiry output includes shareholders for
  private companies or only directors; cost and format of full filing
  copies.

## 4. How to pull ownership

- **Listed companies:** annual report shareholder analysis (>5% blocks),
  directors' interests tables, proxy circulars; BSE disclosures.
- **The s.176 route (public companies):** Companies Act Cap. 308, s.176
  "Basic list of shareholders" — per founder's legal research, any person
  may apply to the company or its transfer agent for a list of
  shareholders (names, holdings) made up to ≤30 days before the request,
  with supplemental lists for changes. **State: O (likely). I and P: TBD —
  Cap. 308 follows the CBCA model, where the equivalent provision
  requires an affidavit and restricts use to matters relating to the
  corporation's affairs. Counsel must confirm: exact procedure, fee,
  affidavit wording, and whether research/publication use is compatible.
  Until then: the route may inform where we look (leads), but nothing
  obtained under it is published or commercially reused.**
- **Private companies:** CAIPO filings (articles, notices), charge
  documents (lenders name owners/guarantors), annual returns if
  accessible — to verify what annual returns disclose in Barbados.

## 5. How to trace intermediaries

- Every intermediate entity (e.g., Neptune Investments Limited) gets its
  own CAIPO Company Inquiry: incorporation date, officers, registered
  office, charges.
- Assign an entity status from the taxonomy (operating company / holdco /
  nominee / trustee / foundation / SPV / employee plan / institutional /
  estate / unknown) with the evidence for the assignment.
- Registered-office and officer overlap with known family entities is a
  lead, never a conclusion — corroborate before attributing.
- Chains exiting Barbados (to Panama, BVI, etc.) hand off to that
  jurisdiction's playbook.

## 6. How to check property

- Barbados Land Registry / Registration of Titles — access method, cost,
  whether searchable by owner name or only by parcel: **to map** (step
  owner: Phase 0).
- Interim: planning applications, development press, listed-company
  property notes in annual reports.

## 7. How to check charges/debt

- CAIPO records registered mortgages and charges (confirmed searchable in
  principle) — pull per entity; charge documents reveal lenders, secured
  assets, sometimes guarantors and group structures.
- Listed-company debt: annual report notes (verified debt state for the
  three-state debt rule).

## 8. How to check courts/probate

- Barbados judiciary (barbadoslawcourts.gov.bb) — online decision/cause
  list availability, party-name search, and probate/estate filing access:
  **to map**. Probate matters for succession cases; gazette probate
  notices as the entry point.

## 9. How to preserve the evidence

- Standard preservation record per source (methodology §6): original
  document → retrieval date → URL/registry identifier → archive copy/hash
  where legally permissible → passage/page → analyst.
- CAIPO paid-inquiry outputs and any s.176 material: store the original
  response, the request details and date — these are point-in-time
  records; the register the next month is a different document.
- Official statute copies preserved: Companies Act Cap. 308 PDFs (CAIPO
  and Barbados Law Courts sites).

## Live-request checklist before marking operational

- [ ] One paid CAIPO Company Inquiry (GEL) — record fields returned, cost,
      turnaround, format.
- [ ] One paid CAIPO Company Inquiry (Neptune Investments Limited) — the
      Profile #1 intermediary.
- [ ] Counsel memo on s.176: procedure, affidavit, permitted use → set
      O/I/P states.
- [ ] Land registry: one owner-name search attempt → record method/cost or
      the limitation.
- [ ] Charges search on one known entity.
- [ ] Court/probate access check (one party-name search).
