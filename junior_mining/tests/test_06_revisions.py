"""Brief §17 case 6: revised disclosures preserve original versions and affect
only the appropriate facts."""

import hashlib
from pathlib import Path

from jmi import ingest


def test_restatement_supersedes_only_restated_facts(approved):
    ws = approved
    before = {f["id"]: f for f in ws.facts(company_id=ws.HPG) if f["effective_date"] == "2026-04-30"
              and not f["qualifiers"].get("zone") and f["metric_id"].startswith("resource_")}
    ws.upload_key("hpg_update")
    after = {f["id"]: f for f in ws.facts(company_id=ws.HPG)}
    restated = {(f["metric_id"], f["resource_category"]) for f in after.values() if f["relation"] == "restatement"}
    assert restated == {("resource_tonnage", "indicated"), ("resource_contained_metal", "indicated"),
                        ("resource_tonnage", "measured_indicated"), ("resource_contained_metal", "measured_indicated")}
    for fid, f in before.items():
        now = after[fid]
        key = (f["metric_id"], f["resource_category"])
        if key in restated:
            assert now["workflow_state"] == "superseded"
            new = [x for x in after.values() if x["revision_of"] == fid]
            assert new and new[0]["relation"] == "restatement"
            assert now["raw_value"] == f["raw_value"] and now["raw_text"] == f["raw_text"]   # original preserved
        else:
            assert now["workflow_state"] == "reviewer_approved", (key, now["workflow_state"])  # grades, measured, inferred


def test_new_effective_date_does_not_supersede_older_estimate(approved):
    ws = approved
    ws.upload_key("hpg_update")
    nov = [f for f in ws.facts(company_id=ws.HPG) if f["effective_date"] == "2026-11-01"]
    assert nov and all(f["relation"] is None for f in nov)
    measured_apr = ws.fact(company_id=ws.HPG, metric_id="resource_contained_metal", resource_category="measured",
                           effective_date="2026-04-30")
    assert measured_apr["workflow_state"] == "reviewer_approved"


def test_original_bytes_and_versions_are_immutable(approved):
    ws = approved
    v = next(x for x in ws.store.find(ws.A, "document_versions") if x["filename"].startswith("HPG_PEA"))
    blob = ingest.read_blob(ws.store, ws.A, v["id"])
    assert hashlib.sha256(blob).hexdigest() == v["sha256"]
    ws.upload_key("hpg_update")
    v2 = ws.store.get(ws.A, "document_versions", v["id"])
    assert v2["sha256"] == v["sha256"] and v2["publication_date"] == v["publication_date"]


def test_identical_upload_is_deduplicated(ws):
    m = next(x for x in ws.ids["manifest"] if x["key"] == "hpg_mda")
    res = ingest.upload(ws.store, ws.A, filename="copy.pdf", data=Path(m["path"]).read_bytes(), title="dup",
                        doc_type="mda", company_id=ws.HPG)
    assert res["duplicate"] is True
    runs = ws.store.find(ws.A, "ingestion_runs", version_id=res["version"]["id"])
    assert len(runs) == 1


def test_new_version_of_a_document_keeps_the_old_one(ws):
    st, a = ws.store, ws.A
    r1 = ingest.upload(st, a, filename="note.txt", data=b"SYNTHETIC\n\nAs at October 1, 2026, the Company had cash and "
                       b"cash equivalents of C$5.0 million.\n", title="Note", doc_type="other", company_id=ws.QRC,
                       publication_date="2026-10-01")
    r2 = ingest.upload(st, a, filename="note.txt", data=b"SYNTHETIC\n\nAs at October 1, 2026, the Company had cash and "
                       b"cash equivalents of C$5.5 million.\n", title="Note", doc_type="other", company_id=ws.QRC,
                       publication_date="2026-10-03", new_version_of=r1["version"]["document_id"])
    assert r2["version"]["version_no"] == 2 and r2["version"]["supersedes_version_id"] == r1["version"]["id"]
    assert st.get(a, "document_versions", r1["version"]["id"])["sha256"] == r1["version"]["sha256"]
    # same metric and date, different value -> conflict preserved, not silently overwritten
    cash = [f for f in st.find(a, "facts", company_id=ws.QRC, metric_id="cash_unrestricted") if f["as_of_date"] == "2026-10-01"]
    assert {f["workflow_state"] for f in cash} == {"conflicting"}


def test_correction_is_a_new_revision(approved):
    from jmi import facts
    ws = approved
    ocr = ws.fact(raw_value="2O1")
    new = facts.correct_fact(ws.store, ws.A, ocr["id"], "letter O read as zero on visual check", raw_value="201")
    assert new["revision_of"] == ocr["id"] and new["relation"] == "correction" and new["normalized_value"] == "201000"
    assert ws.store.get(ws.A, "facts", ocr["id"])["workflow_state"] == "superseded"
    assert ws.store.get(ws.A, "facts", ocr["id"])["raw_value"] == "2O1"
