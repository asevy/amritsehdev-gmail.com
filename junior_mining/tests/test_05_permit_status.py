"""Brief §17 case 5: application status does not become permit issuance."""

from helpers import passage_candidate, vctx, version_of
from jmi import answers, memo as M
from jmi.validate import validate


def test_application_and_acceptance_are_distinct_states(ws):
    rows = [f for f in ws.facts(company_id=ws.HPG) if f["metric_id"] == "permit_status"]
    by = {f["normalized_value"]: f for f in rows}
    assert set(by) == {"applied", "accepted_for_review"}
    assert by["applied"]["as_of_date"] == "2026-03-03" and by["accepted_for_review"]["as_of_date"] == "2026-05-20"
    assert "issued" not in by


def test_forward_looking_permit_sentence_is_a_commitment_not_a_status(ws):
    c = [x for x in ws.store.find(ws.A, "commitments", company_id=ws.HPG) if "permit" in x["subject"]]
    assert c and c[0]["target_text"] == "in H2 2027" and c[0]["attribution"] == "issuer_management"
    assert c[0]["target_window_end"] == "2027-12-31"


def test_has_not_submitted_is_not_applied(ws):
    f = ws.fact(metric_id="permit_status", company_id=ws.OBR)
    assert f["normalized_value"] == "not_applied"


def test_model_claiming_issued_from_application_text_is_rejected(ws):
    v = version_of(ws, "HPG_PEA_Technical_Report_Summary_2026.pdf")
    c = passage_candidate(ws, v, 2, r"submitted its environmental impact statement", "permit_status",
                          "submitted its environmental impact statement", claimed_value="issued", value_kind="enum",
                          fields={"as_of_date": "2026-03-03"}, qualifiers={"permit": "environmental approval (EIS)"})
    r = validate(c, vctx(ws, v))
    assert r.state == "rejected"
    assert any("not an issued permit" in x["detail"] for x in r.checks)


def test_issued_record_of_decision_is_issued(ws):
    f = ws.fact(metric_id="permit_status", company_id=ws.TVG)
    assert f["normalized_value"] == "issued"


def test_answer_reports_status_words_exactly(approved):
    a = answers.ask(approved.store, approved.A, approved.HPG, "What is the permitting status?")
    assert a["status"] == "answered"
    joined = " ".join(x["statement"] for x in a["answer"])
    assert "Application accepted for review" in joined and "issued" not in joined.lower()


def test_memo_claim_fully_permitted_is_unsupported(approved):
    f = approved.fact(metric_id="permit_status", normalized_value="accepted_for_review")
    r = M.validate_claim(approved.store, approved.A, {"kind": "factual", "fact_ids": [f["id"]], "calc_ids": [],
                                                      "text": "The company reports the project is fully permitted.",
                                                      "risk_ids": [], "review": {}})
    assert r["status"] == "unsupported"
