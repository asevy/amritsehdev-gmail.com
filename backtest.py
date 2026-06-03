"""
backtest.py -- walk-forward backtest of swing_scanner signals.

Replays LOADED and MOVING_NOW signals over historical OHLCV, simulates
breakout-confirmation entry with the scanner's ATR stop and a 2R target,
and reports expectancy by signal type. This is the honest test of edge
before real money: if expectancy is not positive across a meaningful
sample, the scanner is not a reason to trade.

Entry/exit model (conservative):
  - On a signal bar, the breakout level `entry_trigger` arms.
  - Fill in the next `fill_window` bars if `high >= entry_trigger`.
  - From fill bar, hold up to `hold_bars`:
      * if `low <= stop`  -> exit at stop (-1R)
      * elif `high >= target` -> exit at target (+2R)
      * else at hold_bars -> close at last close (time-stop)
  - If both stop and target are touched on the same bar, assume stop first
    (worst-case sequencing).
  - No re-signal while holding.

USAGE
-----
    from backtest import backtest
    res = backtest(["NVDA","GEV","ETN","MRVL"], hold_bars=20)
    print(res["report"])
    print(res["trades"].head())

Swap the `fetcher` argument for any callable `(ticker, lookback_days=400) ->
OHLCV DataFrame` to use your own feed. The synthetic self-test in __main__
runs offline.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict

from swing_scanner import Scanner, fetch_ohlcv as default_fetch


@dataclass
class Trade:
    ticker: str
    signal: str           # LOADED / MOVING_NOW
    flag_date: str
    entry_date: str
    entry: float
    stop: float
    target: float
    exit_date: str
    exit_price: float
    bars_held: int
    r_multiple: float
    exit_reason: str      # target / stop / time


def _replay_ticker(df: pd.DataFrame, ticker: str, scanner: Scanner,
                   bench: pd.DataFrame | None, hold_bars: int,
                   fill_window: int = 3, start_idx: int = 252) -> list[Trade]:
    trades: list[Trade] = []
    next_eligible = start_idx
    for i in range(start_idx, len(df) - 1):
        if i < next_eligible:
            continue
        sig = scanner._score(df.iloc[:i + 1], bench, ticker)
        if not (sig.moving_now >= 60 or sig.loaded >= 60):
            continue
        signal_type = "LOADED" if sig.loaded >= sig.moving_now else "MOVING_NOW"
        entry_trigger, stop = sig.entry_trigger, sig.stop
        if (np.isnan(entry_trigger) or np.isnan(stop)
                or stop >= entry_trigger):
            continue
        risk = entry_trigger - stop
        target = entry_trigger + 2 * risk

        # fill search
        fill_idx = None
        for j in range(i + 1, min(i + 1 + fill_window, len(df))):
            if df.iloc[j]["high"] >= entry_trigger:
                fill_idx = j
                break
        if fill_idx is None:
            next_eligible = i + 1
            continue

        # hold from fill bar
        exit_idx, exit_price, reason = None, np.nan, "time"
        for k in range(fill_idx, min(fill_idx + hold_bars + 1, len(df))):
            bar = df.iloc[k]
            if bar["low"] <= stop:
                exit_idx, exit_price, reason = k, stop, "stop"
                break
            if bar["high"] >= target:
                exit_idx, exit_price, reason = k, target, "target"
                break
        if exit_idx is None:
            exit_idx = min(fill_idx + hold_bars, len(df) - 1)
            exit_price = float(df.iloc[exit_idx]["close"])
            reason = "time"

        r = (exit_price - entry_trigger) / risk
        trades.append(Trade(
            ticker=ticker, signal=signal_type,
            flag_date=str(df.index[i].date()),
            entry_date=str(df.index[fill_idx].date()),
            entry=round(float(entry_trigger), 2),
            stop=round(float(stop), 2),
            target=round(float(target), 2),
            exit_date=str(df.index[exit_idx].date()),
            exit_price=round(float(exit_price), 2),
            bars_held=int(exit_idx - fill_idx),
            r_multiple=round(float(r), 2),
            exit_reason=reason))
        next_eligible = exit_idx + 1
    return trades


def _expectancy_table(trades: list[Trade]) -> str:
    if not trades:
        return "no trades fired"
    df = pd.DataFrame([asdict(t) for t in trades])
    lines = ["=== Expectancy by signal ==="]
    for sig in sorted(df["signal"].unique().tolist()) + ["ALL"]:
        sub = df if sig == "ALL" else df[df["signal"] == sig]
        n = len(sub)
        wins = sub[sub["r_multiple"] > 0]
        losses = sub[sub["r_multiple"] <= 0]
        win_rate = len(wins) / n if n else 0
        avg_r = sub["r_multiple"].mean()
        gross_win = wins["r_multiple"].sum()
        gross_loss = abs(losses["r_multiple"].sum())
        pf = (float("inf") if gross_loss == 0 and gross_win > 0
              else (0.0 if gross_loss == 0 else gross_win / gross_loss))
        pf_str = "inf" if pf == float("inf") else f"{pf:.2f}"
        edge = "EDGE" if avg_r > 0 else "no edge"
        lines.append(f"{sig:12} n={n:4d}  win%={win_rate:.0%}  "
                     f"avgR={avg_r:+.2f}  PF={pf_str}  {edge}")
    return "\n".join(lines)


def backtest(tickers, fetcher=default_fetch, hold_bars: int = 20,
             fill_window: int = 3, exclude=None,
             benchmark: str = "SPY") -> dict:
    scanner = Scanner(exclude=exclude or set(),
                      benchmark=benchmark, fetcher=fetcher)
    bench = None
    try:
        bench = fetcher(benchmark)
    except Exception:
        bench = None
    all_trades: list[Trade] = []
    for t in tickers:
        try:
            df = fetcher(t)
        except Exception:
            continue
        if df is None or len(df) < 300:
            continue
        all_trades.extend(_replay_ticker(df, t, scanner, bench,
                                         hold_bars, fill_window))
    trades_df = pd.DataFrame([asdict(t) for t in all_trades])
    return {"trades": trades_df, "report": _expectancy_table(all_trades)}


# ----------------------------------------------------------------------
# Synthetic self-test: random-walk multi-year series, no network
# ----------------------------------------------------------------------
def _series(seed: int, drift: float, vol: float, n: int = 700) -> pd.DataFrame:
    r = np.random.default_rng(seed)
    ret = r.normal(drift, vol, n)
    close = 100 * np.exp(np.cumsum(ret))
    high = close * (1 + np.abs(r.normal(0, 0.008, n)))
    low = close * (1 - np.abs(r.normal(0, 0.008, n)))
    open_ = (high + low) / 2
    volu = np.abs(r.normal(1e6, 2e5, n))
    idx = pd.date_range(end="2026-05-30", periods=n, freq="B")
    return pd.DataFrame({"open": open_, "high": high, "low": low,
                         "close": close, "volume": volu}, index=idx)


if __name__ == "__main__":
    samples = {f"SYN{i}": _series(i, 0.0008, 0.018) for i in range(6)}
    samples["SPY"] = _series(99, 0.0004, 0.010)
    res = backtest([k for k in samples if k != "SPY"],
                   fetcher=lambda t, **_: samples.get(t),
                   hold_bars=20)
    print(res["report"])
    n = len(res["trades"])
    print(f"\ntotal trades: {n}")
    if n:
        pd.set_option("display.width", 200, "display.max_columns", 20)
        print(res["trades"].head(10).to_string(index=False))
    print("\nNote: synthetic random-walk data -- expectancy here is meaningless,")
    print("just validates the wiring. Run on real OHLCV to assess actual edge.")
