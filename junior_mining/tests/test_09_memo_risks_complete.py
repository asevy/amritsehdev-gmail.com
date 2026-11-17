"""Brief §17 case 9: disclosed risks and contrary evidence are not omitted
from the approved memo."""

import pytest

from jmi import ingest, memo as M, risks
from jmi.store import Invalid


def _ready_memo(ws, thesis=True):
    th = M.create_thesis(ws.store, ws.A, ws.HPG, "t", "Thesis text.", "Counter-thesis text.") if thesis else None
    m = M.create_memo(ws.store, ws.A, ws.HPG, "Memo (SYNTHETIC)", thesis_id=th["thesis"]["id"] if th else None)
    return m["version"]["id"]


def test_rule_based_risks_are_in_the_draft(approved):
    vid = _ready_memo(approved)
    body = approved.store.get(approved.A, "memo_versions", vid)["body"]
    titles = [c["text"] for c in body["sections"]["risks"]]
    assert any("going concern" in t for t in titles)
    assert any("not issued" in t for t in titles)


def test_risk_items_cannot_be_removed(approved):
    vid = _ready_memo(approved)
    body = approved.store.get(approved.A, "memo_versions", vid)["body"]
    rid = body["sections"]["risks"][0]["id"]
    with pytest.raises(Invalid):
        M.remove_claim(approved.store, approved.A, vid, rid, "too negative")


def test_new_register_risk_blocks_approval_until_included(approved):
    vid = _ready_memo(approved)
    M.submit(approved.store, approved.A, vid)
    M.review_supported_claims(approved.store, approved.R, vid, "checked")
    assert M.approval_blockers(approved.store, approved.R, vid) == []
    r = risks.create(approved.store, approved.A, approved.HPG, "land_community", "Community agreement not disclosed")
    bl = M.approval_blockers(approved.store, approved.R, vid)
    assert any("Community agreement not disclosed" in b for b in bl)
    with pytest.raises(Invalid):
        M.approve(approved.store, approved.R, vid, "ok")
    del r


def test_contrary_evidence_is_rendered(approved):
    st, a = approved.store, approved.A
    deck = next(v for v in st.find(a, "document_versions") if v["filename"].startswith("HPG_Investor"))
    loc = ingest.cite(st, a, deck["id"], 1, "Fully funded through completion of the pre-feasibility study.")
    gc = next(r for r in st.find(a, "risk_findings", company_id=approved.HPG) if r["origin"] == "rule:going_concern")
    risks.add_evidence(st, a, gc["id"], "contrary", location_id=loc["id"],
                       note="issuer presentation claims full funding to PFS (promotional; unverified)")
    vid = _ready_memo(approved)
    r = M.render(st, a, vid)
    item = next(it for s in r["sections"] if s["key"] == "risks" for it in s["items"] if it.get("risk") and
                "going concern" in it["text"])
    assert item["risk"]["contrary"] and "Fully funded" in item["risk"]["contrary"][0]["quote"]


def test_counter_thesis_is_required(approved):
    with pytest.raises(Invalid):
        M.create_thesis(approved.store, approved.A, approved.HPG, "t", "Thesis only.", "")
    vid = _ready_memo(approved, thesis=False)
    M.submit(approved.store, approved.A, vid)
    M.review_supported_claims(approved.store, approved.R, vid, "checked")
    assert any("counter-thesis" in b for b in M.approval_blockers(approved.store, approved.R, vid))
