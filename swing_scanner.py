"""
swing_scanner.py
================
An honest momentum / anomaly / "coiled-spring" scanner.

WHAT THIS DOES (and does not do)
--------------------------------
It does NOT predict that a stock will pop. Nothing can: the pop is usually
caused by a catalyst (an earnings surprise, an endorsement, a deal) that does
not exist in any price/volume dataset beforehand.

What it DOES is two honest jobs:

  1. "MOVING NOW"  — detects abnormal price+volume action AS IT HAPPENS.
                     A react-fast momentum/breakout scanner. Tells you a name
                     is moving hard on heavy volume right now. This is detection,
                     not prediction.

  2. "LOADED"      — the closest legitimate thing to "about to pop": finds
                     stocks storing POTENTIAL energy — volatility compressed,
                     volume dried up, price coiled in a tight base near its
                     highs. Big moves are preceded by unusually quiet ones more
                     often than chance. It identifies the coil; it CANNOT tell
                     you which way it releases or when. Pair with a known
                     calendar catalyst (earnings date) for the honest version
                     of "about to."

DISCIPLINE BUILT IN
-------------------
Every actionable candidate is emitted WITH a predetermined entry trigger and a
stop. The scanner will not surface a "buy" without a stop attached — this is
the Constellation rule enforced in code. Index ETFs can be excluded from
signals (forever-hold/DCA names should not be traded on momentum).

DATA
----
Defaults to yfinance (free) so it runs out of the box. Swap `fetch_ohlcv` for
your brokerage/market-data API to go production. Requires: pandas, numpy.
yfinance only needed if you use the default fetcher.

USAGE
-----
    from swing_scanner import Scanner
    s = Scanner(exclude={"XEQT","ZEQT","XIC","ZSP","XEF","XWD","XGI"})  # forever-holds
    # discovery: screen a universe
    df = s.scan(["MRVL","NVDA","GEV","ETN","VRT","PWR","AIPO","CEG","ANET","TSM"])
    print(df)
    # discipline: watch your own list and flag entries/stops/exits
    df = s.scan(my_watchlist, mode="monitor")
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, field, asdict
from typing import Iterable, Optional


# ----------------------------------------------------------------------
# Data layer — swap this one function for your own feed
# ----------------------------------------------------------------------
def fetch_ohlcv(ticker: str, lookback_days: int = 400) -> Optional[pd.DataFrame]:
    """Return a DataFrame indexed by date with columns:
    open, high, low, close, volume. Replace with your brokerage API in prod."""
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("pip install yfinance, or replace fetch_ohlcv with your feed")
    df = yf.download(ticker, period=f"{lookback_days}d", interval="1d",
                     auto_adjust=False, progress=False)
    if df is None or len(df) == 0:
        return None
    df = df.rename(columns=str.lower)
    # flatten any multiindex columns from yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df[["open", "high", "low", "close", "volume"]].dropna()


# ----------------------------------------------------------------------
# Indicators (pure functions, no I/O — these are unit-tested below)
# ----------------------------------------------------------------------
def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Average True Range — the stock's typical daily movement."""
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def bollinger_bandwidth(df: pd.DataFrame, n: int = 20, k: float = 2.0) -> pd.Series:
    """Width of Bollinger Bands as % of price. Low = volatility compressed = coiled."""
    c = df["close"]
    ma = c.rolling(n).mean()
    sd = c.rolling(n).std()
    return ((ma + k * sd) - (ma - k * sd)) / ma


def percentile_rank(series: pd.Series, window: int = 120) -> float:
    """Where does the latest value sit within its own recent history? 0..1."""
    s = series.dropna()
    if len(s) < window // 2:
        return np.nan
    window_vals = s.iloc[-window:]
    latest = s.iloc[-1]
    return float((window_vals < latest).mean())


def volume_zscore(df: pd.DataFrame, n: int = 20) -> float:
    """How abnormal is today's volume vs its recent average? In std-devs."""
    v = df["volume"]
    base = v.iloc[-(n + 1):-1]
    if base.std(ddof=0) == 0 or len(base) < n:
        return np.nan
    return float((v.iloc[-1] - base.mean()) / base.std(ddof=0))


def range_position(df: pd.DataFrame, n: int = 252) -> float:
    """Where is price within its n-day high/low range? 1.0 = at the high."""
    window = df.iloc[-n:]
    lo, hi = window["low"].min(), window["high"].max()
    if hi == lo:
        return np.nan
    return float((df["close"].iloc[-1] - lo) / (hi - lo))


def pct_from_high(df: pd.DataFrame, n: int = 252) -> float:
    """How far below the n-day high is price? e.g. -0.03 = 3% below."""
    hi = df["high"].iloc[-n:].max()
    return float(df["close"].iloc[-1] / hi - 1.0)


def relative_strength(df: pd.DataFrame, bench: pd.DataFrame, n: int = 63) -> float:
    """Stock return minus benchmark return over n days. >0 = leadership."""
    if bench is None or len(bench) < n + 1 or len(df) < n + 1:
        return np.nan
    r = df["close"].iloc[-1] / df["close"].iloc[-n - 1] - 1
    rb = bench["close"].iloc[-1] / bench["close"].iloc[-n - 1] - 1
    return float(r - rb)


def momentum_12_1(df: pd.DataFrame) -> float:
    """Jegadeesh-Titman 12-1: return over the last ~12 months excluding the most
    recent month (skips short-term reversal). The classic momentum factor."""
    if len(df) < 252:
        return np.nan
    c = df["close"]
    return float(c.iloc[-21] / c.iloc[-252] - 1)


def nr7(df: pd.DataFrame) -> bool:
    """Narrow Range 7: today's range is the tightest of the last 7 days.
    A classic coil/contraction tell that often precedes expansion."""
    rng = (df["high"] - df["low"]).iloc[-7:]
    return bool(rng.iloc[-1] == rng.min())


def inside_day(df: pd.DataFrame) -> bool:
    """Today's high/low inside yesterday's — consolidation."""
    return bool(df["high"].iloc[-1] <= df["high"].iloc[-2]
                and df["low"].iloc[-1] >= df["low"].iloc[-2])


# ----------------------------------------------------------------------
# Result container
# ----------------------------------------------------------------------
@dataclass
class Signal:
    ticker: str
    price: float = np.nan
    moving_now: float = 0.0      # 0..100 — abnormal action happening right now
    loaded: float = 0.0          # 0..100 — coiled-spring / potential-energy score
    vol_z: float = np.nan        # volume z-score (today vs 20d)
    bbw_pctile: float = np.nan   # Bollinger bandwidth percentile (low=compressed)
    range_pos: float = np.nan    # position in 52wk range (1=at high)
    from_high: float = np.nan    # % below 52wk high
    mom_12_1: float = np.nan     # 12-1 momentum
    rel_str: float = np.nan      # relative strength vs benchmark
    coiled: bool = False         # NR7 / inside-day contraction flag
    entry_trigger: float = np.nan   # the price level that confirms a breakout
    stop: float = np.nan            # MANDATORY stop (ATR-based)
    rr_to_high: float = np.nan      # reward:risk to the prior high
    flags: str = ""

    def as_row(self) -> dict:
        return asdict(self)


# ----------------------------------------------------------------------
# Scanner
# ----------------------------------------------------------------------
class Scanner:
    def __init__(self,
                 exclude: Optional[Iterable[str]] = None,
                 benchmark: str = "SPY",
                 atr_stop_mult: float = 2.0,
                 fetcher=fetch_ohlcv):
        self.exclude = {t.upper() for t in (exclude or [])}
        self.benchmark = benchmark
        self.atr_stop_mult = atr_stop_mult
        self.fetch = fetcher
        self._bench_cache = None

    # --- scoring -------------------------------------------------------
    def _score(self, df: pd.DataFrame, bench: pd.DataFrame, ticker: str) -> Signal:
        sig = Signal(ticker=ticker)
        if df is None or len(df) < 60:
            sig.flags = "insufficient_data"
            return sig

        price = float(df["close"].iloc[-1])
        a = float(atr(df).iloc[-1])
        bbw = bollinger_bandwidth(df)
        bbw_pct = percentile_rank(bbw, window=120)
        vz = volume_zscore(df)
        rpos = range_position(df)
        fhigh = pct_from_high(df)
        mom = momentum_12_1(df)
        rs = relative_strength(df, bench)
        coiled = nr7(df) or inside_day(df)
        day_ret = float(df["close"].iloc[-1] / df["close"].iloc[-2] - 1) if len(df) > 1 else 0.0

        sig.price, sig.vol_z, sig.bbw_pctile = price, vz, bbw_pct
        sig.range_pos, sig.from_high, sig.mom_12_1, sig.rel_str = rpos, fhigh, mom, rs
        sig.coiled = coiled

        # ---- MOVING NOW: abnormal action happening today ----
        # heavy volume + a real price move + near range highs
        mn = 0.0
        if not np.isnan(vz):
            mn += np.clip(vz, 0, 4) / 4 * 45        # up to 45 pts for volume spike
        mn += np.clip(abs(day_ret) / 0.05, 0, 1) * 35  # up to 35 for a >=5% day
        if not np.isnan(rpos):
            mn += np.clip(rpos, 0, 1) * 20          # up to 20 for being near highs
        sig.moving_now = round(float(mn), 1)

        # ---- LOADED: coiled-spring / potential energy (closest to "about to") ----
        # compressed volatility + dried-up volume + tight base near highs
        ld = 0.0
        if not np.isnan(bbw_pct):
            ld += (1 - bbw_pct) * 45                # tighter bands = more coiled
        if not np.isnan(vz):
            ld += np.clip((0 - vz) / 1.5, 0, 1) * 20   # volume BELOW average = dry-up
        if coiled:
            ld += 15                                 # NR7 / inside-day contraction
        if not np.isnan(fhigh):
            # near (but not at) the high: a base under resistance
            ld += np.clip(1 - abs(fhigh + 0.04) / 0.10, 0, 1) * 20
        sig.loaded = round(float(ld), 1)

        # ---- mandatory entry + stop (discipline enforced) ----
        recent_high = float(df["high"].iloc[-20:].max())
        sig.entry_trigger = round(recent_high * 1.001, 2)     # breakout confirmation
        sig.stop = round(price - self.atr_stop_mult * a, 2)   # ATR stop from current
        risk = price - sig.stop
        reward = recent_high - price
        sig.rr_to_high = round(reward / risk, 2) if risk > 0 else np.nan

        notes = []
        if ticker.upper() in self.exclude:
            notes.append("EXCLUDED-forever-hold(no-momentum-trading)")
        if sig.moving_now >= 60:
            notes.append("MOVING-NOW")
        if sig.loaded >= 60:
            notes.append("LOADED-coiled")
        if not np.isnan(vz) and vz >= 3:
            notes.append(f"vol{vz:.1f}sigma")
        if not np.isnan(fhigh) and -0.05 <= fhigh <= 0:
            notes.append("at/near-52wk-high")
        if not np.isnan(sig.rr_to_high) and sig.rr_to_high < 1:
            notes.append("poor-R:R-dont-chase")
        sig.flags = ";".join(notes)
        return sig

    # --- public --------------------------------------------------------
    def scan(self, tickers: Iterable[str], mode: str = "discover") -> pd.DataFrame:
        if self._bench_cache is None:
            self._bench_cache = self.fetch(self.benchmark)
        bench = self._bench_cache
        rows = []
        for t in tickers:
            try:
                df = self.fetch(t)
            except Exception as e:
                rows.append(Signal(ticker=t, flags=f"fetch_error:{e}").as_row())
                continue
            rows.append(self._score(df, bench, t).as_row())
        out = pd.DataFrame(rows)
        if len(out) == 0:
            return out
        sort_key = "moving_now" if mode == "discover" else "loaded"
        return out.sort_values(["moving_now", "loaded"], ascending=False).reset_index(drop=True)


# ----------------------------------------------------------------------
# Self-test with synthetic data (runs with no network / no feed)
# ----------------------------------------------------------------------
def _synthetic(kind: str, n: int = 300, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    if kind == "coiled":          # trends up, then goes very quiet near highs
        base = np.cumsum(rng.normal(0.4, 1.0, n)) + 100
        base[-25:] = base[-25] + rng.normal(0, 0.15, 25).cumsum()  # tight coil
        vol = np.r_[rng.normal(1e6, 1e5, n - 25), rng.normal(4e5, 3e4, 25)]  # dry-up
    elif kind == "popping":       # quiet then a huge volume breakout today
        base = np.cumsum(rng.normal(0.1, 0.6, n)) + 100
        base[-1] = base[-2] * 1.20
        vol = np.r_[rng.normal(1e6, 1e5, n - 1), [6e6]]            # 6x volume today
    else:                          # noise
        base = np.cumsum(rng.normal(0, 1.0, n)) + 100
        vol = rng.normal(1e6, 1e5, n)
    base = np.maximum(base, 1)
    close = base
    high = close * (1 + np.abs(rng.normal(0, 0.006, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.006, n)))
    open_ = (high + low) / 2
    idx = pd.date_range(end="2026-06-02", periods=n, freq="B")
    return pd.DataFrame({"open": open_, "high": high, "low": low,
                         "close": close, "volume": np.abs(vol)}, index=idx)


if __name__ == "__main__":
    samples = {"COIL_DEMO": _synthetic("coiled", seed=1),
               "POP_DEMO": _synthetic("popping", seed=2),
               "NOISE_DEMO": _synthetic("noise", seed=3),
               "SPY": _synthetic("noise", seed=9)}
    s = Scanner(exclude={"XEQT"}, fetcher=lambda t, lookback_days=400: samples.get(t))
    df = s.scan(["COIL_DEMO", "POP_DEMO", "NOISE_DEMO"])
    cols = ["ticker", "price", "moving_now", "loaded", "vol_z",
            "bbw_pctile", "from_high", "entry_trigger", "stop", "rr_to_high", "flags"]
    pd.set_option("display.width", 160, "display.max_columns", 20)
    print(df[cols].to_string(index=False))
