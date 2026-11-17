"""Decimal-safe parsing of printed numbers, units, currencies and dates.

Rules:
  * Values are decimal.Decimal end to end. Floats never touch a quantity.
  * Every transformation from the printed token to the canonical value is
    recorded (scale words, unit conversion, sign from parentheses).
  * The precision a figure was printed with defines its tolerance: "US$412
    million" means [411.5, 412.5] million. Two reports reconcile when their
    intervals overlap — that is the defined rounding tolerance.
  * A token that looks like an OCR error ("1O.5") is NOT corrected. It is
    returned as unparsed with a warning so a reviewer decides.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, getcontext

getcontext().prec = 34

SCALE = {
    "": 0, "thousand": 3, "thousands": 3, "k": 3, "000s": 3, "000's": 3, "'000": 3, "000": 3,
    "million": 6, "millions": 6, "m": 6, "mm": 6, "mln": 6,
    "billion": 9, "billions": 9, "bn": 9, "b": 9,
}

CURRENCY = {
    "us$": "USD", "usd": "USD", "u.s.$": "USD",
    "c$": "CAD", "cad": "CAD", "cdn$": "CAD", "ca$": "CAD",
    "a$": "AUD", "aud": "AUD",
    "$": None,  # ambiguous: resolved only from declared document currency
}

# canonical unit, exponent of the multiplier to reach it
METAL = {"oz": ("oz", 0), "ounces": ("oz", 0), "koz": ("oz", 3), "000 oz": ("oz", 3),
         "000s oz": ("oz", 3), "moz": ("oz", 6), "million ounces": ("oz", 6)}
MASS = {"t": ("t", 0), "tonnes": ("t", 0), "kt": ("t", 3), "000 t": ("t", 3), "000s": ("t", 3),
        "mt": ("t", 6), "million tonnes": ("t", 6)}
GRADE = {"g/t": "g/t", "gpt": "g/t", "g/t au": "g/t", "au g/t": "g/t", "%": "%"}
LENGTH = {"m": "m", "metres": "m", "meters": "m", "metre": "m"}

_OCR_SUSPECT = re.compile(r"\d[OoIl]|[OoIl]\d")
_NUM = re.compile(r"^\(?-?[\d,]*\.?\d+\)?$")


@dataclass
class Parsed:
    value: Decimal | None
    decimals: int = 0
    negative: bool = False
    transformations: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def parse_number(token: str) -> Parsed:
    raw = (token or "").strip()
    t = raw.replace("−", "-").replace(" ", "").replace(" ", "")
    if _OCR_SUSPECT.search(t):
        return Parsed(None, warnings=[f"possible OCR error in '{raw}'; not corrected automatically"])
    if not _NUM.match(t):
        return Parsed(None, warnings=[f"not a number: '{raw}'"])
    tr = []
    neg = t.startswith("(") and t.endswith(")")
    if neg:
        t = t[1:-1]
        tr.append("parentheses read as negative")
    if t.startswith("-"):
        neg, t = True, t[1:]
    if "," in t:
        t = t.replace(",", "")
        tr.append("thousands separators removed")
    try:
        v = Decimal(t)
    except InvalidOperation:
        return Parsed(None, warnings=[f"not a number: '{raw}'"])
    decimals = len(t.split(".", 1)[1]) if "." in t else 0
    return Parsed(-v if neg else v, decimals, neg, tr)


def interval(value: Decimal, decimals: int, multiplier_exp: int = 0) -> tuple[Decimal, Decimal]:
    half = Decimal(5) * Decimal(10) ** (-(decimals + 1)) * Decimal(10) ** multiplier_exp
    return value - half, value + half


def overlaps(a: tuple, b: tuple) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def scale_exp(word: str | None) -> int | None:
    if word is None:
        return 0
    w = word.strip().lower().strip("()")
    return SCALE.get(w)


def currency_code(token: str | None) -> str | None:
    if not token:
        return None
    return CURRENCY.get(token.strip().lower(), "?")


def quantize(value: Decimal, decimals: int) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_EVEN)


def fmt(value: Decimal | None, decimals: int = 2, divisor: str = "1") -> str:
    if value is None:
        return "—"
    v = quantize(Decimal(value) / Decimal(divisor), decimals)
    s = f"{v:,.{decimals}f}"
    return s


def dec(text: str | None) -> Decimal | None:
    if text is None or text == "":
        return None
    return Decimal(str(text))


# ------------------------------------------------------------------ dates
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september",
     "october", "november", "december"], start=1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS["sept"] = 9

DATE_RX = re.compile(   # \s+ because PDF text wraps dates across lines
    r"(?P<iso>\d{4}-\d{2}-\d{2})"
    r"|(?P<m1>[A-Z][a-z]{2,8})\.?\s+(?P<d1>\d{1,2}),?\s+(?P<y1>\d{4})"
    r"|(?P<d2>\d{1,2})\s+(?P<m2>[A-Z][a-z]{2,8}),?\s+(?P<y2>\d{4})")

_ASOF_BEFORE = re.compile(r"(?:as\s+at|as\s+of|at|on|ended|effective(?:\s+date\s+of)?)\s*,?\s*$", re.I)


def as_of_dates(text: str) -> list[str]:
    """Dates introduced by an as-of style phrase ("As at <date>", "ended <date>")."""
    out = []
    for m in DATE_RX.finditer(text or ""):
        if _ASOF_BEFORE.search(text[max(0, m.start() - 24):m.start()]):
            d = parse_date(m.group(0))
            if d:
                out.append(d)
    return out


def parse_date(text: str | None) -> str | None:
    """First explicit calendar date in `text` as ISO 8601, else None."""
    if not text:
        return None
    for m in DATE_RX.finditer(text):
        try:
            if m.group("iso"):
                return date.fromisoformat(m.group("iso")).isoformat()
            mon = (m.group("m1") or m.group("m2")).lower()
            if mon not in MONTHS:
                continue
            d = int(m.group("d1") or m.group("d2"))
            y = int(m.group("y1") or m.group("y2"))
            return date(y, MONTHS[mon], d).isoformat()
        except ValueError:
            continue
    return None


def all_dates(text: str) -> list[str]:
    out = []
    for m in DATE_RX.finditer(text or ""):
        d = parse_date(m.group(0))
        if d:
            out.append(d)
    return out


_Q = re.compile(r"\bQ([1-4])\s*(\d{4})\b", re.I)
_H = re.compile(r"\bH([12])\s*(\d{4})\b", re.I)
_QWORD = re.compile(r"\b(first|second|third|fourth) quarter of (\d{4})\b", re.I)
_MONTHYEAR = re.compile(r"\b([A-Z][a-z]{2,8}) (\d{4})\b")
_YEAREND = re.compile(r"\b(?:by )?(?:the )?end of (\d{4})\b", re.I)


def target_window(text: str) -> tuple[str | None, str | None, str]:
    """Interpret a management target expression. Unambiguous forms only.

    Returns (start, end, note). For forms such as "mid-2027" or "in the coming
    months" the window is left empty with a note: a reviewer sets it, the
    software does not guess.
    """
    import calendar
    m = _Q.search(text)
    if m:
        q, y = int(m.group(1)), int(m.group(2))
        sm = 3 * (q - 1) + 1
        em = sm + 2
        return (date(y, sm, 1).isoformat(),
                date(y, em, calendar.monthrange(y, em)[1]).isoformat(), "calendar quarter")
    m = _QWORD.search(text)
    if m:
        q = ["first", "second", "third", "fourth"].index(m.group(1).lower()) + 1
        y = int(m.group(2))
        sm = 3 * (q - 1) + 1
        em = sm + 2
        return (date(y, sm, 1).isoformat(),
                date(y, em, calendar.monthrange(y, em)[1]).isoformat(), "calendar quarter")
    m = _H.search(text)
    if m:
        h, y = int(m.group(1)), int(m.group(2))
        return ((date(y, 1, 1) if h == 1 else date(y, 7, 1)).isoformat(),
                (date(y, 6, 30) if h == 1 else date(y, 12, 31)).isoformat(), "calendar half-year")
    m = _YEAREND.search(text)
    if m:
        y = int(m.group(1))
        return None, date(y, 12, 31).isoformat(), "no later than calendar year end"
    m = _MONTHYEAR.search(text)
    if m and m.group(1).lower() in MONTHS:
        y, mo = int(m.group(2)), MONTHS[m.group(1).lower()]
        return (date(y, mo, 1).isoformat(),
                date(y, mo, calendar.monthrange(y, mo)[1]).isoformat(), "calendar month")
    return None, None, "target window not machine-interpretable; reviewer to set"
