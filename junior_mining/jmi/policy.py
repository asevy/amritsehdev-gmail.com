"""No-score policy guard (brief §2, §16, §17 case 16).

Checks generated payloads — API responses, exports, rendered pages — for
investment scores or equivalents: score/rating/confidence/probability fields,
star glyphs, "N/10" scores, letter grades, confidence percentages,
recommendation labels and traffic-light status classes.

Mining "grade" (g/t, %) is a physical measurement and is allowed. Text quoted
from source documents is data, not something this application asserts, so
quote fields are skipped (a document may itself contain the word "rating").
"""

from __future__ import annotations

import re

SOURCE_TEXT_KEYS = {"raw_text", "quote", "context", "text", "excerpt", "snip", "wording", "original_wording",
                    "detail", "statement", "message", "question", "rows", "footnotes", "title", "caption"}

ALLOWED_KEYS = {"resource_grade", "reserve_grade", "drill_intercept_grade", "grade", "cutoff_g_t",
                "average_grade"}
FORBIDDEN_KEY = re.compile(
    r"(^|_)(score|scores|scoring|rating|ratings|rated|stars?|confidence|probabilit\w*|likelihood|rank|ranking|"
    r"verdict|recommendation|recommend\w*|price_target|risk_level|severity|traffic_light|quality_pct|"
    r"letter_grade|grade_letter|investment_grade)($|_)", re.I)

FORBIDDEN_VALUE = [
    re.compile(r"[★☆✩✪⭐]"),
    re.compile(r"\b\d+(?:\.\d+)?\s*/\s*(?:5|10|100)\b(?!\s*(?:oz|g|t|m)\b)"),
    re.compile(r"\b\d{1,3}(?:\.\d+)?\s*%\s*(?:confidence|confident|likely|likelihood|probability|chance)\b", re.I),
    re.compile(r"\bconfidence(?:\s+(?:score|level))?\s*[:=]\s*\d", re.I),
    re.compile(r"\bprobability of (?:success|production)\s*[:=]?\s*\d", re.I),
    re.compile(r"^(?:strong\s+)?(?:buy|sell|hold|outperform|underperform|accumulate)$", re.I),
    re.compile(r"\b(?:rating|score)\s*[:=]\s*\S", re.I),
    re.compile(r"\b[A-F][+-]?\s+(?:rating|grade)\b"),
    re.compile(r"\b(?:high|medium|low)[- ]risk\b", re.I),
]

FORBIDDEN_CSS = re.compile(r"class=\"[^\"]*\b(?:traffic|rag-|score|rating|stars?|badge-(?:red|amber|green))\b", re.I)


def scan(payload, path: str = "") -> list[str]:
    """Return violations found in a JSON-like payload."""
    out = []
    if isinstance(payload, dict):
        for k, v in payload.items():
            ks = str(k)
            if ks not in ALLOWED_KEYS and FORBIDDEN_KEY.search(ks):
                out.append(f"{path}/{ks}: forbidden field name")
            if ks in SOURCE_TEXT_KEYS:
                continue
            out.extend(scan(v, f"{path}/{ks}"))
    elif isinstance(payload, (list, tuple)):
        for i, v in enumerate(payload):
            out.extend(scan(v, f"{path}/{i}"))
    elif isinstance(payload, str):
        for rx in FORBIDDEN_VALUE:
            if rx.search(payload):
                out.append(f"{path}: value matches {rx.pattern!r}: {payload[:80]!r}")
    return out


def scan_html(html: str) -> list[str]:
    """Generated pages: CSS classes and visible app text (quotes are inside <q>/<blockquote>)."""
    out = [f"css: {m.group(0)}" for m in FORBIDDEN_CSS.finditer(html)]
    stripped = re.sub(r"(?is)<(blockquote|q|pre)[^>]*>.*?</\1>", " ", html)
    stripped = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", stripped)
    text = re.sub(r"<[^>]+>", " ", stripped)
    for rx in FORBIDDEN_VALUE:
        if rx.pattern.startswith("^"):
            continue
        for m in rx.finditer(text):
            out.append(f"text matches {rx.pattern!r}: {text[max(0, m.start() - 30):m.end() + 30]!r}")
    return out


def schema_fields() -> list[str]:
    """Every column name in the canonical schema, for the schema-level check."""
    import sqlite3
    from .db import migrate
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    names = []
    for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        for r in conn.execute(f"PRAGMA table_info({t})"):
            names.append(f"{t}.{r[1]}")
    conn.close()
    return names
