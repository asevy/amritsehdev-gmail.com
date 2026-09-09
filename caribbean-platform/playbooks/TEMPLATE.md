# Jurisdiction Research Playbook — TEMPLATE

> **Status: FROZEN v2 (2026-09-09) — the canonical jurisdiction playbook
> standard.** Clone faithfully for every market (Jamaica ✓, then DR,
> Trinidad & Tobago, Guyana, Bahamas, Cayman, Turks & Caicos, Puerto
> Rico, Panama). The playbooks are the research operating system for
> Caribbean wealth intelligence: they tell a researcher what sequence to
> follow, what is legally uncertain, what counts as evidence, and when to
> stop attributing ownership. A playbook is **draft** until its
> live-request checklist is complete, then **operational**. The template
> is no longer the bottleneck — executing live requests is.

## Required elements

1. **Status header** — draft/operational, date, seeding basis.
2. **Jurisdiction header** — immediately after the status block: legal
   system · primary language(s) · currency · exchange(s) · company
   registry authority · land-registry authority · courts/probate
   authority · beneficial-ownership regime (public / gated / restricted,
   with the statutory test and threshold recorded verbatim, versioned and
   dated).
3. **Legends** — access states (**O** obtainable / **I** internal-use /
   **P** publishable-reusable, per source; obtainable never implies
   publishable), friction **F** 1–5 (1 = cheap/easy/fast), automation
   potential H/M/L, historical depth (YYYY–present or TBD).
4. **Standing legal rules** — any route with unresolved permitted-use
   questions defaults to **I-only (lead generation and internal
   verification), never publishable evidence**, until counsel clears it.
5. **Route summary table** — every route × O/I/P, F, Auto, Depth.
6. **The nine sections, in order**, each carrying six standard blocks:
   - **Expected outputs** — what a complete result contains, so an
     incomplete registry response is spotted immediately.
   - **Route** — the how, with states per source.
   - **F / Auto / Depth** — friction, automation potential, historical
     depth.
   - **Cost / Refresh / Format** — direct fees, likely agent/legal
     costs, estimated analyst time; refresh cadence (continuous / annual
     / event-driven / snapshot-on-suspicion); machine-readability
     (API/structured · HTML · searchable PDF · scanned PDF · in-person
     only). These fields drive the operating cost model: what it costs
     per year to keep a family in this market current.
   - **Confidence impact** — what this route's evidence can and cannot
     do to the two confidence dimensions (e.g., a Tier 1 shareholder
     filing can move ownership evidence Moderate → High; press coverage
     only creates a lead). Standardizes analyst judgment across markets.
   - **Failure path** — what to do when the obvious route fails, ending
     either in a cross-jurisdiction handoff or a documented "unknown"
     with the precise limitation recorded.
7. **Automation hooks** — the market's continuously monitorable signals
   (filings, director changes, charges, gazettes, status changes) that
   feed the Daily Wealth Engine as proposed claims behind analyst review.
8. **Live-request checklist** — the real requests that must be executed
   before the playbook is marked operational, including filling every
   TBD in the route summary.
9. **Operational notes / known failure modes** — after the checklist:
   registry quirks, stale portals, naming issues, agent requirements,
   blocked access, duplicate entities, and any local practices that
   repeatedly trip researchers up. Grows with use; never deleted.

## The nine sections

1. Where to search first
2. How to identify a person
3. How to identify their companies
4. How to pull ownership
5. How to trace intermediaries — every intermediate entity gets a status
   from the taxonomy (operating company / holdco / nominee / trustee /
   foundation / SPV / employee plan / institutional / government / estate
   / unknown), with evidence; "unknown" carries a follow-up task
6. How to check property
7. How to check charges/debt
8. How to check courts/probate
9. How to preserve the evidence (methodology §6 preservation record;
   registry outputs are point-in-time documents)

## Evidentiary discipline for registry-derived claims

- **The graph preserves exactly what the registry says.** "Person →
  registered shareholder → Company" is evidence of a registered
  relationship as of a date — not, by itself, of current beneficial
  ownership or an economic percentage. Interpretation is a separate,
  labeled analyst claim.
- **Absence is only what the statute makes it.** "Not found" in a
  beneficial-ownership register never becomes "owns below the threshold"
  unless the regime's actual test (shares / voting rights / control),
  threshold, version and search scope support that inference — all
  recorded with the claim.

## Reference instance

[BARBADOS.md](BARBADOS.md) is the canonical example of the filled
template; [JAMAICA.md](JAMAICA.md) is the first clone.
