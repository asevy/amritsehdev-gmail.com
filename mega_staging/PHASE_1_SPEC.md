# PHASE 1 IMPLEMENTATION SPEC
*For the Claude Code session on the MacBook at `~/investing/`. Reference companion to MEGA_SYSTEM_BUILD_BRIEF.md.*

**Goal of Phase 1:** ONE orchestrator that dispatches to analysts, ONE digest
that unifies their outputs, ONE ntfy topic that receives priority-tagged
pushes. All existing subsystems (quality screener, alert monitor) stay
frozen; the orchestrator wraps their outputs into the unified digest.

**Success condition:** for one full week, the mega-digest reproduces the
existing Sunday screener email + the existing 9:45am/3:45pm zone alerts
byte-identically in their sections. Zero regression. Then Phase 2 begins.

---

## 1. File layout to create under `~/investing/`

```
~/investing/
├── orchestrator.py               ← NEW (based on orchestrator_skeleton.py in this staging dir)
├── ntfy_publish.py               ← NEW (drop-in from staging)
├── analysts/
│   ├── __init__.py
│   ├── quality.py                ← NEW: wraps quality_value_screener (see §3)
│   ├── zones.py                  ← NEW: wraps alert_monitor (see §4)
│   ├── junior_stub.py            ← Phase 3 placeholder
│   ├── congress_stub.py          ← Phase 5 placeholder
│   ├── swing_stub.py             ← Phase 6 placeholder
│   ├── research_stub.py          ← Phase 2 placeholder
│   └── filing_regate_stub.py     ← Phase 4 placeholder
├── config/
│   ├── master_watchlist_input.txt    ← ticker per line, # comments ok
│   ├── positions.yaml                ← held names + structural stops + thesis-break rules
│   └── events.yaml                   ← hand-curated calendar entries
├── digests/                           ← YYYY-MM-DD-HHMM.md immutable archive
├── journal.jsonl                      ← every push, every action-button response
├── inbox/pdfs/                        ← Amrit drops TD PDFs here
├── dossiers/<TICKER>/                 ← auto-populated per-ticker research notes
└── .paused                            ← presence file = vacation mode
```

**Do NOT touch:**
- `quality_value_screener.py` (frozen until 2027-07-20)
- `alpha_screener.py` (frozen)
- Any file inside those two modules

---

## 2. Cron schedule (GitHub Actions)

| Window | Toronto time | UTC cron (adjust for DST) | Analysts run |
|---|---|---|---|
| pre_market | 08:30 Mon–Fri | `30 12 * * 1-5` (EDT) / `30 13 * * 1-5` (EST) | quality (weekly-only skips), zones, filing_regate |
| open       | 09:45 Mon–Fri | `45 13 * * 1-5` (EDT) / `45 14 * * 1-5` (EST) | zones (existing alert_monitor.py replaces this stub for now) |
| midday     | 12:00 Mon–Fri | `0 16 * * 1-5` (EDT) / `0 17 * * 1-5` (EST) | zones only |
| close      | 15:45 Mon–Fri | `45 19 * * 1-5` (EDT) / `45 20 * * 1-5` (EST) | zones (existing alert_monitor.py) |
| after_hours| 17:00 Mon–Fri | `0 21 * * 1-5` (EDT) / `0 22 * * 1-5` (EST) | filing_regate, junior_stub, research_stub |
| weekly     | 07:00 Sun     | `0 11 * * 0` (EDT) / `0 12 * * 0` (EST) | quality (existing quality_value_screener.py invocation), congress_stub |

DST handling: use `TZ=America/Toronto` in the workflow env and the cron
runner will do the conversion. Simpler than maintaining two cron sets.

**Migration note:** the existing `alert_monitor.py` continues to run in its
current form during Phase 1. The orchestrator's `zones` analyst is a no-op
that reports "zone alerts handled by alert_monitor.py — see separate push"
until Phase 4 folds it in. Same for `quality_value_screener.py`.

---

## 3. Quality analyst wrapper — spec

Wraps the frozen `quality_value_screener.py`. Does NOT modify it.

```python
# analysts/quality.py
from quality_value_screener import run_sunday_screen  # existing entry point
# (rename if the actual entry point is different — grep for the Sunday runner)

def quality_analyst(ctx):
    if ctx.cron_window != "weekly":
        return SectionReport(
            name="Quality analyst",
            lines=["(runs Sunday only)"],
            fired=False,
        )
    result = run_sunday_screen()   # returns whatever the frozen module already returns
    lines = format_survivors_block(result)  # preserve existing "B 74 ADBE   B:B A:B- D:A-" format
    return SectionReport(
        name="Quality analyst",
        lines=[f"QUALITY-VALUE — {len(result.survivors)} survivor(s) of {result.universe_size}:"] + lines,
        fired=False,      # weekly digest, no push (subscribers read the digest)
        push_priority=None,
    )
```

**Requirement:** the output lines must be byte-identical to what the
existing Sunday email contains, so subscribers see no format change.

---

## 4. Zones analyst wrapper — spec

Wraps the existing `alert_monitor.py`. Same principle — no modification of
the source module. If `alert_monitor.py` continues to push its own alerts
independently during Phase 1, this analyst returns a section that says
"zones handled by alert_monitor.py — see separate push" and does not push.

Phase 4 folds `alert_monitor.py` into this analyst and retires the separate
push path. Not now.

---

## 5. Ntfy topic and env

| Env var | Value | Where set |
|---|---|---|
| `NTFY_TOPIC` | `stock-alerts-f58fea644aedeff437` (existing) OR a new dedicated mega-system topic (Amrit's call — see below) | GitHub Actions secret |
| `NTFY_HOST` | `https://ntfy.sh` | default in code, override if you self-host |
| `JOURNAL_WEBHOOK` | URL to a small serverless function (Cloudflare Workers / AWS Lambda) that receives action-button POSTs and appends to `journal.jsonl` | GitHub Actions secret; can be omitted for Phase 1 — buttons fall back to `view` action |
| `DIGEST_BASE_URL` | `https://github.com/asevy/investing-alerts/blob/main/digests/` (so pushes link back to the day's digest) | GitHub Actions env |
| `NTFY_DISABLED` | `1` to silence pushes (local testing, .paused mode passes this too) | conditional in workflow |

**Topic decision Amrit still owes:** reuse `stock-alerts-f58fea644aedeff437`
(one channel, everything mixed) or route mega-system to a new topic
(existing alerter stays untouched). Recommend NEW topic if he wants per-
channel notification tuning. Ask him first, don't decide unilaterally.

---

## 6. Journal schema

`journal.jsonl` — one JSON object per line. Never edit; only append.

```json
{"ts": 1755740760, "kind": "push", "section": "Zone alerter", "priority": 4,
 "title": "GOOGL entered zone", "body": "GOOGL 340.67 (<= 355) ...",
 "message_id": "abc123"}
{"ts": 1755740800, "kind": "action", "message_id": "abc123",
 "response": "acted", "notes": ""}
{"ts": 1755741000, "kind": "digest", "date": "2026-08-20", "window": "close",
 "sections": 5, "fired": 1, "path": "digests/2026-08-20-1545.md"}
```

The action-response webhook (Phase 1 optional) writes the `action` lines.

---

## 7. Killswitch / vacation mode

Presence of `.paused` file at repo root = skip pushes. Data collection still
runs (analysts execute, digest is still written to `digests/`). Only the
push side is silenced. Contents of `.paused` become the reason string in
the digest header.

To pause from phone: use GitHub mobile app to create the file with content
"vacation until Aug 25", commit, wait for next cron.

To resume: delete the file, commit.

Consider a companion GitHub Actions workflow triggered on issue comment
"/pause 3d" that writes/deletes `.paused` automatically. Nice-to-have,
not required for Phase 1.

---

## 8. Verification protocol — before Phase 1 merges to main

1. `python orchestrator.py --dry-run --window weekly` produces a digest
   whose Quality section is byte-identical to the actual Sunday email.
2. `python orchestrator.py --dry-run --window open` produces a digest
   whose Zones section matches (or defers to) the current alert_monitor
   push exactly.
3. Set `NTFY_DISABLED=0` and run manually once during a low-traffic time
   (e.g., Saturday). Confirm exactly one push arrives (the digest-ready
   silent tag). If multiple pushes arrive during a `--window weekly` dry
   run, the `fired` logic is wrong — fix before merging.
4. Test .paused: create `.paused` in the working tree, run the orchestrator,
   confirm digest is written but zero pushes arrive. Delete `.paused`,
   confirm pushes resume.
5. Test JOURNAL_WEBHOOK if configured: tap an action button, confirm the
   response lands in `journal.jsonl` within 10 seconds.

Only after all five pass does the workflow become the primary cron.
Existing `alert_monitor.py` cron stays live in parallel until Phase 4
so nothing regresses.

---

## 9. What Phase 1 is NOT

- NOT a rewrite of the quality screener (frozen).
- NOT a new zone alerter (existing alert_monitor.py stays live).
- NOT PDF ingest (Phase 2).
- NOT congress monitor (Phase 5).
- NOT swing scanner port (Phase 6).
- NOT bench trigger monitoring (later phase per master §9).

Phase 1 is the SKELETON: orchestrator + digest + push helper + one stub
per analyst + config layout + journal + killswitch. Two live wrappers
(quality, zones) that call the existing frozen modules through no-op
adapters. Nothing broken, nothing changed for anyone else.

---

## 10. Definition of done for Phase 1

- [ ] All files in §1 exist and pass their self-tests
- [ ] Workflow file `.github/workflows/orchestrator.yml` runs on the six schedules in §2
- [ ] One full week of dry runs completed with zero errors, zero pushes (dry mode)
- [ ] Amrit chooses topic (existing or new dedicated) and it's in GitHub secrets
- [ ] Journal webhook decided (build now or defer to Phase 2) — either way, action buttons render
- [ ] `.paused` tested end-to-end
- [ ] Verification protocol §8 passes 5/5
- [ ] Merge to main; enable the workflow; existing systems stay live in parallel

Then Phase 2.
