"""
shortlist.py -- run the full pipeline on a list of tickers and print
trade cards (account + size + stop) for any that clear the gates.

Usage:
    python shortlist.py                              # loads universe.txt
    python shortlist.py GOOGL LMT PWR AMZN JPM      # ad-hoc override

With no CLI args, reads `universe.txt` from the current directory:
one ticker per line, blank lines and #-comments ignored. If the file is
missing or empty, prints instructions and exits -- no silent fallback,
so a scan is always deliberate about which universe it ran.

Pipeline applied: liquidity/size gate + fundamental quality gate (forensic
gate skipped until SEC_UA is set in filing_forensics.py), then daily-setup
score, then catalyst timing. Routing via account_router, sizing via
risk_manager (0.75% sleeve risk per trade, 2x-ATR stop).
"""
from __future__ import annotations
import sys
import re
import os
import pandas as pd

from swing_pipeline import SwingPipeline, QualityGate
from swing_scanner import Scanner
from catalyst_calendar import catalyst_score
from account_router import infer_horizon, route
from risk_manager import RiskManager, RiskConfig


UNIVERSE_FILE = "universe.txt"


def load_universe(path: str = UNIVERSE_FILE) -> list[str]:
    """Read a ticker-per-line file; strip # comments and blank lines."""
    if not os.path.exists(path):
        return []
    out: list[str] = []
    with open(path) as f:
        for raw in f:
            line = raw.split("#", 1)[0].strip()
            if line:
                out.append(line.upper())
    return out


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
    tickers = [t.upper() for t in sys.argv[1:]]
    if not tickers:
        tickers = load_universe()
        if not tickers:
            print(f"ERROR: no tickers given and '{UNIVERSE_FILE}' is missing "
                  f"or empty.\n"
                  f"       Create {UNIVERSE_FILE} (one ticker per line, "
                  f"# comments ok),\n"
                  f"       or pass tickers directly: "
                  f"python shortlist.py NVDA AMD ...", file=sys.stderr)
            sys.exit(1)
        print(f"# loaded {len(tickers)} tickers from {UNIVERSE_FILE}",
              file=sys.stderr)
    main(tickers)
