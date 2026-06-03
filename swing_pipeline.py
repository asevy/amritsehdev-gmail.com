"""
swing_pipeline.py  —  THE UNIFIED TOOL
======================================
Finds intraday swings on GOOD stocks, with discipline enforced end to end.

It chains five layers, in the order that protects you:

   GATE 1  Liquidity & size      -> tradeable, not a micro-cap trap
   GATE 2  Fundamental quality   -> profitable / sound balance sheet ("good")
   GATE 3  Forensic filings      -> no going-concern / material-weakness traps
   ------- a name must PASS all three gates to be a candidate -------
   SCORE 1 Daily setup           -> coiled (LOADED) or already moving (MOVING_NOW)
   SCORE 2 Intraday swing        -> RVOL / opening-range break / VWAP (live session)
   SCORE 3 Catalyst timing       -> scheduled earnings/event in the window

Final rank = the swing signal, but ONLY among names that cleared the gates,
with catalyst proximity as a tie-breaker boost. Every candidate carries a
mechanical entry trigger and a stop — no signal is emitted without a stop.

This is the honest synthesis: it cannot predict a pop, but it concentrates your
attention on fundamentally sound names that are coiled or moving with a catalyst
near — and refuses to surface trash, no matter how hard it's ripping.

Run live in your environment with a data feed. Each layer's data function is
swappable. Pieces live in: swing_scanner.py, filing_forensics.py,
catalyst_calendar.py, intraday.py.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, field, asdict
from typing import Optional, Iterable


# ----------------------------------------------------------------------
# GATE 1 + 2: liquidity / size / fundamental quality
# ----------------------------------------------------------------------
@dataclass
class QualityGate:
    min_dollar_volume: float = 20_000_000   # avg daily $ volume — must be liquid
    min_market_cap: float = 2_000_000_000   # no micro-caps (the GRRR rule)
    require_profitable: bool = True          # positive trailing net income
    max_net_debt_to_ebitda: float = 5.0      # not over-levered


def get_fundamentals(ticker: str) -> dict:
    """Return {market_cap, avg_dollar_volume, net_income, net_debt, ebitda}.
    Default via yfinance; swap for your feed. Missing keys -> None."""
    try:
        import yfinance as yf
    except ImportError:
        return {}
    try:
        info = yf.Ticker(ticker).info
        return {
            "market_cap": info.get("marketCap"),
            "avg_dollar_volume": (info.get("averageVolume") or 0)
                                 * (info.get("currentPrice") or info.get("previousClose") or 0),
            "net_income": info.get("netIncomeToCommon"),
            "net_debt": (info.get("totalDebt") or 0) - (info.get("totalCash") or 0),
            "ebitda": info.get("ebitda"),
        }
    except Exception:
        return {}


def passes_quality(f: dict, g: QualityGate) -> tuple[bool, str]:
    if not f:
        return False, "no_fundamentals"
    reasons = []
    if f.get("market_cap") and f["market_cap"] < g.min_market_cap:
        reasons.append("too_small")
    if f.get("avg_dollar_volume") and f["avg_dollar_volume"] < g.min_dollar_volume:
        reasons.append("illiquid")
    if g.require_profitable and (f.get("net_income") or -1) <= 0:
        reasons.append("unprofitable")
    nd, eb = f.get("net_debt"), f.get("ebitda")
    if nd and eb and eb > 0 and nd / eb > g.max_net_debt_to_ebitda:
        reasons.append("over_levered")
    return (len(reasons) == 0), (";".join(reasons) if reasons else "ok")


# ----------------------------------------------------------------------
# The pipeline
# ----------------------------------------------------------------------
@dataclass
class Candidate:
    ticker: str
    price: float = np.nan
    passed_gates: bool = False
    gate_detail: str = ""
    quality: str = ""
    filing_risk: float = np.nan
    filing_flags: str = ""
    daily_setup: str = ""        # LOADED / MOVING_NOW / -
    daily_score: float = 0.0
    intraday_swing: float = np.nan
    catalyst: str = ""
    catalyst_score: float = 0.0
    final_score: float = 0.0
    entry_trigger: float = np.nan
    stop: float = np.nan
    rr: float = np.nan
    verdict: str = ""

    def row(self):
        return asdict(self)


class SwingPipeline:
    def __init__(self,
                 quality_gate: QualityGate = QualityGate(),
                 forensic_form: str = "10-K",
                 exclude: Optional[Iterable[str]] = None,
                 catalyst_horizon: int = 21,
                 # injectable data/scoring functions (swap for your feed in prod)
                 fundamentals_fn=get_fundamentals,
                 forensic_fn=None,
                 daily_scan_fn=None,
                 intraday_fn=None,
                 catalyst_fn=None):
        self.qg = quality_gate
        self.form = forensic_form
        self.exclude = {t.upper() for t in (exclude or [])}
        self.horizon = catalyst_horizon
        self.fundamentals_fn = fundamentals_fn
        self.forensic_fn = forensic_fn
        self.daily_scan_fn = daily_scan_fn
        self.intraday_fn = intraday_fn
        self.catalyst_fn = catalyst_fn

    def evaluate(self, ticker: str,
                 today_bars: Optional[pd.DataFrame] = None,
                 prior_close: Optional[float] = None,
                 intraday_history=None) -> Candidate:
        c = Candidate(ticker=ticker)
        if ticker.upper() in self.exclude:
            c.verdict = "excluded_forever_hold"
            return c

        # GATE 1+2: quality / liquidity / size
        f = self.fundamentals_fn(ticker) if self.fundamentals_fn else {}
        ok_q, why_q = passes_quality(f, self.qg)
        c.quality = why_q

        # GATE 3: forensic filings
        if self.forensic_fn:
            rep = self.forensic_fn(ticker, form=self.form)
            c.filing_risk = getattr(rep, "risk_score", np.nan)
            hits = getattr(rep, "hits", [])
            c.filing_flags = "; ".join(getattr(h, "label", str(h)) for h in hits[:3])
        ok_forensic = (np.isnan(c.filing_risk) or c.filing_risk < 9)  # >=9 = serious

        c.passed_gates = bool(ok_q and ok_forensic)
        c.gate_detail = ("clean" if c.passed_gates
                         else f"quality:{why_q}|filing_risk:{c.filing_risk}")

        # SCORE 1: daily setup
        if self.daily_scan_fn:
            d = self.daily_scan_fn(ticker)   # expected: dict with scores+entry+stop
            c.price = d.get("price", np.nan)
            mn, ld = d.get("moving_now", 0), d.get("loaded", 0)
            if ld >= mn:
                c.daily_setup, c.daily_score = ("LOADED" if ld >= 60 else "-"), ld
            else:
                c.daily_setup, c.daily_score = ("MOVING_NOW" if mn >= 60 else "-"), mn
            c.entry_trigger = d.get("entry_trigger", np.nan)
            c.stop = d.get("stop", np.nan)
            c.rr = d.get("rr_to_high", np.nan)

        # SCORE 2: intraday swing (if live bars provided)
        if self.intraday_fn and today_bars is not None:
            isig = self.intraday_fn(today_bars, ticker=ticker,
                                    prior_close=prior_close,
                                    intraday_history=intraday_history)
            c.intraday_swing = getattr(isig, "swing_score", np.nan)
            # intraday entry/stop override daily when in-session
            if not np.isnan(getattr(isig, "entry_trigger", np.nan)):
                c.entry_trigger = isig.entry_trigger
                c.stop = isig.stop
                c.rr = isig.rr

        # SCORE 3: catalyst timing
        if self.catalyst_fn:
            cs, clabel = self.catalyst_fn(ticker, self.horizon)
            c.catalyst_score, c.catalyst = cs, clabel

        # FINAL: only gated-clean names get a real score
        swing = np.nanmax([c.intraday_swing if not np.isnan(c.intraday_swing) else 0,
                           c.daily_score])
        if not c.passed_gates:
            c.final_score = 0.0
            c.verdict = "FILTERED_OUT-" + c.gate_detail
        else:
            # swing is the engine; catalyst gives up to +20% boost as tie-breaker
            c.final_score = round(float(swing * (1 + 0.2 * c.catalyst_score / 100)), 1)
            if np.isnan(c.rr) or c.rr is None:
                c.verdict = "clean-need-rr"
            elif c.rr < 1:
                c.verdict = "clean-but-poor-R:R-wait"
            elif swing >= 60:
                c.verdict = "ACTIONABLE-clean-setup"
            else:
                c.verdict = "watch-clean-no-trigger-yet"
        return c

    def run(self, tickers: Iterable[str], intraday_feed=None) -> pd.DataFrame:
        """intraday_feed(ticker) -> (today_bars, prior_close, intraday_history) or None."""
        rows = []
        for t in tickers:
            tb = pc = hist = None
            if intraday_feed:
                got = intraday_feed(t)
                if got:
                    tb, pc, hist = got
            rows.append(self.evaluate(t, today_bars=tb, prior_close=pc,
                                      intraday_history=hist).row())
        df = pd.DataFrame(rows)
        if len(df):
            df = df.sort_values(["passed_gates", "final_score"],
                                ascending=[False, False]).reset_index(drop=True)
        return df


# ----------------------------------------------------------------------
# Self-test: wire synthetic stand-ins for every layer (no network)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # fake fundamentals: GOODCO solid, JUNKCO tiny/unprofitable, TRAPCO ok size
    FUND = {
        "GOODCO": {"market_cap": 5e10, "avg_dollar_volume": 5e8,
                   "net_income": 2e9, "net_debt": 1e9, "ebitda": 6e9},
        "JUNKCO": {"market_cap": 4e8, "avg_dollar_volume": 5e6,
                   "net_income": -1e8, "net_debt": 2e8, "ebitda": -5e7},
        "TRAPCO": {"market_cap": 8e9, "avg_dollar_volume": 1e8,
                   "net_income": 3e8, "net_debt": 1e9, "ebitda": 2e9},
    }
    class _Rep:
        def __init__(self, risk, hits): self.risk_score, self.hits = risk, hits
    class _Hit:
        def __init__(self, label): self.label = label
    FILINGS = {  # TRAPCO has a going-concern flag despite being big enough
        "GOODCO": _Rep(0, []),
        "JUNKCO": _Rep(4, [_Hit("Dilution")]),
        "TRAPCO": _Rep(11, [_Hit("Going-concern / survival doubt")]),
    }
    DAILY = {  # GOODCO coiled+moving, TRAPCO ripping, JUNKCO ripping
        "GOODCO": {"price": 200, "moving_now": 72, "loaded": 65,
                   "entry_trigger": 203, "stop": 192, "rr_to_high": 1.6},
        "JUNKCO": {"price": 20, "moving_now": 95, "loaded": 10,
                   "entry_trigger": 21, "stop": 18, "rr_to_high": 0.5},
        "TRAPCO": {"price": 50, "moving_now": 88, "loaded": 20,
                   "entry_trigger": 51, "stop": 47, "rr_to_high": 1.4},
    }
    def fnd(t, **k): return FUND.get(t, {})
    def frn(t, form="10-K"): return FILINGS.get(t, _Rep(np.nan, []))
    def dly(t): return DAILY.get(t, {})
    def cat(t, h): return (96.0, "earnings in 3d") if t == "GOODCO" else (0.0, "")

    pipe = SwingPipeline(fundamentals_fn=fnd, forensic_fn=frn,
                         daily_scan_fn=dly, intraday_fn=None, catalyst_fn=cat,
                         exclude={"XEQT"})
    df = pipe.run(["GOODCO", "JUNKCO", "TRAPCO", "XEQT"])
    cols = ["ticker", "passed_gates", "quality", "filing_risk", "daily_setup",
            "daily_score", "catalyst", "final_score", "rr", "verdict"]
    pd.set_option("display.width", 170, "display.max_columns", 20)
    print(df[cols].to_string(index=False))
