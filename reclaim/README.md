# RECLAIM — website, commerce, video and member portal (prototype)

A working prototype of the RECLAIM website. It covers:
- the public site and free assessment;
- commerce for memberships;
- a video library with signed streaming, captions and resume;
- a member portal that saves the Blueprint, plan, progress and consents;
- the independent medical practice's Care area, with neutral pharmacy choice and a pharmacy-paid fill flow;
- staff desks for clinician, pharmacist and coach;
- a founder insights dashboard for demand and price testing.

- **Why it's built this way:** [`docs/WEBSITE_SPEC.md`](docs/WEBSITE_SPEC.md)
- **Regulatory sources and counsel questions:** [`docs/COMPLIANCE_REGISTER.md`](docs/COMPLIANCE_REGISTER.md)

> Prototype only. Legal names, partners, formulary items and pharmacy prices are placeholders. Prices are untested hypotheses. Legal pages are drafts that need counsel review. Nothing is charged and no email is sent.

## Run it

Requires **Node 22.13+** (uses the built-in `node:sqlite`). ffmpeg is only needed to regenerate the placeholder videos.

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
| member@reclaim.test | Member (Core) | Portal → **Care** → choose a pharmacy for the waiting prescription → request first fill |
| pharmacist@reclaim.test | Pharmacist | Tick counselling → **Verify & price** → (member pays in Care) → **Mark shipped** |
| clinician@reclaim.test | Clinician | Open Jordan Lee's chart; prescribe from the formulary; write the coach summary |
| coach@reclaim.test | Coach | Sees the Blueprint and the consented care summary — never the medical record |
| founder@reclaim.test | Admin | Insights: funnel, price test, willingness to pay, capacity, outbox. Toggle "Include synthetic demo data" |

New-visitor path: **Free assessment → Start with Core → create account → review agreement → test checkout → welcome**. Then **Billing → Cancel membership** (two clicks, full refund within 14 days).

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` / `build` / `start` | Next.js. **`build` runs the compliance linter first and fails on violations** |
| `npm run compliance` | Linter for drug and peptide names, claims, Schedule A.1 treatment language, hard-coded prices, missing captions, store boundaries, trackers, pre-ticked consents, catalogue bundling, unreviewed articles |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run media` | Regenerates placeholder videos, posters, captions and chapters from `content/videos.json` (ffmpeg) |
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
                         measurements, video progress,    labs, messages, summaries     audit_log (hash chain)
                         bookings, events, waitlist       audit_log (hash chain)
                         audit_log (hash chain)
                                    └──── linked only by an opaque patient_ref; no joins across stores ────┘
```

| Path | Contents |
|---|---|
| `config/` | Entities, jurisdictions, catalogue (prices, limits, workload), tax codes, consents, partners and pharmacy options |
| `content/` | Videos (metadata, chapters, captions), articles with references, draft legal pages |
| `db/schema/*.sql` | Three schemas with integrity CHECKs and append-only audit triggers |
| `lib/` | `auth`, `commerce` (cart, agreement, cancel and refund), `clinical/` and `pharmacy/` (only modules allowed to open their stores), `media-auth` (signed video), `assessment` (non-diagnostic suggestion, Van Westendorp), `analytics` (allow-listed), `email` (CASL guard), `payments` (provider seam) |
| `app/` | Routes. `(site)` public, `portal/` member, `staff/` professional desks, `admin/`, `media-secure/`, `api/` |
| `scripts/` | `compliance-lint.mjs`, `make-placeholder-media.mjs` |

## Swapping mocks for production services

| Mock | Replace with | Where |
|---|---|---|
| Test checkout page | Payment provider, one account per entity, signed webhooks | `lib/payments.ts`, `app/checkout/` |
| Email outbox | Email provider with Canadian data residency | `lib/email.ts` |
| `clinical.db` and clinician desk | The practice's certified EMR (API) | `lib/clinical/` |
| `pharmacy.db` and pharmacy desk | The pharmacy's dispensing system (fill status and price) | `lib/pharmacy/` |
| `media/` plus `/media-secure` | Video host with signed playback (Mux or Cloudflare Stream) | `lib/media-auth.ts`, `lib/videos.ts` |
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

- `npm run typecheck` passes; `npm run compliance` reports 0 errors (warnings list the hypothesis prices and draft articles). A planted violation (drug name, peptide, "guaranteed", "stack", treatment claim, raw price) fails it as expected.
- A 25-step Playwright walkthrough passed with no browser console errors:
  - assessment → join → disclosure → pay → two-click refunded cancel;
  - signed video with Range and resume, progress completion;
  - pharmacy choice with no default → counselling gate → pharmacy pricing → member pays the pharmacy → ship;
  - clinician chart access appears in the member's log;
  - role isolation (coach and founder blocked from the clinical desk; member blocked from admin).
