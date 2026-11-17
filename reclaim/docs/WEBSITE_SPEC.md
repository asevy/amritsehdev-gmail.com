# RECLAIM website — what it must have, and why

Prototype built 2026-11-17 in `reclaim/`. This document explains the decisions; `README.md` explains how to run it; `COMPLIANCE_REGISTER.md` holds the sources.

## 1. What the website is for

The business plan makes the website do five jobs at once:

1. **Acquisition and assessment engine.** It turns a visitor into a member with a Blueprint.
2. **Commerce — for the platform company only.** It sells memberships, add-ons and partner credits. It does **not** sell medication or medical care. Those belong to separate legal entities, which are the merchants of record for their own supplies.
3. **Member portal holding saved information.** Blueprint versions, plan, progress, form-check videos with coach ratings, bookings, messages, consents and receipts, gathered into one growing record so members keep coming back (§4a).
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
| `/learn`, `/learn/[slug]` | Referenced articles with reviewer and date (draft banner until signed off) | Acquisition (SEO) |
| `/about` | Structure, governance, money flows; founder placeholders flagged for counsel | Trust, diligence |
| `/legal/*` | Terms and membership agreement, two privacy notices (platform and practice), cancellation, relationships, accessibility, complaints — all drafts | Compliance |
| `/waitlist` | Non-Ontario demand by province or state plus the first three characters of a postal code; separate opt-in for marketing email | Expansion evidence |
| `/join`, `/join/review`, `/checkout/[id]`, `/join/welcome` | Plan → account and consents → full disclosure and agreement → payment → onboarding. `/join?path=medical` creates a free account for medical care only | Commerce |

### Member portal (`app/portal`) — saved information

| Route | What is saved |
|---|---|
| Today | Today's plan items, upcoming sessions, latest coach cues and any re-film due, Blueprint targets |
| My record | One timeline of everything: form checks and reviews, measurements, Blueprint versions, sessions, weeks, personal bests and form-improvement milestones |
| Blueprint | Versioned plan: goals, capacity, pain limits, nutrition, schedule, sleep, barriers, coaching style, targets. Member edits create a new version |
| This week | Plan items with completion ticks; a form-check task ticks itself when a clip for that exercise is saved |
| Progress | Measurements by metric, small-multiple charts with targets, data tables |
| Form checks | The member's own exercise clips (recorded by them or their coach), on-device measurements, coach ratings and cues, first-vs-latest comparison, re-film due dates |
| Appointments, Coach messages, Local network | Bookings, a coaching thread, credit ledger, partner bookings |
| **Care** (medical practice branding) | Intake, visits, labs, prescriptions, pharmacy choice, pharmacy fills and payment, clinical messages, side-effect reports, sharing switches |
| Billing | Membership, two-click cancel, pause, receipts with agreement fingerprints |
| Privacy & data | Separate consent switches, consent history with wording fingerprints, data export, correction and deletion requests, who accessed the medical record |

### Staff and admin

- `/staff/clinician`: queue, chart, intake red flags, sign visit notes, prescribe from the formulary, care-team summary.
- `/staff/pharmacy`: fill queue, counselling gate, pricing from the price list, shipping.
- `/staff/coach`: form-check review queue, recording a form check with a member, caseload, Blueprint, messages, and the consented care summary only.
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

## 4. Video: one example, plus form checks

Generic exercise video is abundant and free elsewhere, so RECLAIM does not build a content library. It keeps **one programme explainer** on the home page as an example (captions, chapters, transcript). The video unique to RECLAIM is **each member's own form checks**.

**Form checks:**
1. The member records a short side-on clip in the browser (phone or laptop camera) or uploads one. A coach can also record or upload a clip *with* the member, for example in a session; it lands in the member's programme and doesn't use their allowance.
2. On the member's device, an open-source pose model (MediaPipe Pose Landmarker, Apache-2.0, self-hosted) estimates joint angles, reps and lowering time. It also draws the detected skeleton on the deepest rep, so the member can see what was measured. Frames are not sent anywhere for this step.
3. The member can share the video plus the measurements, or **measurements only**.
4. The coach rates each criterion (needs work / improving / solid) and writes cues.
5. Each exercise keeps first-vs-latest clips side by side, a table of every check (ratings, form score, measurements), the latest cues and a re-film due date (every 4 weeks).

| Exercise | Measured on device (estimates) | Coach criteria |
|---|---|---|
| Goblet squat | Reps, knee angle at deepest point, torso lean at the bottom, lowering time | Depth without pain, knee tracking, chest tall/back neutral |
| Hip hinge | Reps, hip angle at deepest point, knee bend at the bottom, lowering time | Hips back, neutral back, soft steady knees |
| Push-up | Reps, elbow angle at deepest point, largest sag/pike of the body line, lowering time | Straight body line, controlled depth, elbow position |

**Limits and guardrails:**
- Reviews are capped per plan (Foundation 1, Core 2, Hybrid 4, Premium 8, Maintenance 1 a month) and counted in coach capacity at 6 minutes each (assumption).
- The measurements are estimates from one camera angle, for tracking change over time. They are **not** a safety guarantee, injury-risk score or clinical assessment, and the copy never says they "ensure" correct lifting.
- When the body isn't clearly visible or no full reps are found, the result is flagged low-confidence instead of guessed.
- A coach reviews every clip; symptoms go to the medical practice.
- **Validation before any claim:** in the pilot, compare device angles and rep counts with coach ratings (and a goniometer on a subset) across lighting, clothing and camera positions. Unit tests cover the angle and rep maths on synthetic data. The model has run end to end in the browser, but it has **not** yet been tested on real lifters.
- **Hardware sensors** (bar-speed or wearable motion sensors) are a later, optional adapter: the data model records each measurement's source. Phone camera first because it needs no hardware inventory (capital-light).

**Privacy:** exercise video of a person's body is sensitive personal information.
- A separate consent is needed before storing video.
- Clips are stored outside the web root and streamed only through one-hour signed links, after re-checking that the viewer is the member or a coach. Founders, clinicians and pharmacists cannot view them.
- Members can delete any video (keeping the ratings) or remove a check entirely, or delete all videos from Privacy.
- Clips are not shared with the medical practice or employers and are never used in marketing.

## 4a. Stickiness: why members keep coming back

Everything a member does is saved into their programme and shown back to them, so the record becomes more valuable every week:

- **My record:** one timeline of form checks, coach reviews, measurements, Blueprint versions, sessions and completed weeks, with personal bests and "form improved" milestones worked out from their own data.
- **Form history:** first-vs-latest clips and a ratings table per exercise, re-film reminders every 4 weeks, and coach cues on the Today page.
- **Plan links:** a form-check task in the weekly plan ticks itself when the clip is saved; coach-recorded clips land straight in the member's programme.
- **Guardrails:** value, not lock-in. Everything is exportable in one click, cancellation stays two clicks, and personal bests avoid body weight. Reminder emails are limited to the member's own programme (counsel to confirm the CASL category); marketing still needs separate consent.

## 5. Saved information and the data boundary

There are three physically separate stores (`.data/platform.db`, `clinical.db`, `pharmacy.db`). Nothing joins across them; the only link is an opaque `patient_ref`. Only `lib/clinical` may open the clinical store and only `lib/pharmacy` the pharmacy store; the linter enforces this.

- **Consents:** an append-only ledger; each row stores the hash of the exact wording shown. Separate switches for:
  - marketing email (CASL);
  - coaching data → clinician;
  - care summary → coach;
  - de-identified research;
  - employer aggregate reporting;
  - product analytics;
  - storing form-check videos.
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
| Form-check video storage and playback | Prototype stores clips privately on the server with signed links. Production: **buy** a video host with direct uploads, transcoding, signed playback and a Canadian region | Never build transcoding |
| Pose estimation | **Use** the open-source on-device model (MediaPipe, Apache-2.0); build only the angle/rep logic and the review workflow | — |
| Hardware motion sensors | Later, **buy/partner** via an adapter only if pilot data shows the camera is not enough | Never manufacture |
| Clinical video visits | **Buy** (EMR-integrated or Ontario Health-verified vendor) | Never |
| Coach and partner booking | Prototype has simple slots; **buy** a scheduler (e.g. Jane App or Acuity) for coaches; partners via their own systems or a credits API | Partner volume justifies a direct integration |
| Email and SMS | **Buy** a provider with Canadian data residency behind `lib/email.ts` | — |
| Analytics | Keep first-party (`events`); add a privacy-first warehouse later | — |
| Support desk | **Buy** (help desk with a Canadian region); never put clinical information in it | — |
| Outcome reporting | **Build** on our own data with intention-to-treat definitions; export to an REB-approved environment for research | — |

## 8. Rollout phases and gates

Each gate is a condition for **entering** that phase, not a review after it. Nothing is charged before gate 1; no medical care starts before gate 2.

| Phase | Ship | Gate to enter this phase |
|---|---|---|
| **0. Demand test (weeks 0–6)** | Public pages, assessment, waitlist, willingness-to-pay survey, fake doors, admin insights. **No payments and no health data.** `RECLAIM_DEMO_MODE=false`; noindex removed only after counsel review of copy | Counsel review of public copy |
| **1. Coaching pilot** | Memberships with the payment provider, portal, form checks with clips on a video host (device measurements labelled as estimates while the validation study runs), coach scheduler, real coaches | **Gate 1:** demand data justifies it (completed assessments and survey responses enough to read the price range and medical-interest share); counsel signs off public copy and the cooling-off and trust questions; coach and partner contracts signed; privacy impact assessment and accessibility audit done |
| **2. Medical arm** | Care area wired to the practice's EMR; pharmacy integration for fill status; clinical notices live | **Gate 2:** agent/ESP agreements with the practice and pharmacy signed; formulary approved by the medical director; legal opinion on the funnel (O. Reg. 114/94 s.7) and the pharmacy relationship |
| **3. Scale and expand** | Jurisdiction rows switched on province by province; employer sponsor codes; licensing tools | **Gate 3:** LegitScript before any paid acquisition; per province or state, waitlist density, licensed clinicians, pharmacy permissions and partners in place. The US needs separate entities and a HIPAA programme |

## 9. What is real and what is mocked in this prototype

**Real and working:**
- every page and flow;
- accounts and sessions, consents, orders and subscriptions with tax;
- agreement snapshots, cancel, pause and refund;
- credits and bookings;
- form checks: in-browser recording, upload, on-device pose measurement, coach review, coach-recorded clips, signed streaming, deletion;
- My record timeline with personal bests and milestones;
- progress logging and charts;
- the full prescription → pharmacy choice → fill → pay → ship flow across three stores;
- audit logs, data export, the admin insights;
- the compliance linter.

**Mocked:**
- payment provider (test checkout page);
- demo form-check clips and their measurements (placeholders, labelled demo);
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
