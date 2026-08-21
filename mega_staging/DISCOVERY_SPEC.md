# DISCOVERY ANALYST SPEC — Phase 1.5
*Extends PHASE_1_SPEC.md. Read that first.*

**Owner decision (Amrit, 2026-08-20): STRICT-WITH-FLAG.**
New gate-passers found outside the 312-name pre-registered universe are
NEVER auto-promoted. They land in a parallel list with a one-paragraph
analyst rationale. Amrit reviews monthly, hand-adds anything worth adding
AFTER the July 20 2027 judgment.

**Owner decision (Amrit, 2026-08-20): FLAG-WITH-REASONS pattern is authoritative.**
The analyst never overrides gates. It flags names that fail one gate with
a written rationale citing a specific filing line. Human decides.

---

## 1. What discovery does

- Runs **quarterly** (fundamentals don't change faster than that).
- Ingests **~2,000–3,000 US-listed common stocks** filtered by market cap
  (≥ $2B) and average daily dollar volume (≥ $20M).
- Runs the **same six gates** as the frozen `quality_value_screener.py`
  (reused via the contract in §4 — does NOT reimplement, does NOT modify).
- Emits three lists:
  1. **New passers** — cleared all six gates, not currently in the 312. Each
     one carries an auto-tag set (sector, size) and any manual tags (theme).
  2. **Flagged near-passers** — failed exactly one gate, with an analyst
     rationale that cites the specific filing line and offers a reason the
     failure might not matter. Max **2 flags per quarterly run**.
  3. **Silence** — if either list is empty, the digest says so explicitly.

## 2. What discovery does NOT do

- Does NOT touch `quality_value_screener.py` or `alpha_screener.py`
  (freeze until 2027-07-20).
- Does NOT modify the 312-name universe.
- Does NOT flag names that fail ≥ 2 gates. Structure trumps story.
- Does NOT accept flags where the required citation is post the analyst
  agent's training cutoff — flag must reference a filing the MacBook can
  actually pull from EDGAR and quote.
- Does NOT recommend action. Every flag defaults to `status: pending_amrit`.
- Does NOT run more often than quarterly. This is a discovery layer, not
  an alert layer.

## 3. Grouping and tags

Multi-grouping via tag rollups. Same passer can appear under several
group headers in the digest.

| Tag type | Source | Example |
|---|---|---|
| Automatic | Yahoo Finance / SEC filings | `sector:tech`, `industry:semis`, `size:mega`, `country:us` |
| Manual (thematic) | `config/tag_overrides.yaml` | `theme:ai-infra`, `theme:defense`, `role:core`, `role:speculative` |

Digest rollup config lives in `config/digest_layout.yaml`:

```yaml
discovery_rollups:
  - by: sector          # official GICS
  - by: theme           # manual thematic tags
  - by: size            # mega/large/mid
  - name: "AI infra intersect"
    intersect: [sector:tech, theme:ai-infra]
```

Same 4 new passers, up to 4 different lenses in the digest. Zero additional
compute — just presentation.

## 4. The six-gate reuse contract

Discovery analyst MUST import gate logic from the frozen module, not
reimplement it. The frozen module needs to expose:

```python
# expected shape in quality_value_screener.py (or a peer module)
def run_six_gates(fundamentals: Fundamentals) -> GateResult:
    """Returns pass/fail per gate + the values used."""

@dataclass
class GateResult:
    passed: bool                              # all six pass
    detail: dict[str, tuple[bool, float]]     # {"roic": (True, 0.314), ...}
```

**If this interface doesn't exist yet**, the MacBook agent's first task
is to check `quality_value_screener.py` and either:
- Confirm the entry point exists under a different name (grep first), or
- Add a thin wrapper (a bug-fix-scope refactor per §1 freeze — a new
  wrapper that calls into the existing logic without changing thresholds
  is not a methodology change; changing any threshold or gate formula
  would be)

Do not reimplement the gates from scratch. Divergence between the two
implementations is worse than no discovery layer at all.

## 5. Flag emission — the anatomy of an analyst_flag

Every flag has exactly these five fields. No flag ships without all five:

```python
@dataclass
class AnalystFlag:
    ticker: str
    failed_gate: str                # one of the 6 gate names
    failure_value: str              # exact number, exact threshold
                                    # e.g. "FCF yield 4.1% vs 4.5% threshold"
    citation: str                   # filing + section + page
                                    # e.g. "AAPL 10-K FY2025, p.23, cash flow statement"
    rationale: str                  # <= 300 chars, cites the citation
                                    # e.g. "ATH sitting on $180B cash; ex-cash yield is 5.8%.
                                    #       See balance sheet line 3."
    status: str                     # "pending_amrit" at creation
                                    # -> "accepted" | "rejected" | "deferred"
    raised_ts: int
    resolved_ts: Optional[int]
    outcome_12mo: Optional[str]     # populated on the 1-year anniversary
                                    # for the quarterly audit
```

## 6. The quarterly audit (mandatory)

Once per quarter, the discovery analyst emits an audit section:

```
## DISCOVERY ANALYST — QUARTERLY AUDIT (Q3 2026)
  Flags raised in Q3 2025 (12mo lookback):     4
    Accepted (Amrit added to tracking):        1 (XYZ)  → 12mo return: +18%
    Rejected:                                  2 (ABC -12%, DEF +4%)
    Deferred / still pending:                  1 (GHI +6%)

  Aggregate flag performance vs pure gate-pass benchmark:
    Flagged names (n=4):     +4.0% avg
    Six-gate passers (n=42): +11.3% avg
    -> Flags UNDERPERFORMED. If this holds through Q4 2026, flag
       authority revoked per pre-registered rule.
```

The pre-registered rule: if the trailing 4-quarter aggregate of flag
outcomes is worse than pure gate-passers, discovery's flag emission is
disabled and it goes back to pass/fail only.

## 7. Journal schema additions

Append these event kinds to `journal.jsonl`:

```json
{"ts": 1755740760, "kind": "analyst_flag_raised", "ticker": "XYZ",
 "gate": "fcf_yield", "value": "4.1%", "threshold": "4.5%",
 "citation": "10-K FY2025 p.23", "rationale": "...", "flag_id": "flg_abc123"}

{"ts": 1755740900, "kind": "analyst_flag_response", "flag_id": "flg_abc123",
 "response": "accepted", "notes": "adding to tracking as of today"}

{"ts": 1786276800, "kind": "analyst_flag_outcome_12mo", "flag_id": "flg_abc123",
 "response_recorded": "accepted", "return_12mo": 0.184,
 "benchmark_return_12mo": 0.113, "outperformed": true}
```

## 8. Verification protocol — before discovery merges to main

1. Discovery analyst runs against a fixed test universe (10 well-known
   large caps) with mocked fundamentals — outputs are deterministic and
   match a golden file.
2. The six-gate reuse contract test: assert the discovery analyst's
   pass/fail on a given ticker matches what the frozen screener would say
   on the same fundamentals. Any divergence = broken reuse contract.
3. Flag-emission cap test: force 5 near-passers, assert exactly 2 flags
   emerge (the top 2 by rationale strength).
4. Freeze compliance: `git diff main -- quality_value_screener.py alpha_screener.py`
   must be empty at merge time. If a bug-fix wrapper was added there,
   verify it's genuinely a wrapper (no threshold or formula change).
5. Journal round-trip: raise a fake flag, respond "accepted", verify both
   entries land correctly and can be reconstructed a year later for the
   outcome_12mo record.

Only after all five pass does the quarterly cron enable.

## 9. Definition of done for Phase 1.5

- [ ] `analysts/discovery.py` written and passes §8 verification
- [ ] Reuse contract with `quality_value_screener.py` established
- [ ] `config/tag_overrides.yaml` populated with at least 5 thematic tags
      per master watchlist entry (Amrit fills in initially, discovery
      auto-tags new names)
- [ ] `config/digest_layout.yaml` populated with initial rollups
- [ ] Quarterly cron added to the workflow (`0 12 1 */3 *` — first day of
      each quarter, 07:00 Toronto)
- [ ] Journal audit report renders correctly for one synthetic quarter
- [ ] First live quarterly run produces a digest section that reads
      sensibly, with flag count ≤ 2

Then Phase 2 or the next in queue.
