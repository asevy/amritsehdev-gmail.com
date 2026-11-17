"""Benchmark tooling: separate measures, denominators, intervals, and an
explicit 'validation pending' flag for non-expert labels."""

import json
from pathlib import Path

from jmi import answers, bench

QUESTIONS = Path(__file__).resolve().parent.parent / "benchmark" / "dev_synthetic_questions.jsonl"


def test_bench_reports_separate_measures_with_denominators(approved):
    qs = [json.loads(l) for l in QUESTIONS.read_text().splitlines() if l.strip()]
    rep = bench.run(approved.store, approved.A, approved.ids["alpha"], qs)
    assert rep["questions"] == len(qs)
    assert rep["production_validation"].startswith("PENDING")
    for name, m in rep["measures"].items():
        assert {"correct", "denominator", "excluded", "wilson_95"} <= set(m), name
    assert rep["measures"]["false_answer_on_unanswerable"]["correct"] == 0
    assert rep["measures"]["value_and_context_accuracy"]["correct"] == rep["measures"]["value_and_context_accuracy"]["denominator"]
    assert "overall" not in json.dumps(rep["measures"]).lower()


def test_unrestricted_cash_is_not_restricted_cash(approved):
    a = answers.ask(approved.store, approved.A, approved.HPG, "How much unrestricted cash does the company have?")
    assert a["metrics"] == ["Cash and cash equivalents (unrestricted)"]
    assert "18.4" in a["answer"][0]["statement"]


def test_wilson_interval_for_zero_errors_is_not_zero_width():
    lo, hi = bench.wilson(0, 9)
    assert lo == 0.0 and hi > 0.25
