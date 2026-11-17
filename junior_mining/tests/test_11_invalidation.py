"""Brief §17 case 11: source corrections identify and invalidate dependent
current outputs; approved memos are flagged, never rewritten."""

from jmi import calc, facts, memo as M, peers


def _approved_memo(ws):
    th = M.create_thesis(ws.store, ws.A, ws.HPG, "t", "Thesis.", "Counter-thesis.",
                         assumptions=[{"text": "cash covers a year of spending", "metric_ids": ["cash_unrestricted"]}])
    m = M.create_memo(ws.store, ws.A, ws.HPG, "Memo (SYNTHETIC)", thesis_id=th["thesis"]["id"])
    vid = m["version"]["id"]
    M.submit(ws.store, ws.A, vid)
    M.review_supported_claims(ws.store, ws.R, vid, "checked")
    M.approve(ws.store, ws.R, vid, "pilot approval")
    return m["memo"]["id"], vid


def test_correction_marks_dependents_stale_and_keeps_approved_memo_intact(approved):
    ws = approved
    mid, vid = _approved_memo(ws)
    before = ws.store.get(ws.A, "memo_versions", vid)
    cash = ws.fact(metric_id="cash_unrestricted", company_id=ws.HPG)
    ev = next(c for c in ws.store.find(ws.A, "calculations", company_id=ws.HPG, formula_id="enterprise_value")
              if c["status"] == "computed")
    new = facts.correct_fact(ws.store, ws.A, cash["id"], "issuer filed an amended MD&A (test)", raw_value="17.4")
    after = ws.store.get(ws.A, "memo_versions", vid)
    assert after["status"] == "approved" and after["stale"] == 1 and cash["id"] in after["stale_reason"]
    assert after["body"] == before["body"] and after["content_sha256"] == before["content_sha256"]
    assert ws.store.get(ws.A, "calculations", ev["id"])["stale"] == 1
    events = [e for e in ws.store.find(ws.A, "events", kind="outputs_invalidated")]
    assert events and any(l["target_id"] == vid for l in __import__("jmi.events", fromlist=["x"]).links_of(
        ws.store, ws.A, events[0]["id"]))
    assert new["workflow_state"] == "needs_review"


def test_stale_approved_memo_renders_as_approved_with_change_notes(approved):
    ws = approved
    mid, vid = _approved_memo(ws)
    before = M.render(ws.store, ws.A, vid)
    ws.upload_key("hpg_update")
    after = M.render(ws.store, ws.A, vid)
    ids = lambda r: [it["id"] for s in r["sections"] for it in s["items"]]
    assert ids(after) == ids(before)                     # nothing withheld from a historical approved record
    assert after["withheld_claims"] == []
    assert "STALE" in after["status_label"] and after["status_label"].startswith("APPROVED")
    assert any(u.startswith("Since approval, claim") for u in after["unresolved"])


def test_rejecting_an_approved_fact_invalidates_downstream(approved):
    ws = approved
    r = calc.market_cap(ws.store, ws.A, ws.HPG)
    cid = calc.save(ws.store, ws.A, r, ws.HPG)
    shares = ws.fact(metric_id="shares_outstanding_basic", company_id=ws.HPG)
    facts.review(ws.store, ws.R2, shares["id"], "reject", "wrong share class (test)")
    assert ws.store.get(ws.A, "calculations", cid)["stale"] == 1


def test_restatement_marks_snapshot_and_thesis_assumption(approved):
    ws = approved
    ps = peers.create_peer_set(ws.store, ws.A, ws.HPG, ws.HPP, "p")
    for m in ws.store.find(ws.A, "peer_members", peer_set_id=ps["id"]):
        peers.decide(ws.store, ws.A, m["id"], "approved", "test")
    peers.approve_set(ws.store, ws.A, ps["id"], "test")
    snap = peers.build_snapshot(ws.store, ws.A, ps["id"], "2026-11-13")
    M.create_thesis(ws.store, ws.A, ws.HPG, "t", "T.", "C.", assumptions=[
        {"text": "M&I scale", "metric_ids": ["resource_contained_metal"], "project_id": ws.HPP}])
    ws.upload_key("hpg_update")
    assert ws.store.get(ws.A, "comparison_snapshots", snap["id"])["stale"] == 1
    a = ws.store.find(ws.A, "thesis_assumptions", company_id=ws.HPG)[0]
    assert a["status"] == "affected_by_change"


def test_commitment_revision_is_linked_to_thesis(approved):
    ws = approved
    c = next(x for x in ws.store.find(ws.A, "commitments", company_id=ws.HPG) if "feasibility" in x["subject"])
    M.create_thesis(ws.store, ws.A, ws.HPG, "t", "T.", "C.", assumptions=[
        {"text": "PFS by Q2 2027", "commitment_ids": [c["id"]]}])
    ws.upload_key("hpg_update")
    assert ws.store.get(ws.A, "commitments", c["id"])["status"] == "revised"
    upd = ws.store.find(ws.A, "commitment_updates", commitment_id=c["id"])
    assert upd and upd[0]["kind"] == "explicit_revision" and upd[0]["new_target_text"] == "in Q4 2027"
    a = ws.store.find(ws.A, "thesis_assumptions", company_id=ws.HPG)[0]
    assert a["status"] == "affected_by_change" and "explicitly revised" in a["status_reason"]
