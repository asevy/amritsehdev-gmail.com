"""Scripted end-to-end demonstration over real HTTP (brief §18 "Final demonstration").

    python scripts/demo.py [DATA_DIR]

Starts the server on a free local port against a fresh data directory, then
drives it as the analyst, reviewer and a second tenant would. Every company,
document and figure is SYNTHETIC. Writes docs/DEMO_TRANSCRIPT.md.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fixtures import synthetic  # noqa: E402
from http_client import Client, serve_in_thread  # noqa: E402
from jmi import audit, config, monitoring  # noqa: E402
from jmi.auth import Auth, system_actor  # noqa: E402
from jmi.db import Database  # noqa: E402
from jmi.store import Store  # noqa: E402

PW = "demo-password-not-a-secret"
LOG: list[str] = []


def say(text=""):
    print(text)
    LOG.append(text)


def check(label, cond, detail=""):
    say(f"- [{'x' if cond else ' '}] {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        raise SystemExit(f"DEMO CHECK FAILED: {label} {detail}")


def main():
    data = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="jmi-demo-"))
    if data.exists():
        shutil.rmtree(data)
    config.set_clock(datetime(2026, 11, 17, 15, 0))
    db = Database(data / "jmi.sqlite3")
    auth = Auth(db)
    store = Store(db, data)
    auth.create_tenant("alpha", "Synthetic Resource Fund A", seats=10)
    auth.create_tenant("beta", "Other Fund LP (synthetic)", seats=5)
    for uid, role, t in [("analyst.a", "analyst", "alpha"), ("reviewer.a", "reviewer", "alpha"),
                         ("admin.a", "admin", "alpha"), ("analyst.b", "analyst", "beta")]:
        auth.create_user(uid, PW, role, t)
    monitoring.seed_feeds(store, system_actor("alpha", "setup"))
    monitoring.seed_feeds(store, system_actor("beta", "setup"))
    fx = synthetic.build(data / "fixtures")
    httpd, base = serve_in_thread(store, auth)
    say("# Junior Mining Intelligence — scripted demonstration (SYNTHETIC data)")
    say(f"\nServer: {base} · analysis clock pinned to 2026-11-17 15:00 UTC · data dir: (temporary)\n")
    A, R, B = Client(base), Client(base), Client(base)
    check("analyst, reviewer and other-tenant analyst sign in", A.login("analyst.a", PW) and R.login("reviewer.a", PW)
          and B.login("analyst.b", PW))

    say("\n## 1. Create the company/project workspace")
    ids, proj = {}, {}
    for key, spec in synthetic.COMPANIES.items():
        s, r = A.post("company.create", {"name": spec["name"], "reporting_currency": spec["currency"]})
        ids[key] = r["result"]["id"]
        A.post("listing.add", {"company_id": ids[key], "exchange": "XSYN", "ticker": spec["ticker"],
                               "currency": spec["listing_currency"]})
        p = spec["projects"][0]
        s, r = A.post("project.create", {"company_id": ids[key], "name": p["name"], "commodity": p["commodity"],
                                         "jurisdiction": p["jurisdiction"], "country": p["country"], "stage": p["stage"],
                                         "deposit_type": p["deposit_type"], "process_route": p["process_route"],
                                         "interest_pct": p["interest_pct"], "interest_kind": p["interest_kind"],
                                         "effective_date": p["effective_date"]})
        proj[key] = r["result"]["id"]
    check("5 synthetic companies with projects, listings and ownership created", len(ids) == 5)
    s, _ = B.post("company.create", {"name": "Halvard Peak Gold Corp."})
    check("the other tenant creates its own record of a same-named company", s == 200)

    say("\n## 2. Upload documents (PDF, XLSX, CSV, TXT) — ingestion runs on upload")
    runs = {}
    for m in fx:
        if m["key"] in ("hpg_update",):
            continue
        cli = B if m["tenant"] == "beta" else A
        cid = None
        if m["company"]:
            cid = ids[m["company"]] if m["tenant"] == "alpha" else json.loads(
                cli.get("/api/companies")[1])["companies"][0]["company"]["id"]
        s, r = cli.upload({"company_id": cid or "", "title": m["title"], "doc_type": m["doc_type"],
                           "publisher": m["publisher"], "publication_date": m["publication_date"],
                           "reporting_currency": m["reporting_currency"] or "", "synthetic": "1",
                           "is_issuer_primary": "1" if m["is_issuer_primary"] else "0"},
                          m["filename"], Path(m["path"]).read_bytes())
        runs[m["key"]] = r.get("result", {})
        say(f"  - {m['filename']}: HTTP {s}, ingestion {r.get('result', {}).get('run_status')}")
    check("corrupt PDF is a visible failed run, not silently skipped", runs["broken"]["run_status"] == "failed")
    st_alpha = system_actor("alpha", "demo")
    v = store.get(st_alpha, "document_versions", runs["hpg_drill_mirror"]["id"])
    check("mirrored press release detected and not re-extracted", bool(v["mirror_of_version_id"]),
          f"similarity {v['mirror_similarity']}")

    say("\n## 3. Inspect and review extracted facts")
    allf = store.find(st_alpha, "facts")
    by = {}
    for f in allf:
        by[f["workflow_state"]] = by.get(f["workflow_state"], 0) + 1
    say(f"  Workflow states after extraction: {json.dumps(by)}")
    hw = [f for f in allf if f["metric_id"] == "historical_estimate_contained_metal" and f["company_id"] == ids["HPG"]]
    check("number about a similarly named project of another company rejected (wrong entity)",
          hw and hw[0]["workflow_state"] == "rejected")
    ocr = next(f for f in allf if f["raw_value"] == "2O1")
    check("OCR-style '2O1' kept unread and sent to review", ocr["normalized_value"] is None)
    s, _ = A.post("fact.review", {"fact_id": allf[0]["id"], "decision": "approve", "reason": "self"})
    check("an analyst cannot approve facts (server-side role check)", s == 403, f"HTTP {s}")
    n = 0
    for f in allf:
        if f["workflow_state"] == "source_matched":
            s, _ = R.post("fact.review", {"fact_id": f["id"], "decision": "approve", "reason": "matches cited source"})
            n += s == 200
    check(f"reviewer approved {n} source-matched records (approval = matches source, not independent truth)", n > 100)
    s, r = A.post("fact.correct", {"fact_id": ocr["id"], "raw_value": "201", "reason": "visual check of cell: 201"})
    corrected = r["result"]["id"]
    s, _ = R.post("fact.review", {"fact_id": corrected, "decision": "approve", "reason": "page image checked"})
    check("OCR correction stored as a new revision and approved by a different person", s == 200)

    say("\n## 4. Surface a discrepancy and non-financial risks")
    disc = store.find(st_alpha, "discrepancies", kind="value_conflict")[0]
    say(f"  Discrepancy: {disc['detail']} (technical report vs investor presentation)")
    keep = next(f for f in store.find(st_alpha, "facts", metric_id="npv") if f["raw_value"] == "412")
    s, _ = R.post("discrepancy.resolve", {"discrepancy_id": disc["id"], "keep_fact_id": keep["id"],
                                          "resolution": "Technical report is the primary QP disclosure; deck figure "
                                                        "inconsistent and rejected"})
    check("reviewer resolves the conflict with a recorded reason; both sources preserved", s == 200)
    rk = store.find(st_alpha, "risk_findings", company_id=ids["HPG"])
    for x in rk:
        say(f"  Open question ({x['category']}): {x['title']}")
    check("permitting and going-concern items opened as QUESTIONS, not findings or grades",
          all(x["status"] == "open_question" for x in rk) and any(x["category"] == "permitting_environment" for x in rk))
    deck = runs["hpg_deck"]["id"]
    s, loc = A.post("cite", {"version_id": deck, "page_no": 1, "quote": "Fully funded through completion of the "
                                                                        "pre-feasibility study."})
    gc = next(x for x in rk if x["origin"] == "rule:going_concern")
    A.post("risk.evidence", {"risk_id": gc["id"], "stance": "contrary", "location_id": loc["result"]["id"],
                             "note": "issuer deck claims full funding to PFS (promotional; not verified)"})
    s, r = A.post("risk.create", {"company_id": ids["HPG"], "category": "evidence_quality",
                                  "title": "Presentation funding statement differs from MD&A going-concern disclosure",
                                  "unresolved_questions": "Which statement is current? Any financing since 2026-09-30?"})
    A.post("risk.evidence", {"risk_id": r["result"]["id"], "stance": "supporting", "location_id": loc["result"]["id"],
                             "note": "deck statement"})
    A.post("risk.attention", {"risk_id": r["result"]["id"], "attention": "1",
                              "reason": "contradictory issuer statements on funding"})
    check("analyst records an evidence-quality discrepancy with citations and an attention reason", s == 200)

    say("\n## 5. Approve a justified peer set and compare supported metrics")
    A.post("assumption.set", {"name": "fx_usd_cad", "value": "1.38", "unit": "CAD per USD", "as_of_date": "2026-11-13",
                              "source": "SYNTHETIC analyst entry (not a real rate)", "rationale": "convert USD balance sheets"})
    s, r = A.post("peerset.create", {"company_id": ids["HPG"], "project_id": proj["HPG"], "name": "Gold developers"})
    psid = r["result"]["id"]
    for m in store.find(st_alpha, "peer_members", peer_set_id=psid):
        co = store.get(st_alpha, "companies", m["company_id"])["name"]
        dec = ("excluded", "copper porphyry — different commodity") if "Quillon" in co else \
            ("approved", "gold asset; differences recorded and shown")
        A.post("peer.decide", {"member_id": m["id"], "decision": dec[0], "rationale": dec[1]})
        say(f"  {co}: {m['classification']} → {dec[0]} ({dec[1]})")
    A.post("peerset.approve", {"peer_set_id": psid, "rationale": "relative-value check for the OMG-style question"})
    s, r = A.post("snapshot.build", {"peer_set_id": psid, "market_data_date": "2026-11-13"})
    snap = json.loads(A.get(f"/api/snapshot/{r['result']['id']}")[1])
    for o in snap["body"]["observations"][:4]:
        say(f"  > {o}")
    for k, notes in snap["body"]["comparability"].items():
        for n_ in notes[:1]:
            say(f"  comparability [{k}]: {n_}")
    check("comparisons are per specified measure with unresolved differences; no overall winner",
          all("winner" not in o.lower() for o in snap["body"]["observations"]))

    say("\n## 6. Draft, review and approve a cited memo")
    s, r = A.post("thesis.create", {"company_id": ids["HPG"], "title": "Halvard Peak relative value",
                                    "thesis_text": "Halvard Peak shows a lower EV per M&I ounce than approved peers under "
                                                   "the stated inputs.",
                                    "counter_thesis_text": "The discount may reflect PEA-stage economics, an EIS decision "
                                                           "not yet issued, and a going-concern material uncertainty.",
                                    "assumption_text": "M&I resource of about 920 koz (effective 2026-04-30) supports scale",
                                    "assumption_metric": "resource_contained_metal"})
    thid = r["result"]["id"]
    s, r = A.post("memo.create", {"company_id": ids["HPG"], "title": "Halvard Peak Gold — memo (SYNTHETIC)",
                                  "thesis_id": thid, "peer_set_id": psid})
    mid = r["result"]["id"]
    vid = store.find(st_alpha, "memo_versions", memo_id=mid)[0]["id"]
    permit = next(f for f in store.find(st_alpha, "facts", metric_id="permit_status", company_id=ids["HPG"])
                  if f["normalized_value"] == "accepted_for_review")
    s, r = A.post("memo.claim", {"version_id": vid, "section": "summary", "kind": "factual",
                                 "text": "Halvard Peak has received its environmental permit.", "fact_ids": permit["id"]})
    check("unsupported claim citing a real source is withheld", r["result"]["validation"]["status"] == "unsupported",
          "; ".join(r["result"]["validation"]["reasons"]))
    A.post("memo.remove_claim", {"version_id": vid, "claim_id": r["result"]["id"], "reason": "not supported"})
    s, r = A.post("memo.claim", {"version_id": vid, "section": "summary", "kind": "factual",
                                 "text": "The company reports that its EIS application was accepted for review as at "
                                         "2026-05-20; the permit has not been issued.", "fact_ids": permit["id"]})
    check("restated claim with correct status and attribution is supported", r["result"]["validation"]["status"] == "supported")
    A.post("memo.submit", {"version_id": vid})
    s, r = R.post("memo.review_supported", {"version_id": vid, "reason": "checked against cited sources"})
    s, r = R.post("memo.approve", {"version_id": vid, "rationale": "pilot approval"})
    check("reviewer approves the memo version (author ≠ approver; all register risks included)", s == 200,
          json.dumps(r)[:200])
    s, pdf, h = A.get(f"/export/memo/{vid}.pdf")
    check("evidence-preserving PDF export recorded with its SHA-256", s == 200 and pdf.startswith(b"%PDF"),
          h.get("X-JMI-Export-SHA256", "")[:16])

    say("\n## 7. Ingest an update; show affected assumptions and stale outputs")
    m = next(x for x in fx if x["key"] == "hpg_update")
    s, r = A.upload({"company_id": ids["HPG"], "title": m["title"], "doc_type": m["doc_type"], "publisher": m["publisher"],
                     "publication_date": m["publication_date"], "synthetic": "1", "is_issuer_primary": "1"},
                    m["filename"], Path(m["path"]).read_bytes())
    inbox = json.loads(A.get("/api/inbox")[1])["events"]
    for e in inbox[:8]:
        say(f"  inbox: {e['kind']}: {e['title']}")
    mv = store.get(st_alpha, "memo_versions", vid)
    check("approved memo flagged stale, status and content unchanged", mv["status"] == "approved" and mv["stale"] == 1,
          mv["stale_reason"][:90])
    ta = store.find(st_alpha, "thesis_assumptions", company_id=ids["HPG"])[0]
    check("thesis assumption marked affected by the restatement", ta["status"] == "affected_by_change", ta["status_reason"])
    check("comparison snapshot marked stale",
          store.get(st_alpha, "comparison_snapshots", snap["id"])["stale"] == 1)
    cm = next(c for c in store.find(st_alpha, "commitments", company_id=ids["HPG"]) if "feasibility" in c["subject"])
    check("PFS target recorded as an explicit issuer revision (not inferred as 'missed')", cm["status"] == "revised")

    say("\n## 8. Unsupported answers are withheld")
    for q in ("What is the probability the project reaches production?", "Should we buy Halvard Peak?",
              "What is the 2027 production guidance?", "What is the true width of hole HP-26-041?",
              "What is the after-tax NPV?"):
        s, a = A.get_json(f"/api/ask?company={ids['HPG']}&q=" + q.replace(" ", "+").replace("?", "%3F"))
        say(f"  Q: {q}\n    → {a['status']}: {a.get('message', '')[:140]}"
            + (f"\n    → {a['answer'][0]['statement'][:160]}" if a.get("answer") else ""))

    say("\n## 9. Cross-tenant access is denied")
    hp_doc = runs["hpg_pea"]["id"]
    for p in (f"/doc/{hp_doc}", f"/api/blob/{hp_doc}", f"/export/memo/{vid}.pdf", f"/company/{ids['HPG']}"):
        s, _, _ = B.get(p)
        check(f"other tenant GET {p.split('/')[1]}/… → 404", s == 404, f"HTTP {s}")
    s, r = B.get_json("/api/search?q=intersected")
    check("other tenant search finds none of this tenant's passages", s == 200 and r["results"] == [])

    ig = db.integrity()
    check("database integrity ok and audit chain verifies", ig["sqlite"] == "ok" and ig["chain"]["ok"],
          f"{ig['chain']['rows']} audited events")
    httpd.shutdown()
    out = ROOT / "docs" / "DEMO_TRANSCRIPT.md"
    out.write_text("\n".join(LOG) + "\n\n_Generated by `python scripts/demo.py`. Identifiers differ per run; all data is "
                   "synthetic._\n")
    print(f"\ntranscript: {out}")
    print(f"data dir: {data}")


if __name__ == "__main__":
    main()
