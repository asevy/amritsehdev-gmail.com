"""
launch.py -- end-to-end integration of the swing toolkit on synthetic data.

Chains: SwingPipeline (gates + scores) -> infer_horizon/route (account) ->
RiskManager.size_order (shares + stops + circuit breakers) -> Journal
(signal log + expectancy). No network required; swap the synthetic
*_fn callbacks for live feeds (yfinance / EDGAR / brokerage) to go production.
"""
from __future__ import annotations
import os, sys
import numpy as np

from swing_pipeline import SwingPipeline, QualityGate
from account_router import infer_horizon, route
from risk_manager import RiskManager, RiskConfig
from trade_journal import Journal

# ---- synthetic universe: a clean leader, a junk ripper, a forensic trap ----
FUND = {
    "GEV":    {"market_cap": 9e10, "avg_dollar_volume": 6e8,
               "net_income": 3e9, "net_debt": 1e9, "ebitda": 7e9},
    "NVDA":   {"market_cap": 3e12, "avg_dollar_volume": 5e10,
               "net_income": 7e10, "net_debt": -3e10, "ebitda": 9e10},
    "JUNKCO": {"market_cap": 3e8,  "avg_dollar_volume": 4e6,
               "net_income": -2e8, "net_debt": 5e8, "ebitda": -1e8},
    "TRAPCO": {"market_cap": 8e9,  "avg_dollar_volume": 1e8,
               "net_income": 3e8,  "net_debt": 1e9, "ebitda": 2e9},
}
class _Rep:
    def __init__(self, risk, hits): self.risk_score, self.hits = risk, hits
class _Hit:
    def __init__(self, label): self.label = label
FILINGS = {
    "GEV":    _Rep(1, []),
    "NVDA":   _Rep(0, []),
    "JUNKCO": _Rep(4, [_Hit("Dilution")]),
    "TRAPCO": _Rep(11, [_Hit("Going-concern / survival doubt")]),
}
DAILY = {
    "GEV":    {"price": 200, "moving_now": 72, "loaded": 65,
               "entry_trigger": 203, "stop": 192, "rr_to_high": 1.6},
    "NVDA":   {"price": 900, "moving_now": 30, "loaded": 82,
               "entry_trigger": 915, "stop": 870, "rr_to_high": 2.1},
    "JUNKCO": {"price":  20, "moving_now": 95, "loaded": 10,
               "entry_trigger":  21, "stop":  18, "rr_to_high": 0.5},
    "TRAPCO": {"price":  50, "moving_now": 88, "loaded": 20,
               "entry_trigger":  51, "stop":  47, "rr_to_high": 1.4},
}
CATALYST = {  # (score, label, days)
    "GEV":  (96.0, "earnings in 3d",  3),
    "NVDA": (50.0, "earnings in 14d", 14),
}

def fnd(t, **_): return FUND.get(t, {})
def frn(t, form="10-K"): return FILINGS.get(t, _Rep(np.nan, []))
def dly(t): return DAILY.get(t, {})
def cat(t, h):
    rec = CATALYST.get(t)
    return (rec[0], rec[1]) if rec else (0.0, "")

# ---- 1. run the pipeline ----------------------------------------------
pipe = SwingPipeline(
    quality_gate=QualityGate(min_market_cap=2e9, min_dollar_volume=2e7),
    fundamentals_fn=fnd, forensic_fn=frn,
    daily_scan_fn=dly, intraday_fn=None, catalyst_fn=cat,
    exclude={"XEQT", "ZEQT", "XIC"},
)
universe = ["GEV", "NVDA", "JUNKCO", "TRAPCO", "XEQT"]
df = pipe.run(universe)
cols = ["ticker", "passed_gates", "daily_setup", "daily_score",
        "catalyst", "final_score", "entry_trigger", "stop", "rr", "verdict"]
print("=== PIPELINE OUTPUT ===")
import pandas as pd
pd.set_option("display.width", 200, "display.max_columns", 20)
print(df[cols].to_string(index=False))

# ---- 2/3. route + size only the actionable, gated-clean candidates ----
rm = RiskManager(RiskConfig(sleeve_value=50_000, mode="suggest"))
journal_path = "/tmp/launch_journal.json"
if os.path.exists(journal_path):
    os.remove(journal_path)
jrnl = Journal(journal_path)

print("\n=== ROUTING + SIZING ACTIONABLE CANDIDATES ===")
actionable = df[df["verdict"].str.startswith("ACTIONABLE", na=False)]
if actionable.empty:
    print("(none — every name was filtered or watch-only)")
for _, r in actionable.iterrows():
    t = r["ticker"]
    cdays = CATALYST.get(t, (None, None, None))[2]
    horizon = infer_horizon(r["daily_setup"], cdays, None)
    advice = route(t, horizon)
    order = rm.size_order(t, entry=float(r["entry_trigger"]),
                          stop=float(r["stop"]), account=advice.account)
    placement = rm.place(order)
    print(f"\n  {t}: {r['daily_setup']} | catalyst={r['catalyst'] or '-'} "
          f"| horizon={horizon}")
    print(f"     account: {advice.account}")
    print(f"     {placement}")
    if order.allowed:
        jrnl.log_signal(
            ticker=t, signal_type=r["daily_setup"],
            flag_price=float(r["entry_trigger"]),
            entry=float(r["entry_trigger"]),
            stop=float(r["stop"]),
            target=round(float(r["entry_trigger"])
                         + 2 * (float(r["entry_trigger"]) - float(r["stop"])), 2),
            horizon=horizon, account=advice.account, taken=True,
        )

# ---- 4. simulate forward prices, close trades, report expectancy -------
print("\n=== SIMULATED FORWARD CLOSE (one winner hits target, one stops) ===")
SIM_EXITS = {"GEV": 230.0, "NVDA": 845.0}  # GEV winner, NVDA stops
jrnl.update(lambda t: SIM_EXITS.get(t))
print(jrnl.report())

os.remove(journal_path)
print("\nLaunch complete. Synthetic only — no real orders placed.")
