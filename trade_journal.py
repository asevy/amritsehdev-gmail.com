"""
trade_journal.py
================
Measures whether the machine actually makes money — the difference between a
real edge and a tool that just feels productive.

It logs EVERY signal the machine flags (taken or not) at the moment it's flagged,
then forward-tracks the price so you can measure the TOOL's hit rate independent
of your execution. Breaks results down by signal type so you learn which signals
have edge (does LOADED beat MOVING_NOW? do catalyst runners work?).

Computes, overall and per signal type:
  - win rate
  - average win / average loss
  - expectancy ($ and R-multiple — avg result per trade in units of risk)
  - profit factor (gross wins / gross losses)

R-multiple is the key metric: a trade that hits its target for +2x the amount
risked is +2R; one stopped out is -1R. Positive average R = the system has edge.

Storage: a simple JSON file. Run `update()` daily to refresh forward prices.
Do NOT fund real money until expectancy is positive over a meaningful sample.
"""
from __future__ import annotations
import json, os, datetime as dt
from dataclasses import dataclass, asdict, field
from typing import Optional


@dataclass
class SignalLog:
    ticker: str
    flagged_date: str
    signal_type: str            # LOADED / MOVING_NOW / catalyst / intraday
    flag_price: float
    entry: float
    stop: float
    target: float
    horizon: str = ""
    account: str = ""
    taken: bool = False         # did you actually trade it?
    # filled forward by update():
    last_price: float = float("nan")
    exit_price: float = float("nan")
    exit_date: str = ""
    status: str = "open"        # open / target_hit / stopped / closed
    return_since_flag: float = float("nan")
    r_multiple: float = float("nan")

    def risk_per_share(self) -> float:
        return max(self.entry - self.stop, 1e-9)


class Journal:
    def __init__(self, path: str = "swing_journal.json"):
        self.path = path
        self.logs: list[SignalLog] = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                self.logs = [SignalLog(**r) for r in json.load(f)]

    def save(self):
        with open(self.path, "w") as f:
            json.dump([asdict(l) for l in self.logs], f, indent=2)

    def log_signal(self, **kw):
        """Record a signal the moment the machine flags it."""
        if "flagged_date" not in kw:
            kw["flagged_date"] = dt.date.today().isoformat()
        self.logs.append(SignalLog(**kw))
        self.save()

    def update(self, price_fn):
        """Refresh forward prices/status. price_fn(ticker)->float (your feed)."""
        for l in self.logs:
            if l.status not in ("open",):
                continue
            px = price_fn(l.ticker)
            if px is None:
                continue
            l.last_price = float(px)
            l.return_since_flag = px / l.flag_price - 1.0
            # resolve target/stop
            if px >= l.target:
                l.status, l.exit_price = "target_hit", l.target
                l.exit_date = dt.date.today().isoformat()
            elif px <= l.stop:
                l.status, l.exit_price = "stopped", l.stop
                l.exit_date = dt.date.today().isoformat()
            if l.status in ("target_hit", "stopped", "closed"):
                l.r_multiple = (l.exit_price - l.entry) / l.risk_per_share()
        self.save()

    def close(self, ticker: str, exit_price: float):
        """Manually close an open position at a given price."""
        for l in self.logs:
            if l.ticker == ticker and l.status == "open":
                l.status, l.exit_price = "closed", float(exit_price)
                l.exit_date = dt.date.today().isoformat()
                l.r_multiple = (exit_price - l.entry) / l.risk_per_share()
        self.save()

    # --- analytics -----------------------------------------------------
    def stats(self, signal_type: Optional[str] = None, taken_only: bool = False) -> dict:
        rows = [l for l in self.logs
                if l.status in ("target_hit", "stopped", "closed")
                and (signal_type is None or l.signal_type == signal_type)
                and (l.taken or not taken_only)]
        n = len(rows)
        if n == 0:
            return {"n": 0, "note": "no closed trades yet"}
        rs = [l.r_multiple for l in rows]
        wins = [r for r in rs if r > 0]
        losses = [r for r in rs if r <= 0]
        gross_win = sum(wins)
        gross_loss = abs(sum(losses))
        # No losses yet: PF is undefined, not a 9-digit number. Report inf and
        # let the formatter render it honestly until enough trades accumulate.
        pf = float("inf") if gross_loss == 0 and gross_win > 0 else (
            0.0 if gross_loss == 0 else round(gross_win / gross_loss, 2))
        return {
            "n": n,
            "win_rate": round(len(wins) / n, 3),
            "avg_R": round(sum(rs) / n, 3),              # expectancy in R
            "avg_win_R": round(sum(wins) / len(wins), 3) if wins else 0.0,
            "avg_loss_R": round(sum(losses) / len(losses), 3) if losses else 0.0,
            "profit_factor": pf,
            "expectancy_positive": (sum(rs) / n) > 0,
        }

    def report(self) -> str:
        lines = ["=== Expectancy by signal type ==="]
        types = sorted({l.signal_type for l in self.logs})
        for t in types + [None]:
            label = t if t else "ALL"
            s = self.stats(signal_type=t)
            if s.get("n", 0) == 0:
                lines.append(f"{label:12} {s.get('note','-')}")
            else:
                pf = s['profit_factor']
                pf_str = "inf" if pf == float("inf") else f"{pf:.2f}"
                lines.append(
                    f"{label:12} n={s['n']:3d}  win%={s['win_rate']:.0%}  "
                    f"avgR={s['avg_R']:+.2f}  PF={pf_str}  "
                    f"{'EDGE' if s['expectancy_positive'] else 'no edge yet'}")
        return "\n".join(lines)


if __name__ == "__main__":
    # synthetic demo: log a handful of signals, simulate outcomes
    j = Journal(path="/tmp/_demo_journal.json")
    j.logs = []  # fresh
    demo = [
        ("AAA", "LOADED", 100, 101, 95, 113),
        ("BBB", "LOADED", 50, 51, 48, 57),
        ("CCC", "MOVING_NOW", 20, 21, 19, 24),
        ("DDD", "MOVING_NOW", 30, 31, 28, 37),
        ("EEE", "catalyst", 200, 202, 190, 230),
    ]
    for tk, st, fp, en, sp, tg in demo:
        j.log_signal(ticker=tk, signal_type=st, flag_price=fp, entry=en,
                     stop=sp, target=tg, taken=True)
    # simulate where each went: AAA hit target, BBB stopped, CCC target, DDD stopped, EEE target
    outcomes = {"AAA": 113, "BBB": 48, "CCC": 24, "DDD": 28, "EEE": 230}
    j.update(price_fn=lambda t: outcomes[t])
    print(j.report())
