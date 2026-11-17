"""Brief §17 case 16: public schemas, UI, reports and exports contain no
investment scores or substitutes. Assertions are made on the raw payloads
(the Vision//Edge boundary-test discipline), not only on rendered pages."""

import json

from jmi import exports, memo as M, peers, policy
from jmi.definitions import METRICS


def test_scanner_detects_known_violations():
    bad = {"company": {"investment_score": 7}, "rating": "A", "note": "8.5/10", "c": "87% confidence",
           "stars": "★★★", "label": "Strong Buy"}
    found = policy.scan(bad)
    assert len(found) >= 5
    assert policy.scan_html('<div class="badge-green">x</div>')
    assert policy.scan({"resource_grade": "1.25 g/t", "quote": "analyst rating: buy"}) == []


def test_schema_has_no_score_fields():
    names = policy.schema_fields()
    assert names
    assert policy.scan({n.split(".")[1]: 1 for n in names}) == []
    assert policy.scan({k: v.as_dict() for k, v in METRICS.items()}) == []


def test_api_payloads_have_no_scores(http):
    c = http.client("analyst.a")
    ps = peers.create_peer_set(http.store, http.A, http.HPG, http.HPP, "p")
    for m in http.store.find(http.A, "peer_members", peer_set_id=ps["id"]):
        peers.decide(http.store, http.A, m["id"], "approved", "test")
    peers.approve_set(http.store, http.A, ps["id"], "test")
    snap = peers.build_snapshot(http.store, http.A, ps["id"], "2026-11-13")
    m = M.create_memo(http.store, http.A, http.HPG, "Memo (SYNTHETIC)", peer_set_id=ps["id"])
    paths = ["/api/companies", f"/api/company/{http.HPG}", f"/api/snapshot/{snap['id']}",
             f"/api/memo/{m['version']['id']}", "/api/inbox", "/api/definitions", f"/api/coverage/{http.HPG}",
             f"/api/ask?company={http.HPG}&q=What+is+the+after-tax+NPV"]
    for p in paths:
        s, body = c.get_json(p)
        assert s == 200, p
        assert policy.scan(body) == [], (p, policy.scan(body)[:3])


def test_pages_have_no_scores_badges_or_traffic_lights(http):
    c = http.client("analyst.a")
    pages = ["/", f"/company/{http.HPG}", "/review", "/discrepancies", f"/risks/{http.HPG}", f"/diligence/{http.HPG}",
             f"/peers/{http.HPG}", f"/calcs/{http.HPG}", f"/memos/{http.HPG}", "/inbox", "/portfolio", "/definitions",
             f"/ask/{http.HPG}?q=Should+we+buy"]
    for p in pages:
        s, body, _ = c.get(p)
        assert s == 200, p
        assert policy.scan_html(body.decode()) == [], (p, policy.scan_html(body.decode())[:3])


def test_exports_have_no_scores(approved):
    m = M.create_memo(approved.store, approved.A, approved.HPG, "Memo (SYNTHETIC)")
    data, _, _ = exports.memo_export(approved.store, approved.A, m["version"]["id"], "json")
    assert policy.scan(json.loads(data)) == []
    csv_data, _, _ = exports.memo_export(approved.store, approved.A, m["version"]["id"], "csv")
    for line in csv_data.decode().splitlines():
        assert policy.scan({"line": line.replace(",", " ")}) == [] or "quote" in line
    facts_csv, _ = exports.facts_csv(approved.store, approved.A, approved.HPG)
    header = facts_csv.decode().splitlines()[1].split(",")
    assert policy.scan({h: 1 for h in header}) == []


def test_refusals_for_score_questions(approved):
    from jmi import answers
    for q in ("Give Halvard Peak a score out of 10", "What is the investment rating?",
              "What is the probability of success?", "What is your price target?", "Is management honest?"):
        a = answers.ask(approved.store, approved.A, approved.HPG, q)
        assert a["status"] == "declined", q
