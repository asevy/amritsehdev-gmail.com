"""Evidence-preserving exports (brief §13).

PDF / CSV / JSON exports keep source references, dates, assumptions,
calculation definitions, draft/approval status and unresolved gaps. Each
export is recorded (exports table + audit chain) with the exact memo version
and the SHA-256 of the bytes produced. Drafts are visibly marked on every
page. Nothing is sent anywhere: exports are downloads only.
"""

from __future__ import annotations

import csv
import hashlib
import io

from . import calc, config, memo as M
from . import definitions as D
from .auth import Actor
from .db import dumps
from .store import AccessDenied, Store


def _record(store, actor, kind, target_id, target_version, fmt, status_label, data: bytes) -> dict:
    sha = hashlib.sha256(data).hexdigest()
    row = store.insert(actor, "exports", {"kind": kind, "target_id": target_id, "target_version": target_version,
                                          "fmt": fmt, "status_label": status_label, "sha256": sha,
                                          "created_by": actor.user_id, "created_at": config.iso_now()},
                       cap="export")
    store.audit(actor, "export", f"{kind}:{target_id}", {"version": target_version, "fmt": fmt, "sha256": sha,
                                                          "status": status_label})
    store.usage(actor, "export", 1, fmt, detail=f"{kind}:{target_id}")
    return row


def memo_export(store: Store, actor: Actor, version_id: str, fmt: str) -> tuple[bytes, str, dict]:
    if not actor.can("export"):
        raise AccessDenied(f"role '{actor.role}' cannot export")
    r = M.render(store, actor, version_id)
    r["export"] = {"exported_by": actor.user_id, "exported_at": config.iso_now(),
                   "calculation_definitions": calc.definitions(), "metric_registry_version": D.REGISTRY_VERSION}
    if fmt == "json":
        data, ctype = dumps(r).encode("utf-8"), "application/json"
    elif fmt == "csv":
        data, ctype = _memo_csv(r), "text/csv"
    elif fmt == "pdf":
        data, ctype = _memo_pdf(r), "application/pdf"
    else:
        raise ValueError("format must be json, csv or pdf")
    rec = _record(store, actor, "memo", r["memo_id"], version_id, fmt, r["status_label"], data)
    return data, ctype, rec


def _memo_csv(r: dict) -> bytes:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["memo", r["title"], "version", r["version_no"], "status", r["status_label"]])
    w.writerow(["analysis_time", r["analysis_time"], "evidence_cutoff", r["evidence_cutoff"],
                "documents_reviewed", r["coverage"]["documents_reviewed"], "content_sha256", r["content_sha256"] or ""])
    w.writerow([])
    w.writerow(["section", "claim_id", "kind", "claim", "review", "evidence_kind", "evidence_id", "document",
                "page", "cell", "quote", "state", "evidence_type", "published", "document_sha256"])
    for s in r["sections"]:
        for it in s["items"]:
            ev = it["evidence"] or [{}]
            for e in ev:
                w.writerow([s["title"], it["id"], it["kind"], it["text"], it["review"].get("status", ""),
                            "fact" if "fact_id" in e else "calculation" if "calc_id" in e else "",
                            e.get("fact_id") or e.get("calc_id") or "", e.get("document") or "", e.get("page") or "",
                            e.get("cell") or "", e.get("quote") or "", e.get("state") or "",
                            e.get("evidence_type") or "", e.get("published") or "", e.get("sha256") or ""])
    w.writerow([])
    w.writerow(["unresolved"])
    for u in r["unresolved"]:
        w.writerow([u])
    w.writerow(["withheld_claims"])
    for x in r["withheld_claims"]:
        w.writerow([x["id"], x["text"], "; ".join(x["reasons"])])
    return out.getvalue().encode("utf-8")


def _memo_pdf(r: dict) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    from xml.sax.saxutils import escape
    buf = io.BytesIO()
    st = getSampleStyleSheet()
    draft = r["status"] != "approved" or "STALE" in r["status_label"]

    def mark(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(40, 770, (r["status_label"] + (" — SYNTHETIC DATA" if r["synthetic"] else ""))[:150])
        canvas.drawString(40, 20, f"version {r['version_id']} · analysis {r['analysis_time']} · evidence cutoff "
                                  f"{r['evidence_cutoff']} · page {doc.page}")
        if draft:
            canvas.setFont("Helvetica-Bold", 60)
            canvas.setFillGray(0.85)
            canvas.translate(300, 400)
            canvas.rotate(35)
            canvas.drawCentredString(0, 0, "DRAFT")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=letter, invariant=1, title=r["title"])
    P = lambda t, s="BodyText": Paragraph(escape(str(t)), st[s])
    story = [P(r["title"], "Title"), P(f"{r['company']} — {r['status_label']}"), P(r["notice"]),
             P(f"Analysis time {r['analysis_time']}; evidence cutoff {r['evidence_cutoff']}; documents reviewed "
               f"{r['coverage']['documents_reviewed']}; coverage complete: {r['coverage']['complete']}."),
             Spacer(1, 8)]
    if r["unresolved"]:
        story.append(P("Unresolved items", "Heading3"))
        story += [P("• " + u) for u in r["unresolved"]]
    for s in r["sections"]:
        story.append(P(s["title"], "Heading2"))
        if not s["items"]:
            story.append(P("Nothing recorded."))
        for it in s["items"]:
            story.append(P(f"[{it['id']}] {it['text']}  (review: {it['review'].get('status')})"))
            for e in it["evidence"]:
                if "fact_id" in e:
                    story.append(P(f"    source: {e['document']}, p.{e['page']}{(' ' + e['cell']) if e.get('cell') else ''} — "
                                   f"\"{(e['quote'] or '')[:160]}\" ({e['state']}; {e['evidence_type']}; fact {e['fact_id']})",
                                   "Code"))
                elif "calc_id" in e:
                    story.append(P(f"    calculation {e['calc_id']} ({e['formula']}); inputs: "
                                   + "; ".join(f"{i['name']}={i['value']} {i.get('unit') or ''} [{i['kind']} {i.get('ref_id') or ''}]"
                                               for i in e["inputs"])[:600], "Code"))
            if it.get("risk"):
                rk = it["risk"]
                story.append(P(f"    {rk['category']} — {rk['status']}. {rk['attention']}"))
                for x in rk["supporting"]:
                    story.append(P(f"    supporting ({x.get('date')}): {x.get('document', '')} p.{x.get('page', '')} "
                                   f"\"{x.get('quote', '')[:140]}\"", "Code"))
                for x in rk["contrary"]:
                    story.append(P(f"    contrary ({x.get('date')}): {x.get('document', '')} p.{x.get('page', '')} "
                                   f"\"{x.get('quote', '')[:140]}\"", "Code"))
                if rk.get("contrary_note"):
                    story.append(P("    " + rk["contrary_note"], "Code"))
    if r["withheld_claims"]:
        story.append(P("Withheld claims (not part of the memo body)", "Heading2"))
        for x in r["withheld_claims"]:
            story.append(P(f"[{x['id']}] {x['text']} — withheld: {'; '.join(x['reasons'])}"))
    doc.build(story, onFirstPage=mark, onLaterPages=mark)
    return buf.getvalue()


def facts_csv(store: Store, actor: Actor, company_id: str) -> tuple[bytes, dict]:
    if not actor.can("export"):
        raise AccessDenied(f"role '{actor.role}' cannot export")
    company = store.get(actor, "companies", company_id)
    out = io.StringIO()
    w = csv.writer(out)
    cols = ["fact_id", "metric", "definition_version", "project_id", "raw_text", "raw_value", "normalized_value",
            "unit", "currency", "resource_category", "scope_basis", "study_type", "tax_basis", "discount_rate",
            "as_of_date", "effective_date", "period_start", "period_end", "publication_date", "retrieved_at",
            "evidence_type", "attribution", "workflow_state", "missing_reason", "transformations", "document",
            "document_sha256", "page", "cell_ref", "char_start", "char_end", "revision_of", "relation"]
    w.writerow(["company", company["name"], "exported_at", config.iso_now(), "synthetic", bool(company["synthetic"])])
    w.writerow(cols)
    for f in store.find(actor, "facts", company_id=company_id, order="metric_id, created_at"):
        loc = store.get(actor, "source_locations", f["location_id"]) if f["location_id"] else {}
        ver = store.get(actor, "document_versions", f["version_id"]) if f["version_id"] else {}
        doc = store.get(actor, "documents", ver["document_id"]) if ver else {}
        w.writerow([f["id"], f["metric_id"], f["definition_version"], f["project_id"], f["raw_text"], f["raw_value"],
                    f["normalized_value"], f["unit"], f["currency"], f["resource_category"], f["scope_basis"],
                    f["study_type"], f["tax_basis"], f["discount_rate"], f["as_of_date"], f["effective_date"],
                    f["period_start"], f["period_end"], f["publication_date"], f["retrieved_at"], f["evidence_type"],
                    f["attribution"], f["workflow_state"], f["missing_reason"], " | ".join(f["transformations"]),
                    doc.get("title"), ver.get("sha256"), loc.get("page_no"), loc.get("cell_ref"),
                    loc.get("char_start"), loc.get("char_end"), f["revision_of"], f["relation"]])
    data = out.getvalue().encode("utf-8")
    rec = _record(store, actor, "facts", company_id, None, "csv", "fact register (all workflow states shown)", data)
    return data, rec


def snapshot_csv(store: Store, actor: Actor, snapshot_id: str) -> tuple[bytes, dict]:
    if not actor.can("export"):
        raise AccessDenied(f"role '{actor.role}' cannot export")
    s = store.get(actor, "comparison_snapshots", snapshot_id)
    b = s["body"]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["peer set", b["peer_set_name"], "market_data_date", b["market_data_date"], "stale",
                bool(s["stale"]), s["stale_reason"]])
    w.writerow(["company", "project", "role", "classification"] + [label for _, label in b["metric_rows"]])
    for r in b["rows"]:
        w.writerow([r["company"], r["project"], r["role"], r["classification"]] +
                   [(c.get("display") if c.get("status") in ("computed", "reported") else "Withheld: " + c.get("reason", ""))
                    for c in (r["cells"].get(k, {}) for k, _ in b["metric_rows"])])
    w.writerow([])
    for k, notes in b["comparability"].items():
        for n in notes:
            w.writerow(["comparability", k, n])
    data = out.getvalue().encode("utf-8")
    rec = _record(store, actor, "snapshot", snapshot_id, snapshot_id, "csv", "comparison snapshot", data)
    return data, rec
