# Swing Toolkit — intraday swings on *good* stocks, with discipline enforced

Four modules that chain into one pipeline. The design principle is simple and it
is the opposite of every "find the next rocket" tool: **it will not surface a
name, no matter how hard it's ripping, unless that name is fundamentally sound
and its filings are clean — and it never emits a signal without a stop.**

It cannot predict a pop. Nothing can; the pop is the catalyst, and catalysts
aren't in the data beforehand. What it *can* do, honestly:

- **Detect** a swing as it forms intraday (relative volume, opening-range break, VWAP).
- **Find** coiled "potential energy" setups on daily bars (volatility compression).
- **Time** them against *scheduled* catalysts (you can know the date, not the outcome).
- **Gate** all of it through quality + forensic filters so you only swing good names.
- **Enforce** a mechanical entry and stop on every candidate.

---

## The files

| File | Job |
|---|---|
| `swing_scanner.py` | Daily-bar setups: `MOVING_NOW` (already moving) and `LOADED` (coiled spring — closest honest thing to "about to"). |
| `filing_forensics.py` | Hudson-Labs-style EDGAR forensics: deterministic red-flag engine (going-concern, material weakness, auditor change, restatement, dilution…) + cite-or-N/A LLM Q&A. |
| `catalyst_calendar.py` | Scheduled-catalyst timing (earnings dates + manual events). The honest "about to" layer. |
| `intraday.py` | Live-session swing engine: RVOL, opening-range breakout, VWAP, gap. |
| `swing_pipeline.py` | **The unified tool.** Gates on liquidity/size/quality/filings, then ranks survivors by swing + catalyst, with entry+stop on each. |

---

## The pipeline logic (why it protects you)

```
GATE 1  Liquidity & size      -> tradeable, not a micro-cap (the GRRR rule)
GATE 2  Fundamental quality   -> profitable, not over-levered ("good")
GATE 3  Forensic filings      -> no going-concern / material-weakness traps
        --- must clear all three to be a candidate ---
SCORE 1 Daily setup           -> LOADED (coiled) or MOVING_NOW
SCORE 2 Intraday swing        -> RVOL / ORB / VWAP (during the session)
SCORE 3 Catalyst timing       -> scheduled event in the window (tie-break boost)
FINAL                         -> rank survivors by swing; every one has a stop
```

A name ripping +95% on momentum but tiny, unprofitable, or carrying a
going-concern flag scores **zero** — it's filtered out. The good, coiled name
with earnings in three days rises to the top. That's the edge: not catching every
move, but never blowing up on the way to the goal.

---

## Running it live

These were tested on synthetic data (this environment has no market/SEC feed).
To run for real, install deps and plug in a data source:

```bash
pip install pandas numpy yfinance requests anthropic
```

```python
from swing_pipeline import SwingPipeline, QualityGate
from filing_forensics import forensic_report_for_ticker
from swing_scanner import Scanner
from catalyst_calendar import catalyst_score
from intraday import analyze_intraday

# daily setup adapter: run the scanner, return a dict per ticker
_scanner = Scanner(exclude={"XEQT","ZEQT","XIC","ZSP"})
def daily_scan(t):
    row = _scanner.scan([t]).iloc[0].to_dict()
    return row

pipe = SwingPipeline(
    quality_gate=QualityGate(min_market_cap=2e9, min_dollar_volume=2e7),
    forensic_fn=forensic_report_for_ticker,
    daily_scan_fn=daily_scan,
    intraday_fn=analyze_intraday,
    catalyst_fn=catalyst_score,
    exclude={"XEQT","ZEQT","XIC","ZSP","XEF","XWD","XGI"},  # forever-holds
)

universe = ["NVDA","GEV","ETN","VRT","PWR","ANET","CEG","TSM","MRVL","AVGO"]
df = pipe.run(universe)              # daily + gates + catalyst
print(df[df.passed_gates].head(15))
```

For **intraday**, supply a feed function returning `(today_bars, prior_close,
intraday_history)` per ticker (5-minute bars; yfinance gives ~60 days of 5m free,
a brokerage API is better), and pass it as `pipe.run(universe, intraday_feed=...)`.

Set your EDGAR User-Agent in `filing_forensics.py` (`SEC_UA`) — the SEC requires
a real name + email. For the cite-or-N/A Q&A, set `ANTHROPIC_API_KEY`.

---

## Honest limits (read these)

- **No prediction.** `LOADED` finds coils; many coils fizzle or break the wrong
  way. `MOVING_NOW` and the intraday engine detect moves *as they happen* and tag
  `poor-R:R` when you're too late. Direction and timing are never guaranteed.
- **Stops are mandatory, not optional.** Sized off the opening range / VWAP / ATR.
  Decide entry and exit before you click. (Your Constellation rule, in code.)
- **Gates need a fundamentals + filings feed** to do their job; without them the
  pipeline still runs but can't protect you — so wire them up before trusting it.
- **This is a focusing tool, not an oracle.** It narrows a universe to a short list
  of sound names worth a human look. The decision — and the position size — stays
  yours (and Munsa's).
- It replicates Hudson Labs' *technique and discipline* on free public data; it
  does not replicate their full multi-model retrieval or S&P valuation coverage.
```
