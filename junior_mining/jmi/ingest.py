"""Upload and ingestion.

* Original bytes are stored unchanged, content-addressed (SHA-256) inside a
  per-tenant directory. A version row is immutable; a new upload of a changed
  file is a new version that points at the one it supersedes.
* Identical bytes in the same tenant are de-duplicated (the existing version
  is returned). Across tenants nothing is shared.
* Ingestion runs are idempotent: the key is tenant + content hash + parser
  version + extractor version. A failed run is visible, keeps its error, and
  can be retried; a succeeded run is never repeated silently.
* Near-identical text from a different publisher (a mirrored press release)
  is linked as a mirror and NOT extracted again — repetition is not
  corroboration.
* Document text is untrusted data. It is parsed, stored and searched; it is
  never treated as an instruction.
"""

from __future__ import annotations

import hashlib
import re
import traceback

from . import config, diligence, entities, events, facts, lineage, risks
from .auth import Actor, system_actor
from .definitions import METRICS
from .extract import DeterministicExtractor, ExtractionContext, EXTRACTOR, EXTRACTOR_VERSION
from .parsers import PARSER_VERSION, ParseError, parse, pdf_bbox
from .store import Invalid, Store
from .validate import VContext, validate

DOC_TYPES = ("technical_report", "mda", "financial_statements", "news_release", "presentation",
             "market_data", "regulatory_record", "other")
MIRROR_THRESHOLD = 0.8


def _norm_text(t: str) -> str:
    return re.sub(r"\s+", " ", t.lower()).strip()


def _shingles(t: str, k: int = 5) -> set:
    w = re.findall(r"[a-z0-9$.%/-]+", t.lower())
    return {" ".join(w[i:i + k]) for i in range(max(0, len(w) - k + 1))}


def upload(store: Store, actor: Actor, *, filename: str, data: bytes, title: str, doc_type: str,
           company_id: str | None = None, publisher: str = "", publication_date: str | None = None,
           source_url: str = "", reporting_currency: str | None = None, is_issuer_primary: bool = False,
           synthetic: bool = False, new_version_of: str | None = None, process_now: bool = True) -> dict:
    tenant = store.require(actor, "write")
    if doc_type not in DOC_TYPES:
        raise Invalid(f"doc_type must be one of {', '.join(DOC_TYPES)}")
    if not data:
        raise Invalid("empty upload")
    if len(data) > store.settings.max_upload_bytes:
        raise Invalid("file exceeds the configured upload limit")
    safe_name = re.sub(r"[^A-Za-z0-9._ -]", "_", filename)[:160] or "upload.bin"
    if company_id:
        store.get(actor, "companies", company_id)
    sha = hashlib.sha256(data).hexdigest()
    existing = store.find(actor, "document_versions", sha256=sha)
    if existing:
        v = existing[0]
        store.audit(actor, "upload_duplicate", v["id"], f"sha256={sha[:12]}")
        return {"version": v, "duplicate": True, "run": _latest_run(store, actor, v["id"])}
    path = store.blob_path(tenant, sha)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
        try:
            path.chmod(0o600)
        except OSError:
            pass
    now = config.iso_now()
    with store.db.tx():
        if new_version_of:
            doc = store.get(actor, "documents", new_version_of)
            prev = store.find(actor, "document_versions", document_id=doc["id"], order="version_no")
            version_no = (prev[-1]["version_no"] + 1) if prev else 1
            supersedes = prev[-1]["id"] if prev else None
        else:
            doc = store.insert(actor, "documents", {
                "company_id": company_id, "title": title, "doc_type": doc_type, "publisher": publisher,
                "is_issuer_primary": is_issuer_primary, "created_by": actor.user_id, "created_at": now})
            version_no, supersedes = 1, None
        v = store.insert(actor, "document_versions", {
            "document_id": doc["id"], "version_no": version_no, "sha256": sha, "size_bytes": len(data),
            "filename": safe_name, "mime": _mime(safe_name), "storage_path": str(path.relative_to(store.data_dir)),
            "publication_date": publication_date, "retrieved_at": now, "source_url": source_url,
            "reporting_currency": reporting_currency, "supersedes_version_id": supersedes,
            "parse_status": "pending", "synthetic": synthetic, "uploaded_by": actor.user_id, "uploaded_at": now})
        run = store.insert(actor, "ingestion_runs", {
            "version_id": v["id"], "idempotency_key": f"{tenant}|{sha}|{PARSER_VERSION}|{EXTRACTOR_VERSION}",
            "status": "queued", "attempts": 0, "created_at": now})
        store.usage(actor, "storage_bytes", len(data), "bytes", detail=v["id"])
        store.audit(actor, "document_uploaded", v["id"], {"sha256": sha, "doc": doc["id"], "type": doc_type})
    if process_now:
        run = process(store, tenant, run["id"])
    return {"version": store.get(actor, "document_versions", v["id"]), "duplicate": False, "run": run}


def _mime(name: str) -> str:
    n = name.lower()
    return ("application/pdf" if n.endswith(".pdf") else
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if n.endswith(".xlsx") else
            "text/csv" if n.endswith(".csv") else "text/plain" if n.endswith((".txt", ".md")) else
            "application/octet-stream")


def _latest_run(store, actor, version_id):
    runs = store.find(actor, "ingestion_runs", version_id=version_id, order="created_at")
    return runs[-1] if runs else None


def read_blob(store: Store, actor: Actor, version_id: str) -> bytes:
    v = store.get(actor, "document_versions", version_id)       # tenant-scoped; 404 otherwise
    return (store.data_dir / v["storage_path"]).read_bytes()


def process(store: Store, tenant_id: str, run_id: str) -> dict:
    """Run one ingestion job as a system principal confined to `tenant_id`."""
    sys_actor = system_actor(tenant_id, "ingest")
    run = store.get(sys_actor, "ingestion_runs", run_id)
    if run["status"] == "succeeded":
        return run
    store.update(sys_actor, "ingestion_runs", run_id, {"status": "running", "attempts": run["attempts"] + 1,
                                                        "started_at": config.iso_now(), "error": ""})
    v = store.get(sys_actor, "document_versions", run["version_id"])
    doc = store.get(sys_actor, "documents", v["document_id"])
    try:
        with store.db.tx():
            n = _process(store, sys_actor, v, doc, run)
        store.update(sys_actor, "ingestion_runs", run_id, {
            "status": "succeeded", "finished_at": config.iso_now(), "candidates": n,
            "extractor": EXTRACTOR, "extractor_version": EXTRACTOR_VERSION})
        _feed(store, sys_actor, ok=True)
    except Exception as exc:
        msg = f"{type(exc).__name__}: {str(exc)[:300]}"
        store.update(sys_actor, "ingestion_runs", run_id, {"status": "failed", "error": msg,
                                                            "finished_at": config.iso_now()})
        store.update(sys_actor, "document_versions", v["id"], {"parse_status": "failed",
                                                                "parse_warnings": [msg]})
        events.emit(store, sys_actor, "ingestion_failed", f"Ingestion failed: {doc['title']} — {msg}",
                    company_id=doc["company_id"], source_version_id=v["id"],
                    detail={"run": run_id, "error": msg})
        _feed(store, sys_actor, ok=False, error=msg)
        store.audit(sys_actor, "ingestion_failed", run_id, msg)
        if not isinstance(exc, ParseError):
            traceback.print_exc()
    return store.get(sys_actor, "ingestion_runs", run_id)


def retry_failed(store: Store, actor: Actor) -> list[dict]:
    tenant = store.require(actor, "write")
    out = []
    for r in store.find(actor, "ingestion_runs", status="failed"):
        out.append(process(store, tenant, r["id"]))
    return out


def _feed(store, actor, ok: bool, error: str = "") -> None:
    feeds = store.find(actor, "source_feeds", name="Document uploads")
    now = config.iso_now()
    if not feeds:
        store.insert(actor, "source_feeds", {
            "name": "Document uploads", "kind": "upload", "status": "active" if ok else "failed",
            "last_success_at": now if ok else None, "last_attempt_at": now, "last_error": error,
            "refresh_expectation_days": None,
            "licensing_note": "Customer-supplied files; rights are the uploader's responsibility."})
    else:
        patch = {"last_attempt_at": now, "status": "active" if ok else "failed", "last_error": error}
        if ok:
            patch["last_success_at"] = now
        store.update(actor, "source_feeds", feeds[0]["id"], patch)


def _process(store: Store, actor: Actor, v: dict, doc: dict, run: dict) -> int:
    path = store.data_dir / v["storage_path"]
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != v["sha256"]:
        raise ValueError("stored bytes do not match the recorded hash; refusing to process")
    parsed = parse(v["filename"], data)
    store.update(actor, "ingestion_runs", run["id"], {"parser": parsed.parser, "parser_version": PARSER_VERSION})
    for p in parsed.pages:
        store.insert(actor, "pages", {"version_id": v["id"], "page_no": p.page_no, "label": p.label,
                                      "text": p.text, "readable": p.readable})
        if p.readable:
            store.db.execute("INSERT INTO passages_fts(text,tenant_id,version_id,page_no,company_id) "
                             "VALUES(?,?,?,?,?)", (p.text, actor.tenant_id, v["id"], p.page_no,
                                                   doc["company_id"] or ""))
    for t in parsed.tables:
        store.insert(actor, "doc_tables", {"version_id": v["id"], "page_no": t.page_no,
                                           "table_index": t.table_index, "title": t.title, "rows": t.rows,
                                           "footnotes": t.footnotes})
    readable = [p for p in parsed.pages if p.readable]
    status = "parsed" if len(readable) == len(parsed.pages) else ("partial" if readable else "failed")
    full = _norm_text(parsed.full_text)
    fp = hashlib.sha256(full.encode()).hexdigest()
    store.update(actor, "document_versions", v["id"], {
        "page_count": len(parsed.pages), "unreadable_pages": parsed.unreadable_pages,
        "parse_status": status, "parse_warnings": parsed.warnings, "text_fingerprint": fp})
    store.usage(actor, "document_processed", 1, "document", detail=v["id"])
    store.usage(actor, "pages_parsed", len(parsed.pages), "pages", detail=v["id"])
    if parsed.unreadable_pages:
        events.emit(store, actor, "unreadable_pages",
                    f"{doc['title']}: page(s) {', '.join(map(str, parsed.unreadable_pages))} have no text layer "
                    "and were not read (no OCR configured)", company_id=doc["company_id"],
                    source_version_id=v["id"], notify=False)

    # Mirrored disclosure? Compare with other documents' current text.
    mine = _shingles(parsed.full_text)
    if mine and doc["doc_type"] != "market_data":
        for other in store.find(actor, "document_versions"):
            if other["id"] == v["id"] or other["document_id"] == doc["id"] or other["mirror_of_version_id"]:
                continue
            pages = store.find(actor, "pages", version_id=other["id"])
            theirs = _shingles("\n".join(p["text"] for p in pages))
            if not theirs:
                continue
            sim = len(mine & theirs) / len(mine | theirs)
            if sim >= MIRROR_THRESHOLD:
                store.update(actor, "document_versions", v["id"], {"mirror_of_version_id": other["id"],
                                                                    "mirror_similarity": f"{sim:.3f}"})
                odoc = store.get(actor, "documents", other["document_id"])
                orig = store.find(actor, "events", source_version_id=other["id"], kind="new_document")
                events.emit(store, actor, "new_document",
                            f"Mirrored release: '{doc['title']}' ({doc['publisher'] or 'unknown publisher'}) "
                            f"repeats '{odoc['title']}' — not extracted again; not independent corroboration",
                            company_id=doc["company_id"], source_version_id=v["id"],
                            detail={"mirror_of": other["id"], "similarity": f"{sim:.3f}"},
                            duplicate_of=orig[0]["id"] if orig else None)
                store.audit(actor, "mirror_detected", v["id"], f"of={other['id']}")
                return 0

    events.emit(store, actor, "new_document", f"New document: {doc['title']}", company_id=doc["company_id"],
                source_version_id=v["id"], event_date=v["publication_date"],
                detail={"doc_type": doc["doc_type"], "publisher": doc["publisher"],
                        "unreadable_pages": parsed.unreadable_pages},
                dedupe_key=f"doc:{v['sha256']}")

    aliases = entities.all_aliases(store, actor)
    company_projects = {}
    if doc["company_id"]:
        company_projects = {p["id"]: p["name"] for p in entities.projects_of(store, actor, doc["company_id"])}
    ctx = ExtractionContext(company_id=doc["company_id"], aliases=aliases, publication_date=v["publication_date"],
                            reporting_currency=v["reporting_currency"], doc_title=doc["title"],
                            listing_map=entities.listing_map(store, actor))
    cands, commits = DeterministicExtractor().extract(parsed, ctx)
    heading = doc["title"] + "\n" + (parsed.pages[0].text[:400] if parsed.pages else "")
    vctx = VContext(company_id=doc["company_id"], company_projects=company_projects, aliases=aliases,
                    reporting_currency=v["reporting_currency"], doc_heading=heading,
                    page_texts={p.page_no: p.text for p in parsed.pages},
                    table_cells={(t.table_index, ri, ci): cell for t in parsed.tables
                                 for ri, row in enumerate(t.rows) for ci, cell in enumerate(row)})
    n = 0
    is_pdf = v["filename"].lower().endswith(".pdf")
    for c in cands:
        val = validate(c, vctx)
        loc = c.location
        bbox, note = (None, "coordinates not applicable (not a PDF passage)")
        if is_pdf and loc.char_start is not None:
            bbox, note = pdf_bbox(data, loc.page_no, c.quote)
        elif loc.table_index is not None:
            note = "table cell reference (no coordinates)"
        lrow = store.insert(actor, "source_locations", {
            "version_id": v["id"], "page_no": loc.page_no, "table_index": loc.table_index,
            "row_index": loc.row_index, "col_index": loc.col_index, "cell_ref": loc.cell_ref,
            "char_start": loc.char_start, "char_end": loc.char_end, "quote": c.quote, "context": c.context,
            "row_header": loc.row_header, "col_header": loc.col_header, "footnotes": loc.footnotes,
            "bbox": bbox, "bbox_note": note})
        f = facts.insert_fact(store, actor, cand=c, val=val, version=v, location_id=lrow["id"],
                              run_id=run["id"], extractor=EXTRACTOR, extractor_version=EXTRACTOR_VERSION)
        n += 1
        if f["company_id"] and f["workflow_state"] != "rejected":
            risks.suggest_from_fact(store, actor, f)
            from . import monitoring
            monitoring.on_new_fact(store, actor, f)
    for cc in commits:
        if not doc["company_id"]:
            continue
        lrow = store.insert(actor, "source_locations", {
            "version_id": v["id"], "page_no": cc.location.page_no, "char_start": cc.location.char_start,
            "char_end": cc.location.char_end, "quote": cc.wording, "context": cc.context,
            "footnotes": [], "bbox": None, "bbox_note": "sentence offsets"})
        pid = None
        if cc.project_mention:
            for a in aliases:
                if a.kind == "project" and a.alias == cc.project_mention and a.company_id == doc["company_id"]:
                    pid = a.entity_id
        diligence.record_commitment(store, actor, doc["company_id"], cc, lrow["id"], pid, v["id"])
    if doc["company_id"]:
        for it in store.find(actor, "diligence_items", company_id=doc["company_id"]):
            diligence.refresh(store, actor, doc["company_id"], it["project_id"])
            break
    store.audit(actor, "ingestion_succeeded", v["id"], {"candidates": n, "commitments": len(commits),
                                                        "extractor": EXTRACTOR_VERSION,
                                                        "parser": PARSER_VERSION})
    return n


def cite(store: Store, actor: Actor, version_id: str, page_no: int, quote: str) -> dict:
    """Create a source location for an analyst-selected passage.

    The quote must occur in the stored page text (whitespace-insensitive). The
    location records the exact characters found — a citation is never placed
    where the text is not."""
    store.require(actor, "write")
    v = store.get(actor, "document_versions", version_id)
    pages = store.find(actor, "pages", version_id=version_id, page_no=int(page_no))
    if not pages:
        raise Invalid(f"page {page_no} does not exist in this document version")
    text = pages[0]["text"]
    q = re.sub(r"\s+", " ", quote).strip()
    if len(q) < 8:
        raise Invalid("quote at least 8 characters so the citation is unambiguous")
    rx = re.compile(r"\s+".join(re.escape(w) for w in q.split(" ")))
    hits = list(rx.finditer(text))
    if not hits:
        raise Invalid("the quoted text does not occur on that page; nothing was cited")
    m = hits[0]
    bbox, note = None, "sentence offsets"
    if v["filename"].lower().endswith(".pdf"):
        bbox, note = pdf_bbox((store.data_dir / v["storage_path"]).read_bytes(), int(page_no), m.group(0))
    from .extract import paragraph_bounds, norm_ws
    pa, pb = paragraph_bounds(text, *m.span())
    row = store.insert(actor, "source_locations", {
        "version_id": version_id, "page_no": int(page_no), "char_start": m.start(), "char_end": m.end(),
        "quote": m.group(0), "context": norm_ws(text[pa:pb]), "footnotes": [], "bbox": bbox,
        "bbox_note": note + (f"; quote occurs {len(hits)} times, first occurrence cited" if len(hits) > 1 else "")})
    store.audit(actor, "citation_created", row["id"], f"version={version_id} page={page_no}")
    return row


def coverage(store: Store, actor: Actor, company_id: str) -> dict:
    """What the evidence base consists of: shown next to every output."""
    store.get(actor, "companies", company_id)          # 404 for another tenant's company
    docs = [d for d in store.find(actor, "documents") if d["company_id"] == company_id]
    vers, failed, unreadable, mirrors = [], [], [], []
    for d in docs:
        for v in store.find(actor, "document_versions", document_id=d["id"]):
            run = _latest_run(store, actor, v["id"])
            item = {"version_id": v["id"], "title": d["title"], "publication_date": v["publication_date"],
                    "doc_type": d["doc_type"], "parse_status": v["parse_status"],
                    "run_status": run["status"] if run else "none"}
            if v["mirror_of_version_id"]:
                mirrors.append(item)
                continue
            if run and run["status"] == "failed":
                failed.append(item)
            elif v["unreadable_pages"]:
                unreadable.append({**item, "pages": v["unreadable_pages"]})
            vers.append(item)
    # market snapshots are multi-company files: include those with rows for this company
    for f in store.find(actor, "facts", company_id=company_id, metric_id="share_price"):
        if f["version_id"] and not any(x["version_id"] == f["version_id"] for x in vers):
            v = store.get(actor, "document_versions", f["version_id"])
            d = store.get(actor, "documents", v["document_id"])
            vers.append({"version_id": v["id"], "title": d["title"], "publication_date": v["publication_date"],
                         "doc_type": d["doc_type"], "parse_status": v["parse_status"], "run_status": "succeeded"})
    dates = [x["publication_date"] for x in vers if x["publication_date"] and x["run_status"] == "succeeded"]
    return {"documents_reviewed": [x for x in vers if x["run_status"] == "succeeded"],
            "ingestion_failed": failed, "unreadable_pages": unreadable, "mirrors_not_counted": mirrors,
            "evidence_cutoff": max(dates) if dates else None,
            "analysis_time": config.iso_now(),
            "complete": not failed and not unreadable}
