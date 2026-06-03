"""
risk_manager.py
===============
The safeguards. Turns a signal + a stop into a correctly-SIZED order, and
enforces hard limits that protect the sleeve from a bad day or a tilt streak.

POSITION SIZING (the missing half of a stop):
  shares = (sleeve_value * risk_per_trade) / (entry - stop)
  i.e. you risk a fixed small % of the sleeve per trade; the stop distance
  decides the size. Tight stop -> bigger position; wide stop -> smaller.
  Position is also capped at max_position_pct of the sleeve regardless.

CIRCUIT BREAKERS (enforced, not advisory):
  - daily_loss_limit      : down this % on the day -> HALT for the day
  - max_concurrent        : cap on open positions
  - max_total_exposure    : cap on total $ at work
  - consecutive_loss_halt : N losses in a row -> HALT, human review

EXECUTION MODE:
  - "suggest" : returns the order for you to place yourself (recommended)
  - "auto"    : would place automatically — ONLY behind the kill-switch and
                hard caps. A flash move, API error, or bug has no human in the
                loop, so the breakers matter far more here.
  kill_switch(): one call halts all further orders until manually reset.

Honest: this controls RISK, it does not create edge. Fund real money only after
the journal shows positive expectancy. Start in "suggest" mode.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Optional
import math


@dataclass
class RiskConfig:
    sleeve_value: float = 50_000.0          # the ring-fenced swing capital
    risk_per_trade: float = 0.0075          # 0.75% of sleeve risked per trade
    max_position_pct: float = 0.20          # no single position > 20% of sleeve
    daily_loss_limit: float = 0.03          # halt if down 3% on the day
    max_concurrent: int = 5
    max_total_exposure_pct: float = 0.80    # at most 80% of sleeve deployed
    consecutive_loss_halt: int = 4
    mode: Literal["suggest", "auto"] = "suggest"


@dataclass
class Order:
    ticker: str
    side: str
    shares: int
    entry: float
    stop: float
    dollar_risk: float
    position_value: float
    account: str = ""
    note: str = ""
    blocked_reason: str = ""

    @property
    def allowed(self) -> bool:
        return not self.blocked_reason


class RiskManager:
    def __init__(self, cfg: RiskConfig = RiskConfig()):
        self.cfg = cfg
        self.open_positions: dict[str, Order] = {}
        self.realized_today: float = 0.0
        self.consecutive_losses: int = 0
        self._halted: bool = False
        self._halt_reason: str = ""

    # --- kill switch ---------------------------------------------------
    def kill_switch(self, reason: str = "manual kill switch"):
        self._halted = True
        self._halt_reason = reason

    def reset(self):
        self._halted = False
        self._halt_reason = ""
        self.realized_today = 0.0
        self.consecutive_losses = 0

    @property
    def halted(self) -> bool:
        return self._halted

    # --- sizing + checks ----------------------------------------------
    def size_order(self, ticker: str, entry: float, stop: float,
                   account: str = "") -> Order:
        c = self.cfg
        risk_per_share = entry - stop
        if risk_per_share <= 0:
            return Order(ticker, "buy", 0, entry, stop, 0, 0, account,
                         blocked_reason="invalid stop (>= entry)")
        dollar_risk = c.sleeve_value * c.risk_per_trade
        shares = math.floor(dollar_risk / risk_per_share)
        pos_value = shares * entry
        # cap by max position size
        cap_value = c.sleeve_value * c.max_position_pct
        if pos_value > cap_value:
            shares = math.floor(cap_value / entry)
            pos_value = shares * entry
        order = Order(ticker, "buy", shares, entry, stop,
                      round(shares * risk_per_share, 2), round(pos_value, 2), account)

        # --- circuit breakers ---
        block = self._check_breakers(order)
        if block:
            order.blocked_reason = block
        elif shares <= 0:
            order.blocked_reason = "size rounds to zero (stop too wide for sleeve)"
        else:
            order.note = (f"risk ${order.dollar_risk:.0f} "
                          f"({c.risk_per_trade:.2%} of sleeve), "
                          f"{order.position_value/c.sleeve_value:.0%} of sleeve")
        return order

    def _check_breakers(self, order: Order) -> str:
        c = self.cfg
        if self._halted:
            return f"HALTED: {self._halt_reason}"
        if self.realized_today <= -c.daily_loss_limit * c.sleeve_value:
            self.kill_switch("daily loss limit hit")
            return "HALTED: daily loss limit hit"
        if self.consecutive_losses >= c.consecutive_loss_halt:
            self.kill_switch(f"{self.consecutive_losses} losses in a row")
            return f"HALTED: {self.consecutive_losses} consecutive losses"
        if len(self.open_positions) >= c.max_concurrent:
            return f"blocked: max {c.max_concurrent} concurrent positions"
        current_exposure = sum(o.position_value for o in self.open_positions.values())
        if current_exposure + order.position_value > c.max_total_exposure_pct * c.sleeve_value:
            return (f"blocked: would exceed {c.max_total_exposure_pct:.0%} "
                    "total-exposure cap")
        return ""

    # --- lifecycle -----------------------------------------------------
    def place(self, order: Order) -> str:
        if not order.allowed:
            return f"NOT PLACED ({order.blocked_reason})"
        self.open_positions[order.ticker] = order
        if self.cfg.mode == "auto":
            return f"AUTO-PLACED {order.shares} {order.ticker} @ {order.entry} (stop {order.stop})"
        return (f"SUGGESTED (place yourself): BUY {order.shares} {order.ticker} "
                f"@ {order.entry}, STOP {order.stop} | {order.note}")

    def record_exit(self, ticker: str, exit_price: float):
        o = self.open_positions.pop(ticker, None)
        if not o:
            return
        pnl = (exit_price - o.entry) * o.shares
        self.realized_today += pnl
        self.consecutive_losses = self.consecutive_losses + 1 if pnl <= 0 else 0
        # re-check breakers after the loss
        if self.realized_today <= -self.cfg.daily_loss_limit * self.cfg.sleeve_value:
            self.kill_switch("daily loss limit hit")
        if self.consecutive_losses >= self.cfg.consecutive_loss_halt:
            self.kill_switch(f"{self.consecutive_losses} losses in a row")
        return round(pnl, 2)


if __name__ == "__main__":
    rm = RiskManager(RiskConfig(sleeve_value=50_000, risk_per_trade=0.0075, mode="suggest"))
    print("--- sizing ---")
    o1 = rm.size_order("GEV", entry=200, stop=192, account="Personal non-reg")
    print(o1.shares, "shares |", rm.place(o1))
    o2 = rm.size_order("ETN", entry=400, stop=390, account="Personal non-reg")
    print(o2.shares, "shares |", rm.place(o2))
    o3 = rm.size_order("VRT", entry=320, stop=300, account="TFSA")
    print(o3.shares, "shares |", rm.place(o3))

    print("\n--- a wide stop shrinks size automatically ---")
    o4 = rm.size_order("WIDE", entry=100, stop=60)   # huge risk/share
    print(o4.shares, "shares |", rm.place(o4), "| risk/share large -> tiny position")

    print("\n--- circuit breaker: simulate consecutive losses ---")
    for tk, ex in [("GEV", 192), ("ETN", 390), ("VRT", 300)]:
        pnl = rm.record_exit(tk, ex)
        print(f"exit {tk} pnl={pnl}  consec_losses={rm.consecutive_losses}  halted={rm.halted}")
    o5 = rm.size_order("NEXT", entry=50, stop=48)
    print("next order:", rm.place(o5))
