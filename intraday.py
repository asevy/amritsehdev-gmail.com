"""
intraday.py
===========
Intraday swing-detection engine. Daily bars tell you what coiled overnight;
THESE signals tell you a swing is firing during the session, using the same
toolkit professional intraday traders rely on:

  - RVOL (relative volume)  : cumulative volume so far today vs the average
                              cumulative volume at this SAME time of day over the
                              trailing N sessions. RVOL > ~2 by mid-morning =
                              unusual participation = something is happening.
                              This is the single most useful intraday signal.
  - Opening Range Breakout  : the high/low of the first `or_minutes` minutes.
                              A break (with volume) is a classic, mechanical
                              entry trigger with a built-in stop (the other side
                              of the range).
  - VWAP                    : volume-weighted average price. Holding above VWAP =
                              buyers in control; losing it = momentum failing.
  - Gap                     : today's open vs prior close, and whether the gap
                              is being held or faded.

DATA: needs intraday bars (1m or 5m), columns: open, high, low, close, volume,
indexed by timestamp. yfinance gives ~60d of 5m / ~7d of 1m for free; a
brokerage API is better for production. Pass `prior_closes` / `intraday_history`
for RVOL baselines.

These DETECT a forming swing and hand you a mechanical entry + stop. They do not
predict direction before the move — they catch it early with discipline attached.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class IntradaySignal:
    ticker: str
    last: float = np.nan
    vwap: float = np.nan
    above_vwap: bool = False
    rvol: float = np.nan            # cumulative-volume relative volume
    gap_pct: float = np.nan         # open vs prior close
    or_high: float = np.nan         # opening-range high
    or_low: float = np.nan          # opening-range low
    or_broke_up: bool = False
    or_broke_dn: bool = False
    intraday_ret: float = np.nan    # open -> last
    swing_score: float = 0.0        # 0..100
    entry_trigger: float = np.nan   # ORB-high breakout level
    stop: float = np.nan            # other side of OR (or VWAP) - mechanical
    rr: float = np.nan
    flags: str = ""


def vwap(bars: pd.DataFrame) -> pd.Series:
    tp = (bars["high"] + bars["low"] + bars["close"]) / 3
    return (tp * bars["volume"]).cumsum() / bars["volume"].cumsum().replace(0, np.nan)


def opening_range(bars: pd.DataFrame, or_minutes: int = 15,
                  bar_minutes: int = 5) -> tuple[float, float]:
    n = max(1, or_minutes // bar_minutes)
    o = bars.iloc[:n]
    return float(o["high"].max()), float(o["low"].min())


def relative_volume(today_bars: pd.DataFrame,
                    intraday_history: Optional[list[pd.DataFrame]]) -> float:
    """Cumulative volume so far today / average cumulative volume at the same
    number of bars into the day over prior sessions."""
    n = len(today_bars)
    cum_today = float(today_bars["volume"].sum())
    if not intraday_history:
        return np.nan
    base = []
    for day in intraday_history:
        if len(day) >= n:
            base.append(float(day["volume"].iloc[:n].sum()))
    if not base:
        return np.nan
    avg = np.mean(base)
    return float(cum_today / avg) if avg > 0 else np.nan


def analyze_intraday(today_bars: pd.DataFrame, ticker: str = "",
                     prior_close: Optional[float] = None,
                     intraday_history: Optional[list[pd.DataFrame]] = None,
                     or_minutes: int = 15, bar_minutes: int = 5,
                     atr_like: Optional[float] = None) -> IntradaySignal:
    sig = IntradaySignal(ticker=ticker)
    if today_bars is None or len(today_bars) < 2:
        sig.flags = "insufficient_intraday_data"
        return sig

    last = float(today_bars["close"].iloc[-1])
    opn = float(today_bars["open"].iloc[0])
    vw = float(vwap(today_bars).iloc[-1])
    orh, orl = opening_range(today_bars, or_minutes, bar_minutes)
    rvol = relative_volume(today_bars, intraday_history)
    gap = (opn / prior_close - 1.0) if prior_close else np.nan
    intra_ret = last / opn - 1.0

    sig.last, sig.vwap, sig.above_vwap = last, vw, last > vw
    sig.rvol, sig.gap_pct = rvol, gap
    sig.or_high, sig.or_low = orh, orl
    sig.or_broke_up = last > orh
    sig.or_broke_dn = last < orl
    sig.intraday_ret = intra_ret

    # ---- swing score: confluence of volume + breakout + trend ----
    sc = 0.0
    if not np.isnan(rvol):
        sc += np.clip((rvol - 1) / 3, 0, 1) * 40      # up to 40 for RVOL up to ~4x
    if sig.or_broke_up:
        sc += 25                                       # broke the opening range up
    if sig.above_vwap:
        sc += 20                                       # buyers in control
    sc += np.clip(intra_ret / 0.05, 0, 1) * 15        # up to 15 for a strong day
    if sig.or_broke_dn and not sig.above_vwap:
        sc *= 0.4                                       # breaking DOWN: not a long setup
    sig.swing_score = round(float(sc), 1)

    # ---- mechanical entry + stop (discipline enforced) ----
    sig.entry_trigger = round(orh * 1.0005, 2)         # confirmed ORB long
    # stop: the tighter-risk of OR-low or VWAP, floored by an ATR-like buffer
    candidate_stop = max(orl, vw * 0.997)
    if atr_like:
        candidate_stop = min(candidate_stop, last - 0.5 * atr_like)
    sig.stop = round(candidate_stop, 2)
    risk = last - sig.stop
    # reward proxy: a measured move = the opening-range height projected up
    reward = (orh - orl)
    sig.rr = round(reward / risk, 2) if risk > 0 else np.nan

    notes = []
    if not np.isnan(rvol) and rvol >= 2:
        notes.append(f"RVOL{rvol:.1f}x")
    if sig.or_broke_up:
        notes.append("ORB-up")
    if sig.above_vwap:
        notes.append("above-VWAP")
    if not np.isnan(gap) and abs(gap) >= 0.03:
        notes.append(f"gap{gap*100:+.0f}%")
    if not np.isnan(sig.rr) and sig.rr < 1:
        notes.append("poor-R:R")
    if sig.or_broke_dn:
        notes.append("breaking-DOWN-not-long")
    sig.flags = ";".join(notes)
    return sig


# ----------------------------------------------------------------------
# Self-test with synthetic intraday bars (no feed needed)
# ----------------------------------------------------------------------
def _synth_day(kind: str, bars: int = 78, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2026-06-02 09:30", periods=bars, freq="5min")
    if kind == "breakout":      # tight open, then trend up hard on volume
        base = 100 + np.r_[rng.normal(0, 0.05, 6), np.linspace(0, 6, bars - 6)] \
               + rng.normal(0, 0.08, bars)
        vol = np.r_[rng.normal(8e4, 1e4, 6), rng.normal(3e5, 4e4, bars - 6)]
    elif kind == "fade":        # gaps up, fades below vwap
        base = 100 + np.r_[np.linspace(3, 0, bars)] + rng.normal(0, 0.1, bars)
        vol = rng.normal(1.2e5, 2e4, bars)
    else:                        # chop
        base = 100 + rng.normal(0, 0.3, bars).cumsum() * 0.1
        vol = rng.normal(9e4, 1e4, bars)
    close = base
    high = close + np.abs(rng.normal(0, 0.05, bars))
    low = close - np.abs(rng.normal(0, 0.05, bars))
    open_ = np.r_[close[0], close[:-1]]
    return pd.DataFrame({"open": open_, "high": high, "low": low,
                         "close": close, "volume": np.abs(vol)}, index=idx)


if __name__ == "__main__":
    # build a few prior sessions for the RVOL baseline
    hist = [_synth_day("chop", seed=i) for i in range(10, 20)]
    for kind, seed in [("breakout", 1), ("fade", 2), ("chop", 3)]:
        # partial day: only first 20 bars elapsed (~mid-morning)
        day = _synth_day(kind, seed=seed).iloc[:20]
        prior = 100.0
        s = analyze_intraday(day, ticker=f"{kind.upper()}_DEMO",
                             prior_close=prior, intraday_history=hist, atr_like=1.5)
        print(f"{s.ticker:16} swing={s.swing_score:5.1f}  rvol="
              f"{s.rvol:4.1f}  last={s.last:6.2f} vwap={s.vwap:6.2f}  "
              f"entry={s.entry_trigger:6.2f} stop={s.stop:6.2f} rr={s.rr}  {s.flags}")
