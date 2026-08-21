"""
orchestrator_skeleton.py -- the dispatch pattern for the mega system.

Reads: config/master_watchlist_input.txt (list of tickers, one per line)
       .paused (presence file = vacation mode; if present, skip run entirely)
Dispatches to: registered analysts (quality, junior, congress, swing,
       research, filing_regate). Each analyst is a callable that returns
       a `SectionReport` with lines (list of strings) plus a `fired` bool.
Aggregates: SectionReports into one Digest.
Emits: Digest as markdown to digests/YYYY-MM-DD-HHmm.md, plus one ntfy
       push per fired-priority section, plus one silent digest-ready push.

DESIGN
------
- Analysts are pure callables: `analyst(context) -> SectionReport`. No side
  effects inside the analyst. Orchestrator handles all I/O.
- Silence-is-data: every section MUST return a SectionReport even when it
  found nothing. Missing sections in the digest = a bug, not silence.
- Killswitch: if `.paused` exists, orchestrator writes a "paused" line to
  the digest and exits without pushing. Data collection still happens
  (the analysts still run) so nothing is lost — only pushes are silenced.
- Errors in one analyst do not stop the run. They become a section with
  fired=False and lines=[f"ERROR: {exc}"]. The daily digest surfaces the
  error but the other analysts still report.

TO INTEGRATE ON THE MACBOOK
---------------------------
1. Replace the stub analysts with real ones:
   - quality_analyst  -> wraps quality_value_screener (do NOT modify it)
   - junior_analyst   -> new, per Junior_Miner_Screener_Spec_v1.2.md
   - congress_analyst -> new, per Congressional_Disclosure_Monitor_Spec_v1.md
   - swing_analyst    -> port from asevy/amritsehdev-gmail.com with the 3 fixes
   - research_analyst -> reads pdf_inbox/, updates dossiers/<TICKER>/
   - filing_regate    -> EDGAR RSS for held names, re-runs 6 gates
2. Set env: NTFY_TOPIC, JOURNAL_WEBHOOK, DIGEST_BASE_URL.
3. Wire into GitHub Actions cron per PHASE_1_SPEC.md schedule table.
"""
from __future__ import annotations
import os
import sys
import json
import logging
import traceback
import datetime as dt
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Optional

# adjust import when migrating to ~/investing/
try:
    from ntfy_publish import push, DIGEST, SILENCE, ZONE, CLUSTER, GATE_BREAK
except ImportError:
    # fallback stub for self-test in this staging repo
    DIGEST, SILENCE, ZONE, CLUSTER, GATE_BREAK = 2, 2, 4, 4, 5
    def push(prio, title, body, **_): return True

log = logging.getLogger("orchestrator")


# ---- data shapes ---------------------------------------------------------
@dataclass
class Context:
    """Passed to every analyst. All shared read-only inputs live here."""
    watchlist: list[str]
    now: dt.datetime
    cron_window: str            # "pre_market" / "open" / "midday" / "close" / "after_hours" / "weekly"
    pdf_inbox_dir: Path
    dossiers_dir: Path


@dataclass
class SectionReport:
    """Every analyst returns one of these. Silence = fired=False + lines describing why."""
    name: str
    lines: list[str] = field(default_factory=list)
    fired: bool = False
    push_priority: Optional[int] = None
    push_title: Optional[str] = None
    push_body: Optional[str] = None


@dataclass
class Digest:
    date: dt.date
    cron_window: str
    sections: list[SectionReport] = field(default_factory=list)

    def to_markdown(self) -> str:
        out = [f"# Digest — {self.date.isoformat()} — {self.cron_window}", ""]
        for s in self.sections:
            marker = "🔔" if s.fired else "·"
            out.append(f"## {marker} {s.name}")
            for line in s.lines:
                out.append(line)
            out.append("")
        return "\n".join(out)


# ---- orchestrator --------------------------------------------------------
def run(analysts: list[Callable[[Context], SectionReport]],
        ctx: Context,
        digests_dir: Path,
        pause_file: Path = Path(".paused")) -> Digest:
    digest = Digest(date=ctx.now.date(), cron_window=ctx.cron_window)

    paused = pause_file.exists()
    if paused:
        note = f"PAUSED (vacation mode). {pause_file.read_text().strip() or 'no reason given'}"
        log.info(note)

    for fn in analysts:
        section = _safe_call(fn, ctx)
        digest.sections.append(section)

    # write markdown archive (always, even when paused — data record matters)
    digests_dir.mkdir(parents=True, exist_ok=True)
    stamp = ctx.now.strftime("%Y-%m-%d-%H%M")
    (digests_dir / f"{stamp}.md").write_text(digest.to_markdown())

    if paused:
        log.info("digest written; skipping pushes due to .paused")
        return digest

    # push fired sections
    fired_any = False
    for s in digest.sections:
        if s.fired and s.push_priority is not None:
            push(s.push_priority,
                 title=s.push_title or s.name,
                 body=s.push_body or "\n".join(s.lines[:10]))
            fired_any = True

    # end-of-run summary push (silent tag)
    n_fired = sum(1 for s in digest.sections if s.fired)
    summary = f"{n_fired}/{len(digest.sections)} sections fired"
    if not fired_any:
        summary = f"Silence — {len(digest.sections)} sections quiet."
    push(DIGEST, title=f"Digest ready — {ctx.cron_window}", body=summary)

    return digest


def _safe_call(fn: Callable[[Context], SectionReport], ctx: Context) -> SectionReport:
    name = getattr(fn, "__name__", "unknown")
    try:
        return fn(ctx)
    except Exception:
        tb = traceback.format_exc(limit=3)
        log.error("analyst %s failed: %s", name, tb)
        return SectionReport(name=name,
                             lines=[f"ERROR: analyst crashed. Traceback:", tb],
                             fired=False)


# ---- stub analysts for self-test ----------------------------------------
def _stub_quality_analyst(ctx: Context) -> SectionReport:
    """Wraps the frozen quality_value_screener.py output. In this stub we
    fake a "4 of 312" survivors output matching the actual live digest
    format seen in the master prompt screenshot."""
    survivors = ["B 74  ADBE   B:B A:B- D:A-",
                 "B- 70  MO     B:B+ A:B D:C"]
    return SectionReport(
        name="Quality analyst (Sunday screener wrap)",
        lines=[f"QUALITY-VALUE — {len(survivors)} survivor(s) of 312:"] + survivors,
        fired=False,   # weekly, not a push event
        push_priority=None,
    )


def _stub_zone_analyst(ctx: Context) -> SectionReport:
    """Wraps the existing alert_monitor.py output. Reports zones in-range."""
    zone_hits = []
    if "GOOGL" in ctx.watchlist:
        zone_hits.append("ZONE GOOGL 340.67 (<= 355) — half now; half post-print ~Jul 23")
    if "META" in ctx.watchlist:
        zone_hits.append("ZONE META 545.83 (<= 650) — half now; half post-print ~Jul 29")
    if not zone_hits:
        return SectionReport(name="Zone alerter", lines=["no zones in range."])
    return SectionReport(
        name="Zone alerter",
        lines=zone_hits,
        fired=True,
        push_priority=ZONE,
        push_title=f"{len(zone_hits)} zone alert(s)",
        push_body="\n".join(zone_hits),
    )


def _stub_congress_analyst(ctx: Context) -> SectionReport:
    return SectionReport(
        name="Congress monitor",
        lines=["INSIDER CLUSTERS: none"],
        fired=False,
    )


def _stub_junior_analyst(ctx: Context) -> SectionReport:
    return SectionReport(
        name="Junior miner screener",
        lines=["AE.V — Class C, next review 2026-08-27 (Q2 filing).",
               "No new candidates cleared 10 gates."],
        fired=False,
    )


def _stub_filing_regate(ctx: Context) -> SectionReport:
    return SectionReport(
        name="Filing-day re-gate (held names)",
        lines=["No new 10-K/10-Q for held names since last run."],
        fired=False,
    )


# ---- self-test (offline, no ntfy, no filesystem writes outside tmp) -----
if __name__ == "__main__":
    import tempfile

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    os.environ["NTFY_DISABLED"] = "1"   # kill push in self-test

    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        ctx = Context(
            watchlist=["GOOGL", "META", "MSFT", "LMT", "CPRT", "RACE", "LIN", "LLY"],
            now=dt.datetime(2026, 8, 20, 15, 45, tzinfo=dt.timezone.utc),
            cron_window="close",
            pdf_inbox_dir=tmp / "pdf_inbox",
            dossiers_dir=tmp / "dossiers",
        )
        analysts = [_stub_quality_analyst, _stub_zone_analyst,
                    _stub_congress_analyst, _stub_junior_analyst,
                    _stub_filing_regate]
        digest = run(analysts, ctx, digests_dir=tmp / "digests")

        md = digest.to_markdown()
        print(md)
        print("=" * 60)

        # assertions
        assert digest.date == dt.date(2026, 8, 20)
        assert len(digest.sections) == 5, "should have exactly 5 stub sections"
        fired = [s for s in digest.sections if s.fired]
        assert len(fired) == 1, "only the zone-alerter stub should have fired"
        assert fired[0].name == "Zone alerter"
        assert "GOOGL" in md and "META" in md
        assert "INSIDER CLUSTERS: none" in md, "silence-is-data preserved"

        # paused test
        (tmp / ".paused").write_text("vacation until Aug 25")
        # switch cwd for the pause_file relative path in run()
        # simpler: call run with explicit pause_file
        digest2 = run(analysts, ctx, digests_dir=tmp / "digests",
                      pause_file=tmp / ".paused")
        md2 = digest2.to_markdown()
        # sections still populated (data collection continues)
        assert len(digest2.sections) == 5

        print("All orchestrator self-tests passed.")
