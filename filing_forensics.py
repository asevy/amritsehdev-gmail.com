"""
filing_forensics.py
===================
A Hudson-Labs-style SEC-filing intelligence toolkit, built honestly and free
on top of the SEC's public EDGAR system. Three jobs, one toolkit:

  1. EDGAR retrieval        — pull any US issuer's real filings (10-K/10-Q/8-K).
  2. Forensic red-flag engine — DETERMINISTIC text detection of the high-value
                                "something's rotten" signals: going-concern,
                                material weakness, auditor change, executive
                                turnover, restatement, late filing (NT), rising
                                related-party / dilution language. No LLM, no
                                hallucination, free. This is the part that
                                catches trouble BEFORE it's priced in.
  3. Cite-or-N/A Q&A         — an LLM layer that answers questions about a filing
                                but is FORCED to quote the source sentence or
                                return "N/A". Mirrors Hudson Labs' core discipline:
                                if it's not in the document, it does not invent it.
                                (Needs your own Anthropic API key to run.)

  + FUSION: `screen_with_forensics` filters the swing_scanner's coiled/moving
    names through filing risk — so a "LOADED" coiled-spring with a going-concern
    flag is correctly demoted from "setup" to "trap".

HONEST LIMITS
-------------
- Deterministic flags are high-precision on the language patterns they target,
  but they are signals to INVESTIGATE, not verdicts. Always click through to the
  cited sentence (the toolkit gives you the offset).
- This does not replicate Hudson Labs' multi-model retrieval polish or its S&P
  valuation data. It replicates the *technique* and the *discipline*, free, and
  fuses it with your own scanner — which is the part you can't buy off the shelf.
- EDGAR requires a descriptive User-Agent with contact info (SEC rule). Set yours.

DEPENDENCIES: requests (or urllib).  LLM layer: anthropic.
"""

from __future__ import annotations
import re, json, time, html
from dataclasses import dataclass, field, asdict
from typing import Optional

SEC_UA = "your-name your-email@example.com"   # <-- SET THIS (SEC requires it)
EDGAR_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
EDGAR_DOC = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"
EDGAR_TICKER_MAP = "https://www.sec.gov/files/company_tickers.json"


# ----------------------------------------------------------------------
# 1. EDGAR retrieval
# ----------------------------------------------------------------------
def _get(url: str, as_json=True, retries=3):
    import requests
    for i in range(retries):
        r = requests.get(url, headers={"User-Agent": SEC_UA,
                                       "Accept-Encoding": "gzip, deflate"})
        if r.status_code == 200:
            return r.json() if as_json else r.text
        time.sleep(0.5 * (i + 1))   # SEC rate-limit politeness (<=10 req/s)
    r.raise_for_status()


def ticker_to_cik(ticker: str) -> Optional[int]:
    """Map a ticker to its SEC Central Index Key (CIK)."""
    data = _get(EDGAR_TICKER_MAP)
    t = ticker.upper()
    for row in data.values():
        if row["ticker"].upper() == t:
            return int(row["cik_str"])
    return None


def latest_filings(cik: int, forms=("10-K", "10-Q", "8-K"), limit=10) -> list[dict]:
    """Return metadata for a company's most recent filings of the given forms."""
    data = _get(EDGAR_SUBMISSIONS.format(cik=cik))
    recent = data["filings"]["recent"]
    out = []
    for form, acc, doc, date, pdoc in zip(
        recent["form"], recent["accessionNumber"], recent["primaryDocument"],
        recent["filingDate"], recent["primaryDocDescription"]):
        if form in forms:
            out.append({
                "form": form, "date": date, "accession": acc, "doc": doc,
                "desc": pdoc,
                "url": EDGAR_DOC.format(cik=cik, acc_nodash=acc.replace("-", ""), doc=doc),
            })
        if len(out) >= limit:
            break
    return out


def fetch_filing_text(url: str) -> str:
    """Download a filing and strip it to plain text for analysis."""
    raw = _get(url, as_json=False)
    raw = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", raw)
    txt = re.sub(r"(?s)<[^>]+>", " ", raw)
    txt = html.unescape(txt)
    txt = re.sub(r"[ \t\u00a0]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n\n", txt)
    return txt.strip()


# ----------------------------------------------------------------------
# 2. Deterministic forensic red-flag engine
# ----------------------------------------------------------------------
# Each flag: (key, severity 1-3, human label, list of regex patterns).
# Patterns are written to catch the *disclosure language* companies are
# legally required to use — which is why deterministic detection works.
FLAG_RULES = [
    ("going_concern", 3, "Going-concern / survival doubt", [
        r"substantial doubt about (?:its|our|the company.?s) ability to continue as a going concern",
        r"going concern", r"may (?:not|be unable to) continue as a going concern"]),
    ("material_weakness", 3, "Material weakness in internal controls", [
        r"material weakness(?:es)? (?:in|relating to) (?:our|its|the company.?s)? ?internal control",
        r"not effective.{0,80}internal control over financial reporting",
        r"internal control over financial reporting.{0,80}(?:was|were) not effective",
        r"material weakness(?:es)?.{0,80}internal control",
        r"identified a material weakness"]),
    ("restatement", 3, "Restatement of prior financials", [
        r"restat(?:e|ed|ement) (?:of|its|our|the) .{0,40}financial statements",
        r"non-?reliance on previously issued financial statements",
        r"should no longer be relied upon"]),
    ("auditor_change", 2, "Auditor change / dismissal / resignation", [
        r"dismiss(?:ed|al of) (?:our|its|the) (?:independent )?(?:registered public accounting firm|auditor)",
        r"(?:auditor|accounting firm) (?:resigned|declined to stand)",
        r"change in (?:our )?(?:certifying accountant|independent auditor)"]),
    ("late_filing", 2, "Late filing / NT (notification of inability to file timely)", [
        r"unable to file.{0,40}(?:within the prescribed time|on a timely basis)",
        r"could not be (?:completed|filed) (?:without unreasonable effort|by the prescribed)",
        r"\bForm\s+NT\b", r"notification of (?:late|inability to) fil"]),
    ("liquidity_stress", 2, "Liquidity / covenant / default stress", [
        r"may not have sufficient (?:liquidity|cash|capital resources)",
        r"breach(?:ed)? .{0,30}covenant", r"event of default", r"cross-default",
        r"need(?:s|ed)? to raise additional (?:capital|financing)"]),
    ("dilution_risk", 1, "Dilution / heavy share issuance language", [
        r"may issue (?:a )?(?:substantial|significant) (?:additional )?(?:number of )?shares",
        r"at-the-market offering", r"sell .{0,20}shares .{0,20}from time to time",
        r"substantial dilution"]),
    ("related_party", 1, "Related-party transaction concentration", [
        r"related part(?:y|ies) transaction", r"transactions with related parties"]),
    ("exec_turnover", 1, "Executive / CFO departure", [
        r"(?:chief financial officer|chief executive officer|principal accounting officer)"
        r".{0,40}(?:resign|depart|step(?:ped)? down|terminat)",
        r"(?:resignation|departure) of .{0,30}(?:CFO|CEO|chief)"]),
    ("impairment", 1, "Goodwill / asset impairment", [
        r"goodwill impairment", r"impairment (?:charge|of (?:goodwill|long-lived))"]),
]


@dataclass
class FlagHit:
    key: str
    severity: int
    label: str
    excerpt: str           # the actual sentence — your audit trail
    offset: int


@dataclass
class ForensicReport:
    ticker: str
    form: str = ""
    date: str = ""
    url: str = ""
    risk_score: int = 0          # weighted sum of severities
    hits: list = field(default_factory=list)
    summary: str = ""

    def as_dict(self):
        d = asdict(self)
        d["hits"] = [asdict(h) if isinstance(h, FlagHit) else h for h in self.hits]
        return d


def _excerpt(text: str, start: int, span: int = 240) -> str:
    a = max(0, start - 40); b = min(len(text), start + span)
    return re.sub(r"\s+", " ", text[a:b]).strip()


def forensic_scan(text: str, ticker: str = "", meta: dict | None = None) -> ForensicReport:
    """Run the deterministic red-flag engine over filing text."""
    rep = ForensicReport(ticker=ticker)
    if meta:
        rep.form, rep.date, rep.url = meta.get("form", ""), meta.get("date", ""), meta.get("url", "")
    low = text.lower()
    seen = set()
    for key, sev, label, patterns in FLAG_RULES:
        for pat in patterns:
            m = re.search(pat, low)
            if m and key not in seen:
                seen.add(key)
                rep.hits.append(FlagHit(key, sev, label,
                                        _excerpt(text, m.start()), m.start()))
                rep.risk_score += sev * sev   # square so severe flags dominate
                break
    rep.hits.sort(key=lambda h: -h.severity)
    if rep.hits:
        top = "; ".join(f"{h.label}" for h in rep.hits[:4])
        rep.summary = f"{len(rep.hits)} flag(s), risk {rep.risk_score}: {top}"
    else:
        rep.summary = "No forensic red flags detected in this filing's language."
    return rep


def forensic_report_for_ticker(ticker: str, form="10-K") -> ForensicReport:
    """End-to-end: ticker -> latest filing -> forensic report."""
    cik = ticker_to_cik(ticker)
    if cik is None:
        return ForensicReport(ticker=ticker, summary="CIK not found on EDGAR.")
    fs = latest_filings(cik, forms=(form,), limit=1)
    if not fs:
        return ForensicReport(ticker=ticker, summary=f"No {form} found.")
    meta = fs[0]
    txt = fetch_filing_text(meta["url"])
    return forensic_scan(txt, ticker=ticker, meta=meta)


# ----------------------------------------------------------------------
# 3. LLM cite-or-N/A Q&A (Hudson Labs' core discipline)
# ----------------------------------------------------------------------
CITE_SYSTEM = (
    "You are a forensic equity-research analyst reading an SEC filing. "
    "Answer ONLY from the provided filing text. For every claim you make, quote "
    "the exact supporting sentence in double quotes. If the filing does not "
    "contain the answer, respond with exactly 'N/A' and nothing else. Never use "
    "outside knowledge. Never infer numbers not present. Prefer 'N/A' over a guess."
)


def ask_filing(question: str, filing_text: str,
               model: str = "claude-opus-4-20250514",
               max_chars: int = 180_000) -> str:
    """Ask a question about a filing with cite-or-N/A discipline.
    Requires `anthropic` and ANTHROPIC_API_KEY in your environment."""
    import anthropic
    client = anthropic.Anthropic()
    snippet = filing_text[:max_chars]
    msg = client.messages.create(
        model=model, max_tokens=1500, system=CITE_SYSTEM,
        messages=[{"role": "user",
                   "content": f"FILING TEXT:\n{snippet}\n\nQUESTION: {question}\n\n"
                              f"Answer with citations, or 'N/A'."}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


# ----------------------------------------------------------------------
# 4. FUSION — filter the swing scanner through filing risk
# ----------------------------------------------------------------------
def screen_with_forensics(scanner_df, top_n: int = 15, form="10-K",
                          fetch=forensic_report_for_ticker):
    """Take the swing_scanner output and add a forensic risk column.
    A coiled/moving name with serious filing flags is a TRAP, not a setup.
    Returns the dataframe with: filing_risk, filing_flags, verdict."""
    import pandas as pd
    df = scanner_df.copy()
    df = df.head(top_n)
    risks, flagstr, verdict = [], [], []
    for _, row in df.iterrows():
        t = row["ticker"]
        try:
            rep = fetch(t, form=form)
            risks.append(rep.risk_score)
            flagstr.append("; ".join(h.label for h in rep.hits[:3]) if rep.hits else "")
        except Exception as e:
            risks.append(float("nan")); flagstr.append(f"err:{e}")
        # verdict logic: high price signal + clean filings = real; + flags = trap
        sig = max(row.get("moving_now", 0), row.get("loaded", 0))
        r = risks[-1]
        if r != r:                       # NaN
            verdict.append("filing_unknown")
        elif r >= 9:
            verdict.append("TRAP-serious-filing-risk")
        elif r >= 4 and sig >= 60:
            verdict.append("caution-investigate-filing")
        elif sig >= 60:
            verdict.append("clean-setup")
        else:
            verdict.append("low-signal")
    df["filing_risk"] = risks
    df["filing_flags"] = flagstr
    df["verdict"] = verdict
    return df.sort_values(["verdict", "filing_risk"]).reset_index(drop=True)


# ----------------------------------------------------------------------
# Self-test of the deterministic engine with realistic filing language
# ----------------------------------------------------------------------
if __name__ == "__main__":
    troubled = """
    Item 1A. Risk Factors. Our recurring losses and negative working capital
    raise substantial doubt about our ability to continue as a going concern.
    Management has concluded that our internal control over financial reporting
    was not effective as of December 31 due to a material weakness relating to
    revenue recognition. On March 2 we dismissed our independent registered
    public accounting firm. We may issue a substantial number of additional
    shares through an at-the-market offering, which would cause substantial
    dilution. The Chief Financial Officer resigned effective immediately.
    """
    healthy = """
    Item 1A. Risk Factors. Competition in our markets is intense. Our results
    may fluctuate with macroeconomic conditions and foreign exchange rates.
    We maintain effective internal control over financial reporting and our
    independent auditor issued an unqualified opinion. We generated strong
    free cash flow and returned capital through buybacks.
    """
    for name, txt in [("TROUBLED_CO", troubled), ("HEALTHY_CO", healthy)]:
        rep = forensic_scan(txt, ticker=name)
        print(f"\n=== {name} ===")
        print(rep.summary)
        for h in rep.hits:
            print(f"  [sev {h.severity}] {h.label}")
            print(f"      -> \"{h.excerpt[:90]}...\"")
