"""Brief §17 case 1: the correct number with the wrong entity, period,
currency, scale or scope is rejected or flagged."""

from helpers import passage_candidate, vctx, version_of
from jmi.validate import validate

CASH = r"cash and cash equivalents of C\$18\.4 million"


def _cash(ws, **claims):
    v = version_of(ws, "HPG_Q3_2026_MDA.pdf")
    base = dict(fields={"as_of_date": "2026-09-30"}, qualifiers={"currency_token": "C$", "scale_word": "million"},
                claimed_value="18400000")
    for k, val in claims.items():
        if isinstance(val, dict) and k in base:
            base[k] = {**base[k], **val}
        else:
            base[k] = val
    return validate(passage_candidate(ws, v, 1, CASH, "cash_unrestricted", "18.4", **base), vctx(ws, v))


def test_correct_claim_is_source_matched(ws):
    r = _cash(ws)
    assert r.state == "source_matched", r.checks
    assert r.normalized_value == "18400000" and r.currency == "CAD"


def test_wrong_period_is_rejected(ws):
    r = _cash(ws, fields={"as_of_date": "2025-12-31"})
    assert r.state == "rejected"
    assert any(c["check"] == "period" and c["status"] == "fail" for c in r.checks)


def test_wrong_currency_is_rejected(ws):
    r = _cash(ws, claimed_currency="USD", qualifiers={"currency_token": "US$"})
    assert r.state == "rejected"
    assert any(c["check"] == "currency" and c["status"] == "fail" for c in r.checks)


def test_wrong_scale_is_rejected(ws):
    r = _cash(ws, qualifiers={"scale_word": "billion"}, claimed_value="18400000000")
    assert r.state == "rejected"
    assert any(c["check"] == "scale" and c["status"] == "fail" for c in r.checks)


def test_right_scale_word_wrong_value_is_rejected(ws):
    r = _cash(ws, claimed_value="18400")          # thousands instead of millions
    assert r.state == "rejected"
    assert any(c["check"] == "value" and c["status"] == "fail" for c in r.checks)


def test_wrong_scope_basis_is_rejected(ws):
    v = version_of(ws, "HPG_PEA_Technical_Report_Summary_2026.pdf")
    c = passage_candidate(ws, v, 1, r"after-tax NPV \(5%\) of US\$412 million", "npv", "412",
                          fields={"effective_date": "2026-06-01", "study_type": "pea", "tax_basis": "after_tax",
                                  "discount_rate": "5", "scope_basis": "attributable"},
                          qualifiers={"currency_token": "US$", "scale_word": "million"})
    r = validate(c, vctx(ws, v))
    assert r.state == "rejected"
    assert any(x["check"] == "scope" and x["status"] == "fail" for x in r.checks)


def test_missing_basis_is_flagged_not_assumed(ws):
    v = version_of(ws, "HPG_Investor_Presentation_2026-09.pdf")
    deck = [f for f in ws.facts(version_id=v["id"]) if f["metric_id"] == "resource_contained_metal"][0]
    assert deck["workflow_state"] == "needs_review"
    assert "basis not stated" in deck["missing_reason"] and "effective date not stated" in deck["missing_reason"]


def test_wrong_entity_similar_project_name_is_rejected(ws):
    """The MD&A mentions the neighbouring 'Halvard West Project' (another company)."""
    v = version_of(ws, "HPG_Q3_2026_MDA.pdf")
    rows = [f for f in ws.facts(version_id=v["id"]) if f["metric_id"] == "historical_estimate_contained_metal"]
    assert rows and all(f["workflow_state"] == "rejected" for f in rows)
    assert any("Halvard West Project" in c["detail"] for c in rows[0]["checks"] if c["check"] == "entity")


def test_model_assigning_another_companys_project_is_rejected(ws):
    v = version_of(ws, "HPG_Q3_2026_MDA.pdf")
    c = passage_candidate(ws, v, 2, r"historical\s+estimate of 1\.1 Moz", "historical_estimate_contained_metal", "1.1",
                          qualifiers={"unit_token": "Moz"}, project_mention="Halvard Peak Project")
    r = validate(c, vctx(ws, v))
    assert r.state == "rejected"


def test_as_of_versus_expiry_date_ambiguity_is_flagged(ws):
    v = version_of(ws, "HPG_Q3_2026_MDA.pdf")
    c = passage_candidate(ws, v, 1, r"38,000,000 share purchase warrants", "warrants_outstanding", "38,000,000",
                          fields={"as_of_date": "2027-06-30"})     # the expiry, not the as-at date
    r = validate(c, vctx(ws, v))
    assert r.state in ("needs_review", "rejected")
