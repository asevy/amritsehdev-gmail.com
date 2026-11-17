"""Brief §17 case 14: a user cannot retrieve another tenant's documents through
direct URLs, search, exports, caches or background jobs."""

import pytest

from jmi import ingest, memo as M
from jmi.auth import system_actor
from jmi.store import NotFound


def _alpha_ids(ws):
    v = next(x for x in ws.store.find(ws.A, "document_versions") if x["filename"].startswith("HPG_PEA"))
    f = ws.fact(metric_id="cash_unrestricted", company_id=ws.HPG)
    m = M.create_memo(ws.store, ws.A, ws.HPG, "alpha memo (SYNTHETIC)")
    return v, f, m


def test_direct_urls_return_404_across_tenants(http):
    v, f, m = _alpha_ids(http)
    b = http.client("analyst.b")
    for path in (f"/doc/{v['id']}", f"/doc/{v['id']}/original", f"/doc/{v['id']}/page/1.png", f"/api/doc/{v['id']}",
                 f"/api/blob/{v['id']}", f"/fact/{f['id']}", f"/api/fact/{f['id']}", f"/company/{http.HPG}",
                 f"/api/company/{http.HPG}", f"/memo/{m['memo']['id']}", f"/api/memo/{m['version']['id']}",
                 f"/export/memo/{m['version']['id']}.pdf", f"/export/facts/{http.HPG}.csv",
                 f"/api/coverage/{http.HPG}", f"/api/ask?company={http.HPG}&q=cash"):
        s, body, _ = b.get(path)
        assert s == 404, (path, s)
        assert b"Halvard Peak Project" not in body and b"18.4" not in body


def test_same_name_company_in_other_tenant_is_separate(http):
    b = http.client("analyst.b")
    s, data = b.get_json(f"/api/company/{http.HPG_B}")
    assert s == 200
    assert data["company"]["tenant_id"] == "beta"
    assert all(x["tenant_id"] == "beta" for x in data["facts"])
    assert not any(x["raw_value"] == "18.4" for x in data["facts"])


def test_search_is_tenant_scoped(http):
    a, b = http.client("analyst.a"), http.client("analyst.b")
    s, ra = a.get_json("/api/search?q=intersected")
    assert s == 200 and ra["results"]
    s, rb = b.get_json("/api/search?q=intersected")
    assert s == 200 and rb["results"] == []
    s, rb2 = b.get_json("/api/search?q=placement")
    assert rb2["results"]
    s, ra2 = a.get_json("/api/search?q=placement")
    assert ra2["results"] == []


def test_actions_on_other_tenant_records_are_404(http):
    v, f, m = _alpha_ids(http)
    rb = http.client("reviewer.b")
    s, body = rb.post("fact.review", {"fact_id": f["id"], "decision": "approve", "reason": "x"})
    assert s == 404
    s, body = rb.post("cite", {"version_id": v["id"], "page_no": 1, "quote": "Halvard Peak Gold Corp."})
    assert s == 404
    assert http.store.get(http.A, "facts", f["id"])["workflow_state"] == "reviewer_approved"


def test_background_job_is_confined_to_its_tenant(ws):
    run = ws.store.find(ws.A, "ingestion_runs")[0]
    with pytest.raises(NotFound):
        ingest.process(ws.store, "beta", run["id"])
    with pytest.raises(NotFound):
        ingest.read_blob(ws.store, system_actor("beta", "ingest"), run["version_id"])


def test_blob_storage_and_cache_keys_are_per_tenant(http):
    v, _, _ = _alpha_ids(http)
    assert f"/blobs/alpha/" in "/" + v["storage_path"] + "/" or v["storage_path"].startswith("blobs/alpha/")
    a = http.client("analyst.a")
    s, _, _ = a.get(f"/doc/{v['id']}/page/1.png")
    assert s == 200
    b = http.client("analyst.b")
    s, _, _ = b.get(f"/doc/{v['id']}/page/1.png")         # cached for alpha; still refused for beta
    assert s == 404
