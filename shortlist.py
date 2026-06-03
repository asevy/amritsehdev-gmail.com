"""
shortlist.py -- run the full pipeline on a small list of tickers and print
trade cards (account + size + stop) for any that clear the gates.

Usage:
    python shortlist.py                              # default list
    python shortlist.py GOOGL LMT PWR AMZN JPM      # any custom list

Pipeline applied: liquidity/size gate + fundamental quality gate (forensic
gate skipped until SEC_UA is set in filing_forensics.py), then daily-setup
score, then catalyst timing. Routing via account_router, sizing via
risk_manager (0.75% sleeve risk per trade, 2x-ATR stop).
"""
from __future__ import annotations
import sys
import re
import pandas as pd

from swing_pipeline import SwingPipeline, QualityGate
from swing_scanner import Scanner
from catalyst_calendar import catalyst_score
from account_router import infer_horizon, route
from risk_manager import RiskManager, RiskConfig


DEFAULT_SHORTLIST = ["GOOGL", "LMT", "PWR", "AMZN", "JPM"]


def main(tickers: list[str]) -> None:
    pd.set_option("display.width", 220, "display.max_columns", 20)

    scanner = Scanner(
        exclude={"XEQT", "ZEQT", "XIC", "ZSP", "XEF", "XWD", "XGI"},
    )

    def daily_scan_fn(t: str) -> dict:
        row = scanner.scan([t])
        return row.iloc[0].to_dict() if len(row) else {}

    pipe = SwingPipeline(
        quality_gate=QualityGate(min_market_cap=2e9, min_dollar_volume=2e7),
        daily_scan_fn=daily_scan_fn,
        catalyst_fn=catalyst_score,
        # forensic_fn left None until SEC_UA is set in filing_forensics.py
    )

    df = pipe.run(tickers)
    cols = ["ticker", "passed_gates", "quality", "daily_setup", "daily_score",
            "catalyst", "final_score", "entry_trigger", "stop", "rr", "verdict"]
    print(df[cols].to_string(index=False))

    rm = RiskManager(RiskConfig(sleeve_value=50_000, mode="suggest"))
    print("\n=== TRADE CARDS ===")
    gated = df[df.passed_gates]
    if gated.empty:
        print("(no names cleared the gates -- no actionable trades today)")
        return
    for _, r in gated.iterrows():
        m = re.search(r"(\d+)d", str(r["catalyst"]))
        cdays = int(m.group(1)) if m else None
        horizon = infer_horizon(r["daily_setup"], cdays, None)
        advice = route(r["ticker"], horizon)
        order = rm.size_order(
            r["ticker"],
            entry=float(r["entry_trigger"]),
            stop=float(r["stop"]),
            account=advice.account,
        )
        placed = rm.place(order)
        print(f"\n{r['ticker']}: {r['daily_setup'] or '-'} | "
              f"catalyst={r['catalyst'] or '-'} | horizon={horizon}")
        print(f"  account: {advice.account}")
        print(f"  reason : {advice.reason.split('.')[0]}.")
        print(f"  {placed}")


if __name__ == "__main__":
    tickers = sys.argv[1:] or DEFAULT_SHORTLIST
    main(tickers)
