"""Brief §17 case 8: peer mismatch and incompatible definitions are exposed;
unsupported comparisons are withheld; no overall winner."""

import pytest

from jmi import peers
from jmi.store import Invalid


def _approved_set(ws, exclude_copper=True):
    ps = peers.create_peer_set(ws.store, ws.A, ws.HPG, ws.HPP, "Gold peers (test)")
    for m in ws.store.find(ws.A, "peer_members", peer_set_id=ps["id"]):
        if m["company_id"] == ws.QRC and exclude_copper:
            peers.decide(ws.store, ws.A, m["id"], "excluded", "copper porphyry; different commodity")
        else:
            peers.decide(ws.store, ws.A, m["id"], "approved", "gold; differences recorded")
    peers.approve_set(ws.store, ws.A, ps["id"], "test")
    return ps


def test_candidates_explain_inclusion_and_label_broader_comparators(approved):
    c = {x["company"]: x for x in peers.generate_candidates(approved.store, approved.A, approved.HPG, approved.HPP)}
    assert c["Quillon Ridge Copper Corp."]["classification"] == "broader_comparator"
    assert any("different commodity" in d for d in c["Quillon Ridge Copper Corp."]["differences"])
    assert c["Orrin Basin Resources Ltd."]["classification"] == "strict_peer"
    assert any("70%" in d for d in c["Orrin Basin Resources Ltd."]["differences"])
    assert all(x["inclusion_reasons"] for x in c.values())


def test_decision_requires_rationale_and_set_requires_decisions(approved):
    ps = peers.create_peer_set(approved.store, approved.A, approved.HPG, approved.HPP, "x")
    m = approved.store.find(approved.A, "peer_members", peer_set_id=ps["id"])[0]
    with pytest.raises(Invalid):
        peers.decide(approved.store, approved.A, m["id"], "approved", "  ")
    with pytest.raises(Invalid):
        peers.approve_set(approved.store, approved.A, ps["id"], "premature")
    with pytest.raises(Invalid):
        peers.build_snapshot(approved.store, approved.A, ps["id"], "2026-11-13")


def test_snapshot_exposes_incompatibilities(approved):
    snap = peers.build_snapshot(approved.store, approved.A, _approved_set(approved)["id"], "2026-11-13")
    comp = snap["body"]["comparability"]
    assert any("study types differ" in n for n in comp["npv_after_tax"])
    assert any("Gold-price assumptions differ" in n and "not re-priced" in n for n in comp["npv_after_tax"])
    assert any("reporting bases differ" in n for n in comp["ev_per_mi_oz_100"])
    assert any("not company equity value" in n.lower() for n in comp["attributable_npv"])


def test_unsupported_comparisons_are_withheld_with_reason(approved):
    snap = peers.build_snapshot(approved.store, approved.A, _approved_set(approved)["id"], "2026-11-13")
    bwm = next(r for r in snap["body"]["rows"] if r["company"].startswith("Brightwater"))
    assert bwm["cells"]["enterprise_value"]["status"] == "withheld"
    assert "total debt" in bwm["cells"]["enterprise_value"]["reason"]
    hpg = next(r for r in snap["body"]["rows"] if r["role"] == "subject")
    assert hpg["cells"]["ev_per_pp_oz_100"]["status"] == "withheld"


def test_price_must_be_on_the_market_data_date(approved):
    snap = peers.build_snapshot(approved.store, approved.A, _approved_set(approved)["id"], "2026-11-14")
    assert all(r["cells"]["market_cap"]["status"] == "withheld" for r in snap["body"]["rows"])
    assert "market-data date" in snap["body"]["rows"][0]["cells"]["market_cap"]["reason"]


def test_no_overall_winner_and_alphabetical_default(approved):
    snap = peers.build_snapshot(approved.store, approved.A, _approved_set(approved)["id"], "2026-11-13")
    rows = snap["body"]["rows"]
    assert rows[0]["role"] == "subject"
    names = [r["company"] for r in rows[1:]]
    assert names == sorted(names)
    text = " ".join(snap["body"]["observations"]).lower()
    for word in ("winner", "best", "better investment", "cheapest", "top pick", "recommend"):
        assert word not in text
    assert all(("Under these inputs" in o and "remain unresolved" in o) or "not compared" in o
               for o in snap["body"]["observations"])
    sorted_rows, note = peers.sort_rows(rows, "ev_per_mi_oz_100")
    assert "does not establish an overall preference" in note


def test_excluded_peer_is_listed_with_rationale(approved):
    snap = peers.build_snapshot(approved.store, approved.A, _approved_set(approved)["id"], "2026-11-13")
    assert snap["body"]["excluded"] == [{"company": "Quillon Ridge Copper Corp.",
                                         "rationale": "copper porphyry; different commodity"}]
