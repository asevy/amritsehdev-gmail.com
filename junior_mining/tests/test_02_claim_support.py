"""Brief §17 case 2: a valid citation that does not support the full claim
cannot approve it."""

import pytest

from jmi import memo as M
from jmi.store import Invalid


def _memo(ws):
    m = M.create_memo(ws.store, ws.A, ws.HPG, "Test memo (SYNTHETIC)")
    return m["version"]["id"]


def _v(ws, text, fact_ids=(), calc_ids=()):
    return M.validate_claim(ws.store, ws.A, {"kind": "factual", "text": text, "fact_ids": list(fact_ids),
                                             "calc_ids": list(calc_ids), "risk_ids": [], "review": {}})


def test_supported_claim_passes(approved):
    f = approved.fact(metric_id="cash_unrestricted", company_id=approved.HPG)
    r = _v(approved, "The company reports unrestricted cash of C$18.4 million as at 2026-09-30.", [f["id"]])
    assert r["status"] == "supported", r


def test_correct_number_wrong_date_is_unsupported(approved):
    f = approved.fact(metric_id="cash_unrestricted", company_id=approved.HPG)
    r = _v(approved, "The company reports unrestricted cash of C$18.4 million as at 2026-12-31.", [f["id"]])
    assert r["status"] == "unsupported" and any("2026-12-31" in x for x in r["reasons"])


def test_permit_issued_claim_citing_application_is_unsupported(approved):
    f = approved.fact(metric_id="permit_status", normalized_value="accepted_for_review")
    r = _v(approved, "The company reports that its environmental permit has been issued.", [f["id"]])
    assert r["status"] == "unsupported" and any("issued" in x for x in r["reasons"])


def test_reserves_claim_citing_resource_is_unsupported(approved):
    f = approved.fact(metric_id="resource_contained_metal", company_id=approved.HPG, resource_category="measured_indicated",
                      raw_value="920")
    r = _v(approved, "The company reports reserves of 920 koz.", [f["id"]])
    assert r["status"] == "unsupported" and any("reserve" in x for x in r["reasons"])


def test_npv_claim_without_qualifiers_is_unsupported(approved):
    f = approved.fact(metric_id="npv", raw_value="412")
    r = _v(approved, "The PEA estimates an NPV of US$412 million.", [f["id"]])
    assert r["status"] == "unsupported"
    assert any("tax basis" in x for x in r["reasons"]) and any("discount rate" in x for x in r["reasons"])


def test_unattributed_issuer_statement_is_unsupported(approved):
    f = approved.fact(metric_id="cash_unrestricted", company_id=approved.HPG)
    r = _v(approved, "Unrestricted cash was C$18.4 million as at 2026-09-30.", [f["id"]])
    assert r["status"] == "unsupported" and any("attribute" in x for x in r["reasons"])


def test_number_not_in_cited_record_is_unsupported(approved):
    f = approved.fact(metric_id="cash_unrestricted", company_id=approved.HPG)
    r = _v(approved, "The company reports unrestricted cash of C$19.4 million as at 2026-09-30.", [f["id"]])
    assert r["status"] == "unsupported" and any("19.4" in x for x in r["reasons"])


def test_citation_to_unapproved_fact_is_unsupported(ws):
    f = ws.fact(metric_id="cash_unrestricted", company_id=ws.HPG)
    assert f["workflow_state"] == "source_matched"
    r = _v(ws, "The company reports unrestricted cash of C$18.4 million as at 2026-09-30.", [f["id"]])
    assert r["status"] == "unsupported" and any("not reviewer-approved" in x for x in r["reasons"])


def test_reviewer_cannot_approve_an_unsupported_claim(approved):
    vid = _memo(approved)
    f = approved.fact(metric_id="permit_status", normalized_value="accepted_for_review")
    c = M.add_claim(approved.store, approved.A, vid, "summary", "factual",
                    "The company reports that it has received its environmental permit.", fact_ids=[f["id"]])
    assert c["validation"]["status"] == "unsupported"
    with pytest.raises(Invalid):
        M.review_claim(approved.store, approved.R, vid, c["id"], "approved", "looks fine")
    rendered = M.render(approved.store, approved.A, vid)
    assert any(w["id"] == c["id"] for w in rendered["withheld_claims"])
    body_ids = [it["id"] for s in rendered["sections"] for it in s["items"]]
    assert c["id"] not in body_ids
