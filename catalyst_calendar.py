"""
catalyst_calendar.py
====================
The honest "about to" timing layer. You cannot know the OUTCOME of an event,
but you can know the DATE. This module surfaces scheduled catalysts so a coiled,
fundamentally-clean stock with an event in the next N days floats to the top.

Catalyst types (in rough order of how reliably they move a stock):
  - earnings date            (scheduled, highest-frequency mover)
  - ex-dividend / guidance    (scheduled)
  - known product/keynote events, index rebalances (manual calendar)

Default feed: yfinance (free, has earnings dates). Swap `get_earnings_date`
for your data provider for fuller coverage (FDA dates, conferences, etc.).
"""
from __future__ import annotations
import datetime as dt
from dataclasses import dataclass
from typing import Optional


@dataclass
class Catalyst:
    ticker: str
    kind: str
    date: Optional[dt.date]
    days_away: Optional[int]
    note: str = ""


def get_earnings_date(ticker: str) -> Optional[dt.date]:
    """Next scheduled earnings date via yfinance. Replace with your feed."""
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        cal = yf.Ticker(ticker).get_earnings_dates(limit=8)
        if cal is None or len(cal) == 0:
            return None
        today = dt.date.today()
        future = [d.date() for d in cal.index if d.date() >= today]
        return min(future) if future else None
    except Exception:
        return None


# manual calendar for events no feed has (keynotes, FDA, index rebalances)
MANUAL_CATALYSTS: dict[str, list[tuple[str, str, str]]] = {
    # "TICKER": [("YYYY-MM-DD", "kind", "note"), ...]
    # e.g. "NVDA": [("2026-06-09", "keynote", "GTC keynote")],
}


def catalysts_for(ticker: str, horizon_days: int = 21) -> list[Catalyst]:
    """All known catalysts within horizon_days. Earnings + manual events."""
    today = dt.date.today()
    out: list[Catalyst] = []

    ed = get_earnings_date(ticker)
    if ed is not None:
        days = (ed - today).days
        if 0 <= days <= horizon_days:
            out.append(Catalyst(ticker, "earnings", ed, days, "scheduled earnings"))

    for ds, kind, note in MANUAL_CATALYSTS.get(ticker.upper(), []):
        try:
            d = dt.date.fromisoformat(ds)
        except ValueError:
            continue
        days = (d - today).days
        if 0 <= days <= horizon_days:
            out.append(Catalyst(ticker, kind, d, days, note))

    out.sort(key=lambda c: (c.days_away if c.days_away is not None else 999))
    return out


def catalyst_score(ticker: str, horizon_days: int = 21) -> tuple[float, str]:
    """0..100 timing score: nearer scheduled catalyst = higher. Honest 'about to'.
    Returns (score, label). Score peaks a few days before the event."""
    cats = catalysts_for(ticker, horizon_days)
    if not cats:
        return 0.0, ""
    c = cats[0]
    d = c.days_away if c.days_away is not None else horizon_days
    # peak ~2-7 days out (pre-positioning window), taper to event and far out
    if d <= 1:
        s = 55          # day-of: move may already be underway
    elif d <= 7:
        s = 100 - (d - 2) * 4      # 2-7 days = the sweet spot
    else:
        s = max(0, 70 - (d - 7) * 4)
    label = f"{c.kind} in {d}d ({c.date})"
    return float(s), label


if __name__ == "__main__":
    # offline self-test of the scoring curve (no feed needed)
    import datetime as _dt
    base = _dt.date.today()
    def fake(days):  # simulate a catalyst N days away
        MANUAL_CATALYSTS["TEST"] = [((base + _dt.timedelta(days=days)).isoformat(),
                                     "earnings", "test")]
        return catalyst_score("TEST")
    for d in [0, 1, 3, 5, 7, 12, 20, 40]:
        s, lbl = fake(d)
        print(f"{d:3d} days away -> score {s:5.1f}  {lbl}")
