# RECLAIM website — what it must have, and why

Prototype built 2026-11-17 in `reclaim/`. This document explains the decisions; `README.md` explains how to run it; `COMPLIANCE_REGISTER.md` holds the sources.

## 1. What the website is for

The business plan makes the website do five jobs at once:

1. **Acquisition and assessment engine.** It turns a visitor into a member with a Blueprint.
2. **Commerce — for the platform company only.** It sells memberships, add-ons and partner credits. It does **not** sell medication or medical care. Those belong to separate legal entities, which are the merchants of record for their own supplies.
3. **Member portal holding saved information.** Blueprint versions, plan, progress, video progress, bookings, messages, consents and receipts.
4. **Front door for the independent medical practice and the pharmacy.** It is operated as their agent or electronic service provider, with separate records, branding, notices and audit trails.
5. **The cheapest demand-test instrument the business has.** The plan says to test demand, price and attachment before building or hiring. The site measures these first-hand: funnel, willingness to pay, sequential price tests, interest in medical care, waitlist geography, B2B fake doors and coaching workload.

The fourth job shapes the rest. Medication commerce is the intended primary revenue engine, but the rules that make it lawful also shape the website:
- no drug names or claims in public marketing;
- no membership that buys medical access;
- pharmacy choice that is genuinely neutral;
- money that flows directly to the entity that supplies the service.

The prototype builds those constraints into structure rather than relying on copywriting.

## 2. Site map

### Public site (`app/(site)`)

| Route | Purpose | Business-plan arm |
|---|---|---|
| `/` | Positioning, "who does what" across the three entities, how it works (video), programmes preview | All |
| `/assessment` | Four-minute lifestyle and preference questionnaire. Suggests a programme with reasons; answers stay in the browser until signup; optional anonymous price-sensitivity survey | 1, 2 (acquisition), pricing |
| `/how-it-works` | Six steps, each labelled with the responsible entity; Blueprint-session video | All |
| `/programmes` | Five tiers with **inclusions and explicit limits**, pilot-price badges, add-ons, credit rules, the practice's fee schedule (OHIP $0), "medication priced by your pharmacy", cancellation summary | 2, 3 |
| `/medical-care` | Independent practice, the four steps, the independence guarantees, who should see their own doctor. **No drug names** | 1 |
| `/pharmacy` | Pharmacy choice, the three options, disclosure, how fills work | 1 |
| `/coaching` | What coaches do and don't do, response times, credentials, cover | 2 |
| `/network` | Partner types (placeholders), credits, regulated providers as a directory only, "become a partner" form | 3 |
| `/employers`, `/organisations`, `/research` | Fake-door pages with lead forms. Nothing is sold before it exists | 4, 5 |
| `/outcomes` | Pre-specified measures and methods, published before any results | Evidence, exit value |
| `/learn`, `/learn/[slug]`, `/learn/video/[id]` | Referenced articles with reviewer and date (draft banner until signed off); public videos | Acquisition (SEO) |
| `/about` | Structure, governance, money flows; founder placeholders flagged for counsel | Trust, diligence |
| `/legal/*` | Terms and membership agreement, two privacy notices (platform and practice), cancellation, relationships, accessibility, complaints — all drafts | Compliance |
| `/waitlist` | Non-Ontario demand by province or state plus the first three characters of a postal code; separate opt-in for marketing email | Expansion evidence |
| `/join`, `/join/review`, `/checkout/[id]`, `/join/welcome` | Plan → account and consents → full disclosure and agreement → payment → onboarding. `/join?path=medical` creates a free account for medical care only | Commerce |

### Member portal (`app/portal`) — saved information

| Route | What is saved |
|---|---|
| Today | Today's plan items, upcoming sessions, resume-watching, Blueprint targets |
| Blueprint | Versioned plan: goals, capacity, pain limits, nutrition, schedule, sleep, barriers, coaching style, targets. Member edits create a new version |
| This week | Plan items with completion ticks; videos linked to items tick off automatically |
| Progress | Measurements by metric, small-multiple charts with targets, data tables |
| Video library | Saved videos, resume position, completion; signed streaming |
| Appointments, Coach messages, Local network | Bookings, a coaching thread, credit ledger, partner bookings |
| **Care** (medical practice branding) | Intake, visits, labs, prescriptions, pharmacy choice, pharmacy fills and payment, clinical messages, side-effect reports, sharing switches |
| Billing | Membership, two-click cancel, pause, receipts with agreement fingerprints |
| Privacy & data | Separate consent switches, consent history with wording fingerprints, data export, correction and deletion requests, who accessed the medical record |

### Staff and admin

- `/staff/clinician`: queue, chart, intake red flags, sign visit notes, prescribe from the formulary, care-team summary.
- `/staff/pharmacy`: fill queue, counselling gate, pricing from the price list, shipping.
- `/staff/coach`: caseload, Blueprint, messages, and the consented care summary only.
- `/admin`: founder insights — no clinical data.

In production the clinician and pharmacist desks are the practice's certified EMR and the pharmacy's dispensing system. They exist here only to demonstrate the boundaries.

## 3. Commerce design

| Who sells | What | Tax | Where the money goes |
|---|---|---|---|
| RECLAIM (platform) | Memberships, Blueprint session, extra coach sessions, partner credits | HST (taxable services) | Platform account |
| Independent medical practice | Uninsured services only. OHIP-insured services cost $0 (database CHECK) | Exempt | Practice account (payment checkout not built) |
| Pharmacy chosen by the patient | Drug, dispensing fee, delivery | Zero-rated (database CHECK `tax_cents = 0`) | Pharmacy account |

- **No cross-entity cart.** Platform orders can only contain platform items; the schema `CHECK (entity_id='platform')` enforces it. Medication exists only in the pharmacy store. There is no bundled "all-in" price.
- **Disclosure before agreement.** The review page shows the supplier's legal identity, itemised price and tax, renewal, cancellation, refunds and exclusions. The person ticks "I agree"; the snapshot is stored with a SHA-256 fingerprint and emailed straight away.
- **Cancellation.** Two clicks, online, no call. It takes effect at the end of the period, or immediately with a full refund within 14 days of the first payment, which covers the statutory 10-day cooling-off period. Pause is offered on the same screen. **Refunds never depend on a clinical decision.**
- **Price testing.** One live price for everyone at a time (A or B), switched by an admin; conversion is compared by period with Wilson 95% intervals. All prices are marked `hypothesis` until evidence supports them, and the linter lists every hypothesis price as a warning on each run.
- **Medication purchase path:**
  1. The clinician prescribes from the formulary.
  2. The patient chooses a pharmacy: options in random order, none pre-selected, presentation recorded.
  3. A pharmacist verifies the prescription, with counselling required before a first fill.
  4. The pharmacist prices it from the pharmacy's own list. That function takes no membership argument.
  5. The patient pays the pharmacy in a pharmacy-branded panel.
  6. The pharmacy ships with tracking.
- **Payments seam.** `lib/payments.ts` is a mock provider. Production uses one account per entity (for example Stripe Connect or separate accounts), with no per-prescription or percentage fee flowing to the platform.

## 4. Video

| Type | Access | Hosting (prototype → production) |
|---|---|---|
| Programme explainers, public education | Public | Static MP4 and HLS → Mux or Cloudflare Stream public playback |
| Movement library, lesson curriculum, assessment tests | Active or paused members | `media/` (not web-public), streamed by `/media-secure` with one-hour HMAC-signed tokens and Range support → host's signed playback IDs |
| Medication education | Only patients with a matching prescription, owned by the practice or pharmacy | Not built; must sit outside platform marketing |
| Clinical video visits | Patient and clinician | Buy: the practice's EMR or an Ontario Health-verified virtual-visit vendor. No recording |

Every video has:
- captions, on by default, generated from the same cue data as the transcript;
- chapters;
- a clickable transcript and playback speed control;
- resume from the saved position, saved every 10 seconds and on pause or page hide;
- completion at 90%, which ticks off the matching plan item.

The linter fails the build if any video lacks captions. Placeholder renders are generated by `npm run media`; produced videos replace the files without code changes.

## 5. Saved information and the data boundary

There are three physically separate stores (`.data/platform.db`, `clinical.db`, `pharmacy.db`). Nothing joins across them; the only link is an opaque `patient_ref`. Only `lib/clinical` may open the clinical store and only `lib/pharmacy` the pharmacy store; the linter enforces this.

- **Consents:** an append-only ledger; each row stores the hash of the exact wording shown. Separate switches for:
  - marketing email (CASL);
  - coaching data → clinician;
  - care summary → coach;
  - de-identified research;
  - employer aggregate reporting;
  - product analytics.
- **Audit:** hash-chained, append-only logs in each store; database triggers block UPDATE and DELETE. Members see staff access to their medical record.
- **Rights:**
  - one-click JSON export of platform data, plus a labelled summary of the clinical record;
  - correction and deletion requests with 30-day clocks;
  - requests for a full copy of the medical record are routed to the practice.
- **Analytics:** first-party only; event names and property keys are allow-listed so no health data can be recorded; no third-party pixels (the linter enforces this).

## 6. Compliance built into the code (not just the copy)

`npm run compliance` runs automatically before every `npm run build` and fails it on:

1. a prescription drug, brand or peptide name in public content or video captions;
2. claim language (guarantee, miracle, risk-free, clinically proven, superlatives, star ratings, numeric weight-loss promises, "stack", "research use only");
3. a Schedule A.1 condition within eight words of treat, cure, prevent or manage;
4. hard-coded prices in public JSX (prices must come from the catalogue);
5. videos without captions, posters or media files;
6. code outside `lib/clinical` or `lib/pharmacy` opening their stores, or clinical/pharmacy code importing commerce;
7. third-party trackers;
8. pre-ticked optional consents;
9. catalogue items that aren't platform-sold, lack a tax code, or bundle medical care or medication;
10. published articles with no clinical reviewer.

These are enforced by the schema:
- `CHECK` that an OHIP encounter has $0 fee;
- formulary `hc_status='marketed'` with governance approval required;
- one product per prescription;
- pharmacy orders zero-tax;
- platform orders platform-only;
- append-only audit triggers.

These are enforced by server code:
- `requireUser()` in every protected page and server action;
- membership is never checked on Care routes;
- licensure and location attestation before a clinical booking;
- the CASL guard in `sendEmail()`.

## 7. Build versus buy

| Capability | Recommendation | Build in-house when… |
|---|---|---|
| Marketing site, assessment, portal UI, Blueprint, insights | **Build** (this codebase). It is the proprietary method and the diligence record | — |
| CMS for articles and pages | Typed content files now; a headless CMS later, with the linter as its publish check | More than one non-engineer editing weekly |
| Auth | Built: scrypt plus database sessions. Before launch add MFA for staff, and consider a managed identity provider with Canadian data residency | — |
| Payments and subscriptions | **Buy** (Stripe or similar), one account per entity; keep our own cancel screen | Never build card handling |
| EMR, clinical notes, e-prescribing, labs | **Buy**: the practice's OntarioMD-certified EMR; PrescribeIT or fax; lab interfaces through the EMR. The portal reads and writes through the EMR's API as agent | Never, unless an EMR blocks integration |
| Pharmacy dispensing and claims adjudication | **Buy**: the pharmacy's dispensing system; integrate only fill status and price | Never |
| Video hosting and streaming | **Buy** (Mux or Cloudflare Stream); keep our player | Never |
| Clinical video visits | **Buy** (EMR-integrated or Ontario Health-verified vendor) | Never |
| Coach and partner booking | Prototype has simple slots; **buy** a scheduler (e.g. Jane App or Acuity) for coaches; partners via their own systems or a credits API | Partner volume justifies a direct integration |
| Email and SMS | **Buy** a provider with Canadian data residency behind `lib/email.ts` | — |
| Analytics | Keep first-party (`events`); add a privacy-first warehouse later | — |
| Support desk | **Buy** (help desk with a Canadian region); never put clinical information in it | — |
| Outcome reporting | **Build** on our own data with intention-to-treat definitions; export to an REB-approved environment for research | — |

## 8. Rollout phases and gates

| Phase | Ship | Gate to move on |
|---|---|---|
| **0. Demand test (weeks 0–6)** | Public pages, assessment, waitlist, willingness-to-pay survey, fake doors, admin insights. **No payments and no health data.** `RECLAIM_DEMO_MODE=false`; noindex removed only after counsel review of copy | Counsel sign-off on public copy; enough completed assessments and survey responses to read the price range and medical-interest share |
| **1. Coaching pilot** | Memberships with the payment provider, portal, video library on the host, coach scheduler, real coaches | Cooling-off and trust questions answered; signed agreements with coaches and two or three partners; accessibility audit; privacy impact assessment |
| **2. Medical arm** | Care area wired to the practice's EMR; pharmacy integration for fill status; clinical notices and agreements live | Signed agent/ESP agreements; formulary approved by the medical director; legal opinion on the funnel (O. Reg. 114/94 s.7) and pharmacy relationship; LegitScript before any paid acquisition |
| **3. Scale and expand** | Jurisdiction rows switched on province by province; employer sponsor codes; licensing tools | Waitlist density per province or state, licensed clinicians, pharmacy permissions and partners in place. The US needs separate entities and a HIPAA programme |

## 9. What is real and what is mocked in this prototype

**Real and working:**
- every page and flow;
- accounts and sessions, consents, orders and subscriptions with tax;
- agreement snapshots, cancel, pause and refund;
- credits and bookings;
- video streaming with signed URLs, captions and resume;
- progress logging and charts;
- the full prescription → pharmacy choice → fill → pay → ship flow across three stores;
- audit logs, data export, the admin insights;
- the compliance linter.

**Mocked:**
- payment provider (test checkout page);
- email (written to an outbox);
- EMR, e-prescribing, labs, video visits;
- scheduling slots;
- partner names, formulary items and pharmacy prices (placeholders);
- legal text (drafts);
- prices (hypotheses);
- synthetic analytics (tagged and excluded by default).

## 10. Founder decisions this build assumed (change in config)

- **Placement:** the code lives in a `reclaim/` folder of this repository (an unrelated trading toolkit sits at its root). Move it to its own repository when convenient.
- **Prices:** Foundation $39, Core $149, Hybrid $249, Premium $449, Maintenance $69 per month (B variants higher). These are **placeholders**, not evidence-based, and are set in `config/catalog.ts`.
- **Names:** legal names, the practice, the pharmacy, partners and founders are bracketed placeholders in `config/site.ts`, `config/partners.ts` and `/about`. The physician co-founder is not named until counsel advises.
- **Medication on the public site:** none. A C.01.044-style price list was deliberately not built.
