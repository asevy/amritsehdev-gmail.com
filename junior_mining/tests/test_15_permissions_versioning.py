"""Brief §17 case 15: review/export permissions and approval versioning."""

import pytest

from jmi import audit, exports, facts, memo as M
from jmi.store import AccessDenied, Invalid


def _memo(ws):
    th = M.create_thesis(ws.store, ws.A, ws.HPG, "t", "Thesis.", "Counter-thesis.")
    return M.create_memo(ws.store, ws.A, ws.HPG, "Memo (SYNTHETIC)", thesis_id=th["thesis"]["id"])


def test_read_only_cannot_write_review_or_export(http):
    v = http.client("viewer.a")
    s, _ = v.post("company.create", {"name": "x"})
    assert s == 403
    f = http.fact(metric_id="cash_unrestricted", company_id=http.HPG)
    s, _ = v.post("fact.review", {"fact_id": f["id"], "decision": "reject", "reason": "x"})
    assert s == 403
    m = _memo(http)
    s, _, _ = v.get(f"/export/memo/{m['version']['id']}.pdf")
    assert s == 403
    s, _, _ = v.get(f"/company/{http.HPG}")
    assert s == 200


def test_analyst_cannot_approve_facts_or_memos(approved):
    f = approved.fact(metric_id="npv", raw_value="585")
    with pytest.raises(AccessDenied):
        facts.review(approved.store, approved.A, f["id"], "reject", "x")
    m = _memo(approved)
    M.submit(approved.store, approved.A, m["version"]["id"])
    with pytest.raises(AccessDenied):
        M.approve(approved.store, approved.A, m["version"]["id"], "self")


def test_separation_of_duties(approved):
    ocr = approved.fact(raw_value="2O1")
    new = facts.correct_fact(approved.store, approved.R, ocr["id"], "visual check", raw_value="201")
    with pytest.raises(AccessDenied):
        facts.review(approved.store, approved.R, new["id"], "approve", "own correction")
    facts.review(approved.store, approved.R2, new["id"], "approve", "second reviewer")
    m = M.create_memo(approved.store, approved.R, approved.HPG, "Reviewer-authored memo (SYNTHETIC)")
    with pytest.raises(AccessDenied):
        M.review_claim(approved.store, approved.R, m["version"]["id"], "c1", "approved")


def test_approved_version_is_immutable_and_new_versions_increment(approved):
    m = _memo(approved)
    vid = m["version"]["id"]
    M.submit(approved.store, approved.A, vid)
    M.review_supported_claims(approved.store, approved.R, vid, "checked")
    v = M.approve(approved.store, approved.R, vid, "pilot")
    assert v["status"] == "approved" and v["content_sha256"]
    with pytest.raises(Invalid):
        M.add_claim(approved.store, approved.A, vid, "summary", "interpretive", "Edit after approval.")
    v2 = M.new_version(approved.store, approved.A, m["memo"]["id"], refresh=False)
    assert v2["version_no"] == 2 and v2["status"] == "draft"
    assert all(c["review"]["status"] == "pending" for s in v2["body"]["sections"].values() for c in s)
    M.submit(approved.store, approved.A, v2["id"])
    M.review_supported_claims(approved.store, approved.R, v2["id"], "checked")
    M.approve(approved.store, approved.R, v2["id"], "second approval")
    assert approved.store.get(approved.A, "memo_versions", vid)["status"] == "superseded"
    assert approved.store.get(approved.A, "memo_versions", vid)["content_sha256"] == v["content_sha256"]


def test_csrf_required_for_writes(http):
    a = http.client("analyst.a")
    s, body = a.post("company.create", {"name": "No token Co."}, csrf="")
    assert s == 400 and body["error"] == "bad_csrf"
    s, body = a.post("company.create", {"name": "Forged token Co."}, csrf="0" * 32)
    assert s == 400


def test_export_is_recorded_with_version_and_hash_and_draft_marked(approved):
    m = _memo(approved)
    data, ctype, rec = exports.memo_export(approved.store, approved.A, m["version"]["id"], "json")
    import hashlib
    import json
    assert rec["sha256"] == hashlib.sha256(data).hexdigest() and rec["target_version"] == m["version"]["id"]
    body = json.loads(data)
    assert body["status_label"].startswith("DRAFT") and body["unresolved"]
    tail = audit.tail(approved.db, "alpha", 20)
    assert any(e["action"] == "export" and rec["sha256"] in e["detail"] for e in tail)
    pdf, _, _ = exports.memo_export(approved.store, approved.A, m["version"]["id"], "pdf")
    assert pdf.startswith(b"%PDF")
    with pytest.raises(AccessDenied):
        exports.memo_export(approved.store, approved.V, m["version"]["id"], "csv")


def test_admin_reads_audit_but_cannot_review(http):
    adm = http.client("admin.a")
    s, body, _ = adm.get("/admin/audit")
    assert s == 200 and b"Chain verifies" in body
    f = http.fact(metric_id="npv", raw_value="585")
    s, _ = adm.post("fact.review", {"fact_id": f["id"], "decision": "reject", "reason": "x"})
    assert s == 403
    an = http.client("analyst.a")
    s, _, _ = an.get("/admin/audit")
    assert s == 403


def test_lockout_after_repeated_failures(http):
    from http_client import Client
    c = Client(http.base)
    for _ in range(5):
        assert not c.login("viewer.a", "wrong-password-123")
    assert not c.login("viewer.a", "correct-horse-battery-staple")     # locked even with the right password


def test_audit_chain_detects_tampering(approved):
    assert audit.verify_chain(approved.db)["ok"]
    approved.db.execute("UPDATE audit SET detail='edited' WHERE seq=(SELECT MIN(seq)+3 FROM audit)")
    r = audit.verify_chain(approved.db)
    assert r["ok"] is False and r["broken_at_seq"]
