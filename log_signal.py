"""
log_signal.py -- record a flagged setup in swing_journal.json.

Default is `taken=False` (a watchlist entry the scanner flagged but you
haven't acted on). Add --taken when you actually place the order.

Usage:
    # log the LMT LOADED setup as a watchlist entry
    python log_signal.py LMT LOADED \\
        --flag-price 513.43 --entry 541.75 --stop 493.48 --target 638.29 \\
        --horizon multi_week --account "TFSA (post-catalyst)"

    # show the journal afterwards
    python -c "from trade_journal import Journal; print(Journal().report())"

    # update forward prices (flagged-not-taken signals also track):
    python -c "from trade_journal import Journal; from swing_scanner import fetch_ohlcv; \\
               j=Journal(); j.update(lambda t: float(fetch_ohlcv(t).close.iloc[-1])); \\
               print(j.report())"
"""
from __future__ import annotations
import argparse
from trade_journal import Journal


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ticker", help="e.g. LMT")
    p.add_argument("signal_type",
                   choices=["LOADED", "MOVING_NOW", "catalyst", "intraday"])
    p.add_argument("--flag-price", type=float, required=True,
                   help="price when the signal fired (today's close)")
    p.add_argument("--entry", type=float, required=True,
                   help="breakout entry trigger from scanner")
    p.add_argument("--stop", type=float, required=True,
                   help="ATR-based stop from scanner")
    p.add_argument("--target", type=float, required=True,
                   help="profit target (typically entry + 2*(entry-stop))")
    p.add_argument("--horizon", default="",
                   help="intraday / few_day / multi_week / multi_month")
    p.add_argument("--account", default="",
                   help="e.g. TFSA, Personal non-registered")
    p.add_argument("--taken", action="store_true",
                   help="set if you actually placed the order (default: flagged-only)")
    p.add_argument("--journal", default="swing_journal.json",
                   help="journal file path (default: swing_journal.json)")
    args = p.parse_args()

    j = Journal(args.journal)
    j.log_signal(
        ticker=args.ticker.upper(),
        signal_type=args.signal_type,
        flag_price=args.flag_price,
        entry=args.entry,
        stop=args.stop,
        target=args.target,
        horizon=args.horizon,
        account=args.account,
        taken=args.taken,
    )
    risk = args.entry - args.stop
    reward = args.target - args.entry
    rr = round(reward / risk, 2) if risk > 0 else float("nan")
    print(f"Logged {args.ticker.upper()} {args.signal_type} "
          f"(taken={args.taken})")
    print(f"  flag ${args.flag_price}  entry ${args.entry}  "
          f"stop ${args.stop}  target ${args.target}  R:R {rr}")
    print(f"  horizon: {args.horizon or '-'}  account: {args.account or '-'}")
    print(f"Journal: {args.journal} ({len(j.logs)} total entries)")


if __name__ == "__main__":
    main()
