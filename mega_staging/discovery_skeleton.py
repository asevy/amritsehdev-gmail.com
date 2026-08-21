"""
discovery_skeleton.py -- Phase 1.5 discovery analyst skeleton.

STRICT-WITH-FLAG (per Amrit decision 2026-08-20):
- Discovery reports new gate-passers OUTSIDE the pre-registered 312 universe.
- Never auto-promotes into the 312 (protects the July 20 2027 judgment).
- Emits FLAGS on near-passers (1 gate fail) with mandatory citations.
- Max 2 flags per quarterly run.
- Every flag defaults to `pending_amrit`.

REUSE CONTRACT:
- Discovery must import gate logic from the frozen quality_value_screener,
  never reimplement it. The frozen module is expected to expose:

      def run_six_gates(fundamentals) -> GateResult

  If it doesn't, the MacBook agent's first task is to add a thin wrapper
  (not a methodology change).

- This skeleton uses a stub `run_six_gates` for the self-test.

USAGE PATTERN ON THE MACBOOK:
    from quality_value_screener import run_six_gates  # real import
    from discovery import run_discovery

    passers, flags = run_discovery(
        universe=broad_us_universe(min_mcap=2e9, min_advol=2e7),
        already_tracked={"AAPL","MSFT",...},   # the 312-name universe
        run_six_gates=run_six_gates,
        fetch_fundamentals=your_fundamentals_fetcher,
        max_flags=2,
    )
"""
from __future__ import annotations
import time
import uuid
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional

log = logging.getLogger("discovery")


# ------------------------------------------------------------------
# Data shapes -- the contract with the frozen screener
# ------------------------------------------------------------------
@dataclass
class Fundamentals:
    """What the discovery layer feeds into the six-gate function.
    Must match the shape the frozen screener expects."""
    ticker: str
    market_cap: float
    avg_dollar_volume: float
    roic: float               # gate 1: >= 0.15
    gross_margin: float       # gate 2: >= 0.40 (stable check separate)
    gross_margin_series: list[float]  # for stability check
    fcf: float                # gate 3: fcf >= net_income
    net_income: float
    dilution_pct_12mo: float  # gate 4: shares outstanding change (split-adj, filed-date normalized)
    interest_coverage: float  # gate 5: >= 8
    fcf_yield: float          # gate 6: >= 0.045


@dataclass
class GateResult:
    """What the frozen six-gate function returns."""
    passed: bool
    detail: dict           # {"roic": (True, 0.314), "gross_margin": (True, 0.604), ...}


@dataclass
class AnalystFlag:
    ticker: str
    failed_gate: str
    failure_value: str
    citation: str
    rationale: str
    status: str = "pending_amrit"
    raised_ts: int = field(default_factory=lambda: int(time.time()))
    resolved_ts: Optional[int] = None
    outcome_12mo: Optional[str] = None
    flag_id: str = field(default_factory=lambda: f"flg_{uuid.uuid4().hex[:8]}")


@dataclass
class DiscoveryOutput:
    universe_size: int
    passers: list[str]                 # new gate-passers not in already_tracked
    passer_tags: dict[str, list[str]]  # ticker -> list of tags
    flags: list[AnalystFlag]
    silence_note: Optional[str] = None


# ------------------------------------------------------------------
# The discovery layer itself
# ------------------------------------------------------------------
def run_discovery(
    universe: list[str],
    already_tracked: set[str],
    run_six_gates: Callable[[Fundamentals], GateResult],
    fetch_fundamentals: Callable[[str], Optional[Fundamentals]],
    tag_lookup: Callable[[str], list[str]] = lambda t: [],
    max_flags: int = 2,
    rationale_fn: Optional[Callable[[str, GateResult, Fundamentals], Optional[AnalystFlag]]] = None,
) -> DiscoveryOutput:
    """Screen the broader universe, report NEW passers + up to `max_flags` near-passers.

    Args:
        universe: list of tickers to screen this quarter (~2000-3000 names)
        already_tracked: the pre-registered 312 (or whatever the current universe is)
        run_six_gates: the frozen gate function -- MUST come from quality_value_screener
        fetch_fundamentals: your data adapter (yfinance, brokerage feed, whatever)
        tag_lookup: given a ticker, return list of tags for grouping
        max_flags: hard cap on flags per run (defaults to 2 per SPEC §5)
        rationale_fn: optional analyst-rationale generator for near-passers.
                      Signature: (ticker, gate_result, fundamentals) -> Optional[AnalystFlag].
                      Return None to skip flagging. If omitted, no flags emitted.

    Returns:
        DiscoveryOutput with new passers, tags per passer, and flags.
    """
    passers = []
    tags = {}
    candidate_flags: list[AnalystFlag] = []
    excluded_no_data = 0
    excluded_already_tracked = 0

    for t in universe:
        if t in already_tracked:
            excluded_already_tracked += 1
            continue
        f = fetch_fundamentals(t)
        if f is None:
            excluded_no_data += 1
            continue

        gr = run_six_gates(f)

        if gr.passed:
            passers.append(t)
            tags[t] = tag_lookup(t)
            continue

        # near-pass: exactly ONE gate failed -> candidate for flag
        n_failed = sum(1 for (ok, _) in gr.detail.values() if not ok)
        if n_failed == 1 and rationale_fn is not None:
            flag = rationale_fn(t, gr, f)
            if flag is not None:
                _assert_flag_shape(flag)
                candidate_flags.append(flag)
        # if n_failed >= 2 -> never flag. Structure trumps story.

    # cap flags at max_flags. If rationale_fn returned them in order of
    # strength, we take the first N; otherwise sort by hash for stability.
    flags = candidate_flags[:max_flags]
    if len(candidate_flags) > max_flags:
        log.info("discovery: %d candidate flags emitted, capped to %d",
                 len(candidate_flags), max_flags)

    silence_note = None
    if not passers and not flags:
        silence_note = (f"No new passers, no flags. Universe scanned: {len(universe)}. "
                        f"Silence is data.")

    return DiscoveryOutput(
        universe_size=len(universe),
        passers=passers,
        passer_tags=tags,
        flags=flags,
        silence_note=silence_note,
    )


def _assert_flag_shape(flag: AnalystFlag) -> None:
    """Refuse to ship a flag missing any of the five mandatory fields."""
    missing = [name for name in ("ticker", "failed_gate", "failure_value",
                                  "citation", "rationale")
               if not (getattr(flag, name) or "").strip()]
    if missing:
        raise ValueError(f"AnalystFlag missing mandatory fields: {missing}. "
                         f"Refusing to emit unverified flag.")
    if len(flag.rationale) > 300:
        raise ValueError(f"AnalystFlag rationale exceeds 300 chars "
                         f"({len(flag.rationale)}); trim before emitting.")


def format_discovery_section(out: DiscoveryOutput,
                             rollups: Optional[list[dict]] = None) -> list[str]:
    """Render the discovery output as digest lines. If rollups=[{"by": "sector"}, ...]
    is provided, group passers by each tag rollup."""
    lines = [f"DISCOVERY — universe scanned: {out.universe_size} names"]
    if out.silence_note:
        lines.append(out.silence_note)
        return lines

    lines.append(f"  New six-gate passers (not in pre-registered 312): {len(out.passers)}")

    if rollups:
        for r in rollups:
            key = r.get("by")
            if not key:
                continue
            groups: dict[str, list[str]] = {}
            for t in out.passers:
                bucket = _tag_value(out.passer_tags.get(t, []), key) or "unclassified"
                groups.setdefault(bucket, []).append(t)
            lines.append(f"  Grouped by {key}:")
            for bucket, ts in sorted(groups.items()):
                lines.append(f"    {bucket:20s}  ({len(ts)}) {', '.join(ts[:8])}"
                             + (" ..." if len(ts) > 8 else ""))
    else:
        for t in out.passers[:20]:
            lines.append(f"    {t}  tags: {','.join(out.passer_tags.get(t, [])) or 'none'}")

    if out.flags:
        lines.append("")
        lines.append(f"  Analyst flags ({len(out.flags)} — near-passers with rationale):")
        for f in out.flags:
            lines.append(f"    {f.ticker}  fails: {f.failed_gate} ({f.failure_value})")
            lines.append(f"      rationale: {f.rationale}")
            lines.append(f"      citation:  {f.citation}")
            lines.append(f"      status:    {f.status}  ({f.flag_id})")
    else:
        lines.append("  Analyst flags: none this quarter.")
    return lines


def _tag_value(tags: list[str], key: str) -> Optional[str]:
    """Given tags like ['sector:tech', 'size:mega'], return the value for `key`."""
    prefix = f"{key}:"
    for t in tags:
        if t.startswith(prefix):
            return t[len(prefix):]
    return None


# ------------------------------------------------------------------
# Self-test with a synthetic universe
# ------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # ---- fake frozen gate function (for self-test only) -------------
    def fake_run_six_gates(f: Fundamentals) -> GateResult:
        detail = {
            "roic":            (f.roic >= 0.15, f.roic),
            "gross_margin":    (f.gross_margin >= 0.40, f.gross_margin),
            "fcf_gte_ni":      (f.fcf >= f.net_income, f.fcf / max(f.net_income, 1)),
            "no_dilution":     (f.dilution_pct_12mo <= 0.05, f.dilution_pct_12mo),
            "int_coverage":    (f.interest_coverage >= 8, f.interest_coverage),
            "fcf_yield":       (f.fcf_yield >= 0.045, f.fcf_yield),
        }
        return GateResult(passed=all(ok for ok, _ in detail.values()), detail=detail)

    # ---- synthetic universe -----------------------------------------
    FUNDS = {
        # New passers (not in already_tracked)
        "SYN1": Fundamentals("SYN1", 5e10, 3e8, 0.22, 0.55, [0.53,0.54,0.55], 8e9, 6e9, 0.01, 45, 0.055),
        "SYN2": Fundamentals("SYN2", 3e10, 2e8, 0.18, 0.48, [0.47,0.48,0.48], 4e9, 3e9, 0.02, 22, 0.048),
        # Near-passer: fails only fcf_yield
        "NEAR": Fundamentals("NEAR", 8e10, 5e8, 0.20, 0.60, [0.59,0.60,0.60], 5e9, 4e9, 0.01, 100, 0.041),
        # Multi-gate failer (should NOT be flagged)
        "BAD":  Fundamentals("BAD", 2e10, 1e8, 0.08, 0.30, [0.28,0.29,0.30], 1e9, 2e9, 0.10, 3, 0.02),
        # Already tracked (in the 312) -- must be excluded
        "OLD":  Fundamentals("OLD", 1e11, 8e8, 0.25, 0.65, [0.64,0.65,0.65], 12e9, 8e9, 0.01, 200, 0.06),
    }
    tag_data = {
        "SYN1": ["sector:tech", "theme:ai-infra", "size:mega"],
        "SYN2": ["sector:health", "size:large"],
        "NEAR": ["sector:tech", "theme:core", "size:mega"],
        "BAD":  ["sector:energy", "size:mid"],
    }
    already = {"OLD"}

    # ---- rationale function (for near-passer NEAR) ------------------
    def rationale(ticker, gr, fundamentals):
        # only flag if we can produce a real citation + rationale
        if ticker != "NEAR":
            return None
        return AnalystFlag(
            ticker=ticker,
            failed_gate="fcf_yield",
            failure_value=f"{fundamentals.fcf_yield:.1%} vs 4.5% threshold",
            citation="SYNTHETIC 10-K FY2025 p.23 (cash flow statement)",
            rationale=("Balance sheet holds $180B cash. Ex-cash FCF yield is 5.8%, "
                       "above threshold. Cash is not being deployed but is available."),
        )

    out = run_discovery(
        universe=list(FUNDS.keys()),
        already_tracked=already,
        run_six_gates=fake_run_six_gates,
        fetch_fundamentals=lambda t: FUNDS.get(t),
        tag_lookup=lambda t: tag_data.get(t, []),
        max_flags=2,
        rationale_fn=rationale,
    )

    # ---- assertions -------------------------------------------------
    assert "SYN1" in out.passers and "SYN2" in out.passers, "should surface both synth passers"
    assert "OLD" not in out.passers, "already-tracked names must be excluded"
    assert "BAD" not in out.passers, "multi-gate failer must not pass"
    assert len(out.flags) == 1, "should have exactly 1 flag (NEAR)"
    assert out.flags[0].ticker == "NEAR"
    assert out.flags[0].status == "pending_amrit"

    # multi-gate failer should NOT produce a flag even if rationale offered
    def eager_rationale(ticker, gr, fundamentals):
        return AnalystFlag(
            ticker=ticker, failed_gate="everything",
            failure_value="lots", citation="none",
            rationale="trust me")
    out2 = run_discovery(
        universe=["BAD"],
        already_tracked=set(),
        run_six_gates=fake_run_six_gates,
        fetch_fundamentals=lambda t: FUNDS.get(t),
        rationale_fn=eager_rationale,
    )
    assert len(out2.flags) == 0, "multi-gate failer must not be flagged, ever"

    # bad flag shape should be rejected at emit time
    def bad_rationale(ticker, gr, fundamentals):
        return AnalystFlag(ticker=ticker, failed_gate="fcf_yield",
                           failure_value="4.1%", citation="",  # missing
                           rationale="vibes")
    try:
        run_discovery(universe=["NEAR"], already_tracked=set(),
                      run_six_gates=fake_run_six_gates,
                      fetch_fundamentals=lambda t: FUNDS.get(t),
                      rationale_fn=bad_rationale)
        raise AssertionError("expected ValueError for missing citation")
    except ValueError as e:
        print(f"  ok  refused unverified flag: {e}")

    # render
    print()
    for line in format_discovery_section(out, rollups=[{"by": "sector"}, {"by": "size"}]):
        print(line)

    print("\nAll discovery skeleton self-tests passed.")
