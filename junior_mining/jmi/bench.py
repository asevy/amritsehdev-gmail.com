"""Benchmark tooling (brief §17): run a labelled question set and report
measures SEPARATELY, each with its denominator, exclusions and a 95% Wilson
interval. No single combined number is produced.

Labels carry their provenance. Unless every label in a run comes from
qualified, adjudicated expert review, the report says production validation
is pending. Zero errors in a sample is reported as an interval, never as
"error-free".

    python -m jmi.bench QUESTIONS.jsonl            # against a fresh SYNTHETIC workspace
"""

from __future__ import annotations

import json
import math
import statistics
import sys
import tempfile
import time
from decimal import Decimal
from pathlib import Path


def wilson(k: int, n: int, z: float = 1.96) -> tuple | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - r) / d, 3), round((c + r) / d, 3))


def _measure(k, n, excluded=0, note=""):
    return {"correct": k, "denominator": n, "excluded": excluded, "proportion": round(k / n, 3) if n else None,
            "wilson_95": wilson(k, n), "note": note}


def run(store, actor, company_ids: dict, questions: list[dict]) -> dict:
    from . import answers
    rows = []
    for q in questions:
        cid = company_ids.get(q["company_key"])
        t0 = time.perf_counter()
        a = answers.ask(store, actor, cid, q["question"]) if cid else {"status": "error"}
        ms = (time.perf_counter() - t0) * 1000
        exp = q["expected"]
        status_ok = a["status"] == exp["status"]
        value_ok = None
        if exp.get("value") is not None and a["status"] == "answered":
            got = [store.get(actor, "facts", x["fact_id"]) for x in a["answer"]]
            value_ok = any(f["normalized_value"] is not None and Decimal(f["normalized_value"]) == Decimal(exp["value"])
                           and (not exp.get("date") or exp["date"] in (f["as_of_date"], f["effective_date"]))
                           and (not exp.get("unit") or exp["unit"] in (f["unit"], f["currency"]))
                           for f in got)
        rows.append({"id": q["id"], "stratum": q.get("stratum", {}), "expected": exp["status"], "got": a["status"],
                     "status_ok": status_ok, "value_ok": value_ok, "latency_ms": round(ms, 2),
                     "label_source": q.get("label_source", "unknown"), "held_out": q.get("held_out", False)})
    answerable = [r for r in rows if r["expected"] == "answered"]
    abstain = [r for r in rows if r["expected"] in ("not_found", "declined")]
    valued = [r for r in rows if r["value_ok"] is not None]
    lat = [r["latency_ms"] for r in rows]
    expert = all(r["label_source"].startswith("expert:") for r in rows) and rows
    report = {
        "questions": len(rows),
        "label_provenance": sorted({r["label_source"] for r in rows}),
        "production_validation": "available" if expert else
            "PENDING — labels are not qualified, adjudicated expert labels; these results test the tooling and "
            "the synthetic fixtures only",
        "measures": {
            "value_and_context_accuracy": _measure(sum(1 for r in valued if r["value_ok"]), len(valued),
                                                   note="answered questions with a labelled value, date and unit"),
            "answerable_coverage": _measure(sum(1 for r in answerable if r["got"] == "answered"), len(answerable),
                                            note="labelled answerable questions answered from approved facts"),
            "appropriate_abstention": _measure(sum(1 for r in abstain if r["status_ok"]), len(abstain),
                                               note="questions labelled not-found or out-of-policy"),
            "false_answer_on_unanswerable": _measure(sum(1 for r in abstain if r["got"] == "answered"), len(abstain),
                                                     note="lower is better; an answer where none was labelled"),
        },
        "latency_ms": {"n": len(lat), "p50": round(statistics.median(lat), 2) if lat else None,
                       "p95": round(sorted(lat)[max(0, int(len(lat) * 0.95) - 1)], 2) if lat else None},
        "cost": {"model_calls": 0, "note": "deterministic extraction and answering; no model provider configured"},
        "not_measured_here": ["complete-claim support (see tests/test_02_claim_support.py; needs expert labels)",
                              "material fact/risk recall (needs expert-labelled documents)",
                              "freshness against live sources (no live feeds)",
                              "reviewer effort (needs timed pilot sessions)"],
        "strata": {},
        "rows": rows,
        "caveat": "A sample with zero observed errors does not show zero future errors; see the interval.",
    }
    for r in rows:
        for k, v in r["stratum"].items():
            s = report["strata"].setdefault(f"{k}={v}", {"n": 0, "status_ok": 0})
            s["n"] += 1
            s["status_ok"] += int(r["status_ok"])
    return report


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    qpath = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent / "benchmark" / "dev_synthetic_questions.jsonl"
    questions = [json.loads(l) for l in qpath.read_text().splitlines() if l.strip()]
    from datetime import datetime
    from . import auth as AU, config, db, facts, seed, store as ST
    config.set_clock(datetime(2026, 11, 17, 15, 0))
    tmp = Path(tempfile.mkdtemp(prefix="jmi-bench-"))
    d = db.Database(tmp / "jmi.sqlite3")
    st = ST.Store(d, tmp)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    ids = seed.seed(st, AU.Auth(d), tmp / "fx", upload_keys=[
        "hpg_pea", "hpg_mda", "hpg_drill", "hpg_drill_mirror", "hpg_xlsx", "hpg_deck", "market", "tvg", "obr", "qrc",
        "bwm", "broken"])
    R = seed.actor(st, "reviewer.a")
    for f in st.find(R, "facts"):
        if f["workflow_state"] == "source_matched":
            facts.review(st, R, f["id"], "approve", "benchmark setup")
    disc = st.find(R, "discrepancies", kind="value_conflict")
    if disc:
        keep = next(f for f in st.find(R, "facts", metric_id="npv") if f["raw_value"] == "412")
        facts.resolve_discrepancy(st, R, disc[0]["id"], "primary disclosure kept (benchmark setup)", keep["id"])
    report = run(st, seed.actor(st, "analyst.a"), ids["alpha"], questions)
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
