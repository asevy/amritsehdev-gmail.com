"""
account_router.py
=================
Routes each candidate to the RIGHT account, based on the trade's intended
holding horizon and the account's cumulative trading frequency.

The key insight: the Tax-Free Savings Account reclassification risk is driven by
the trading PATTERN (frequency, short holds), not by any single trade. So:

  - intraday / few-day momentum  -> personal non-registered
        (frequent + short = keep the day-trading footprint OUT of the TFSA, and
         out of the corporation's passive-income grind; losses stay usable)
  - multi-week to multi-month     -> TFSA (tax-free, hold long enough to be
        position trade           clearly investment, not a business)
  - long-term hold               -> TFSA / RRSP / corporation as fits

It also watches per-account frequency: if the TFSA starts accumulating many
short-hold trades, it warns BEFORE the account looks like a trading business.

NOT tax advice. The corporate passive-income / Small Business Deduction
interaction and the TFSA business-income line should be confirmed with your
accountant. This encodes the shape so routing is deliberate, not accidental.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

Horizon = Literal["intraday", "few_day", "multi_week", "multi_month", "long_term"]


@dataclass
class AccountAdvice:
    ticker: str
    horizon: Horizon
    account: str
    reason: str
    tax_note: str
    frequency_warning: str = ""


# rough horizon -> account mapping
def route(ticker: str, horizon: Horizon,
          tfsa_short_trades_trailing_year: int = 0,
          corp_passive_income_ytd: float = 0.0,
          passive_income_grind_threshold: float = 50_000.0) -> AccountAdvice:
    """Recommend the account for a trade of the given horizon."""
    if horizon in ("intraday", "few_day"):
        acct = "Personal non-registered"
        reason = ("Short hold / higher frequency — keep this pattern out of the "
                  "Tax-Free Savings Account (business-income reclassification risk) "
                  "and out of the corporation (passive-income grind on the Small "
                  "Business Deduction). Losses stay usable personally.")
        tax = ("Capital-gains treatment personally (~26-27% effective at top "
               "Ontario bracket). Losses offset personal capital gains.")
    elif horizon in ("multi_week", "multi_month"):
        acct = "Tax-Free Savings Account"
        reason = ("Hold is long enough to be clearly an investment, not day-trading. "
                  "A multi-week/month winner is exactly what the TFSA is for — "
                  "gain is tax-free.")
        tax = ("Tax-free if the account's overall pattern stays investment-like. "
               "Do NOT let short-hold trades pile up here.")
    else:  # long_term
        acct = "TFSA / RRSP / Corporation (as fits your plan)"
        reason = "Long-term holding — route by your broader plan and contribution room."
        tax = ("TFSA tax-free; RRSP tax-deferred; corporation per your structure. "
               "Forever-holds (index funds) belong here, not in the swing sleeve.")

    warn = ""
    if acct == "Tax-Free Savings Account" and tfsa_short_trades_trailing_year >= 25:
        warn = (f"CAUTION: {tfsa_short_trades_trailing_year} short-hold trades in the "
                "TFSA over the trailing year — the account is starting to look like a "
                "trading business. Move active trades to personal non-registered.")
    if acct.startswith("Personal") and corp_passive_income_ytd > passive_income_grind_threshold:
        warn += (" Note: corporation already over the $50k passive-income threshold "
                 "this year — another reason to keep gains personal, not corporate.")
    return AccountAdvice(ticker, horizon, acct, reason, tax, warn)


def infer_horizon(daily_setup: str, catalyst_days: int | None,
                  intraday_swing: float | None) -> Horizon:
    """Best-guess horizon from the signal mix. You can always override."""
    if intraday_swing is not None and intraday_swing >= 60 and (catalyst_days is None):
        return "few_day"                      # pure intraday momentum
    if catalyst_days is not None and catalyst_days <= 21:
        return "multi_week"                   # catalyst runner — held into/through event
    if daily_setup == "LOADED":
        return "multi_week"                   # coiled breakout, typically held days-weeks
    if daily_setup == "MOVING_NOW":
        return "few_day"
    return "multi_month"


if __name__ == "__main__":
    cases = [
        ("FAST", "MOVING_NOW", None, 72),       # intraday momentum
        ("MRVL", "LOADED", 12, 30),             # catalyst runner, multi-week
        ("COIL", "LOADED", None, None),         # coiled breakout
        ("HOLD", "-", None, None),              # nothing -> longer term
    ]
    for tk, setup, cdays, isw in cases:
        h = infer_horizon(setup, cdays, isw)
        a = route(tk, h, tfsa_short_trades_trailing_year=0)
        print(f"{tk:5} setup={setup:11} -> horizon={h:11} -> {a.account}")
        print(f"      {a.reason}")
    print("\n--- frequency guard demo ---")
    a = route("XYZ", "multi_week", tfsa_short_trades_trailing_year=30)
    print(a.frequency_warning)
