# RECLAIM — website, commerce, video and member portal (prototype)

A working prototype of the RECLAIM website. It covers:
- the public site and free assessment;
- commerce for memberships;
- **form checks**: members (or their coach) record a lift in the browser; an on-device pose model measures joint angles, reps and tempo; the coach rates it; first-vs-latest comparisons show improvement over time;
- a member portal that saves everything into **My record** (form checks, measurements, Blueprint versions, sessions, personal bests) so members keep coming back;
- one example programme video (captions, chapters, transcript). There is deliberately no exercise-video library;
- the independent medical practice's Care area, with neutral pharmacy choice and a pharmacy-paid fill flow;
- staff desks for clinician, pharmacist and coach;
- a founder insights dashboard for demand and price testing.

- **Why it's built this way:** [`docs/WEBSITE_SPEC.md`](docs/WEBSITE_SPEC.md)
- **Regulatory sources and counsel questions:** [`docs/COMPLIANCE_REGISTER.md`](docs/COMPLIANCE_REGISTER.md)

> Prototype only. Legal names, partners, formulary items and pharmacy prices are placeholders. Prices are untested hypotheses. Legal pages are drafts that need counsel review. Nothing is charged and no email is sent.

## Run it

Requires **Node 22.18+** (uses the built-in `node:sqlite` and runs the TypeScript unit tests directly). On first `npm run dev` / `npm run build`, `scripts/setup-pose.mjs` copies the pose runtime into `public/mediapipe/` and downloads the 5.8 MB pose model once into `public/models/`. If that download is blocked, form checks still work without automatic measurement. ffmpeg is only needed to regenerate placeholder media.

```bash
cd reclaim
```

```bash
npm install
```

```bash
npm run dev
```

Open http://localhost:3000. The first request creates `.data/` and seeds demo data. To start over:

```bash
npm run db:reset
```

### Demo accounts (password `reclaim-demo`)

| Email | Role | Try |
|---|---|---|
| member@reclaim.test | Member (Core) | **Form checks**: compare goblet-squat clips (form score 17% → 83%), record or upload a push-up; **My record**; Care → choose a pharmacy → request first fill |
| pharmacist@reclaim.test | Pharmacist | Tick counselling → **Verify & price** → (member pays in Care) → **Mark shipped** |
| clinician@reclaim.test | Clinician | Open Jordan Lee's chart; prescribe from the formulary; write the coach summary |
| coach@reclaim.test | Coach | Review the waiting hip-hinge form check; record a clip with Jordan; sees the consented care summary, never the medical record |
| founder@reclaim.test | Admin | Insights: funnel, price test, willingness to pay, capacity, outbox. Toggle "Include synthetic demo data" |

New-visitor path: **Free assessment → Start with Core → create account → review agreement → test checkout → welcome**. Then **Billing → Cancel membership** (two clicks, full refund within 14 days).

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` / `build` / `start` | Next.js. **`build` runs the compliance linter first and fails on violations** |
| `npm test` | Unit tests for the movement maths (angles, aspect correction, rep detection, tempo, tamper-proof parsing) on synthetic landmarks |
| `npm run setup:pose` | Copies the pose runtime and downloads the model (runs automatically before dev and build) |
| `npm run compliance` | Linter for drug and peptide names, claims, Schedule A.1 treatment language, hard-coded prices, missing captions, store boundaries, trackers, pre-ticked consents, catalogue bundling, unreviewed articles |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run media` | Regenerates the example programme video and the demo form-check clips (ffmpeg) |
| `npm run db:reset` | Deletes `.data/`; demo data reseeds on the next request |

## Architecture

```
                    ┌──────────────────────── Next.js app (one codebase, three entities) ───────────────────────┐
 Visitor ──► Public site, /assessment (answers stay in browser), /programmes, /join ──► mock hosted checkout   │
 Member  ──► /portal  (Blueprint · plan · progress · video · coach · network · billing · privacy)              │
             /portal/care  ── operated as agent for ──►  Independent medical practice                         │
 Staff   ──► /staff/clinician  /staff/pharmacy  /staff/coach        Founders ──► /admin (no clinical data)     │
                    └───────────────┬───────────────────────────────┬───────────────────────────┬─────────────┘
                                    │                               │                           │
                         .data/platform.db (PIPEDA)       .data/clinical.db (PHIPA)     .data/pharmacy.db (PHIPA)
                         users, consents, orders,         patients, intake, visits,     rx inbox, fills, price
                         subscriptions, Blueprint,        formulary, prescriptions,     list, orders (0% tax)
                         measurements, form checks,       labs, messages, summaries     audit_log (hash chain)
                         bookings, events, waitlist       audit_log (hash chain)
                         audit_log (hash chain)
                                    └──── linked only by an opaque patient_ref; no joins across stores ────┘
```

| Path | Contents |
|---|---|
| `config/` | Entities, jurisdictions, catalogue (prices, limits, workload), tax codes, consents, partners and pharmacy options |
| `content/` | The one example video (chapters, captions), articles with references, draft legal pages |
| `db/schema/*.sql` | Three schemas with integrity CHECKs and append-only audit triggers |
| `lib/` | `auth`, `commerce` (cart, agreement, cancel and refund), `clinical/` and `pharmacy/` (only modules allowed to open their stores), `form-checks` (storage, allowance, review, signed playback), `mechanics` (pure angle/rep maths) and `pose-browser` (on-device model), `record` (My record timeline), `media-auth` (signed links), `assessment` (non-diagnostic suggestion, Van Westendorp), `analytics` (allow-listed), `email` (CASL guard), `payments` (provider seam) |
| `app/` | Routes. `(site)` public, `portal/` member, `staff/` professional desks, `admin/`, `media-secure/`, `api/` |
| `scripts/` | `compliance-lint.mjs`, `make-placeholder-media.mjs` |

## Swapping mocks for production services

| Mock | Replace with | Where |
|---|---|---|
| Test checkout page | Payment provider, one account per entity, signed webhooks | `lib/payments.ts`, `app/checkout/` |
| Email outbox | Email provider with Canadian data residency | `lib/email.ts` |
| `clinical.db` and clinician desk | The practice's certified EMR (API) | `lib/clinical/` |
| `pharmacy.db` and pharmacy desk | The pharmacy's dispensing system (fill status and price) | `lib/pharmacy/` |
| Form-check clips in `.data/uploads/` plus `/media-secure/form-check` | Video host with direct uploads, transcoding, signed playback and a Canadian region | `lib/form-checks.ts`, `lib/media-auth.ts` |
| Generated slots | Coach scheduler; partner booking APIs | `app/portal/appointments`, `app/portal/network` |
| SQLite | Postgres (same schema shape; three databases or schemas with separate credentials) | `lib/db/` |

Before launch:
- MFA for staff;
- a nonce-based CSP (currently `unsafe-inline`);
- rate limiting backed by a shared store;
- an accessibility audit;
- a privacy impact assessment;
- penetration testing;
- removing `robots: noindex` only after counsel signs off the public copy.

## Verification done

- `npm run typecheck` passes; `npm test` passes 9 unit tests on the movement maths; `npm run compliance` reports 0 errors (warnings list hypothesis prices and draft articles). A planted violation (drug name, peptide, "guaranteed", "stack", treatment claim, raw price) fails it as expected.
- Playwright, 20-step main walkthrough with no browser console errors: assessment → join → disclosure → pay → two-click refunded cancel; pharmacy choice with no default → counselling gate → pharmacy pricing → member pays the pharmacy → ship; clinician chart access shown in the member's log; role isolation.
- Playwright, 17-step form-check walkthrough, run on the dev server **and on a production build under the strict CSP**:
  - seeded history and the first-vs-latest comparison;
  - signed clip streaming with Range, and refusal without a token;
  - member upload with the pose model running on the device; it correctly reports no person in the placeholder clip;
  - the push-up plan item ticks; the monthly allowance blocks a third upload;
  - coach review; the coach records with the browser camera (Chromium fake device);
  - the member sees the cues; My record shows the milestones;
  - admin is blocked.
- **Not yet validated:** pose accuracy on real lifters. No real footage could be used in this environment, so this needs the pilot validation described in `docs/WEBSITE_SPEC.md` §4.
