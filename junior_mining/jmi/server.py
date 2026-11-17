"""HTTP server: the eight working screens, a JSON API and the action endpoint.

Provenance (adapted): asevy/vision-edge-gateway @ 592cbff, ve_server.py —
security headers, HttpOnly + SameSite=Strict session cookie (Secure behind a
TLS proxy), session-bound CSRF token on every write, body-size cap, data-layer
refusals mapped to 403/404 without detail, another tenant's record answered
with 404 not 403. Changed: CSP forbids scripts entirely (the UI is plain
forms); multipart uploads; a policy guard checks JSON output for score-like
fields before it leaves the process.

Standard library HTTP server. Bind to 127.0.0.1 and put a TLS reverse proxy
in front before it leaves the machine (see docs/DEPLOY.md).
"""

from __future__ import annotations

import email.parser
import email.policy
import json
import re
import sys
import time
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import (answers, audit as AU, calc, config, diligence, entities, events, exports, facts as F, ingest,
               memo as M, monitoring, parsers, peers, policy, risks)
from . import definitions as D
from . import ui
from .auth import Auth, ROLES
from .db import Database, dumps
from .store import AccessDenied, Invalid, NotFound, Store
from .ui import esc

MAX_JSON = 2_000_000
COOKIE = "jmisess"


class App:
    def __init__(self, store: Store, auth: Auth, policy_guard: bool = True):
        self.store = store
        self.auth = auth
        self.policy_guard = policy_guard
        self.png_cache: dict = {}


def _split(v: str) -> list[str]:
    return [x.strip() for x in (v or "").replace("\n", ",").split(",") if x.strip()]


class Handler(BaseHTTPRequestHandler):
    server_version = "JMI"
    sys_version = ""

    # ------------------------------------------------------------ plumbing
    def log_message(self, fmt, *args):
        if getattr(self.server, "quiet", False):
            return
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    @property
    def app(self) -> App:
        return self.server.app

    @property
    def st(self) -> Store:
        return self.server.app.store

    def _cookie(self, name):
        for part in self.headers.get("Cookie", "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == name:
                return v
        return None

    def _send(self, code, body: bytes, ctype="text/html; charset=utf-8", extra=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; "
                                                    "form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, where, extra=()):
        if not where.startswith("/") or where.startswith("//"):
            where = "/"
        self.send_response(303)
        self.send_header("Location", where)
        self.send_header("Content-Length", "0")
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()

    def _json(self, code, obj):
        if self.app.policy_guard and code == 200:
            bad = policy.scan(obj)
            if bad:
                sys.stderr.write("policy guard blocked a response: %s\n" % bad[:3])
                return self._send(500, b'{"error":"policy_guard"}', "application/json")
        return self._send(code, dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def _actor(self):
        return self.app.auth.actor(self._cookie(COOKIE))

    def _csrf(self):
        return self.app.auth.csrf_for(self._cookie(COOKIE))

    def _error(self, exc, as_json: bool, actor=None):
        if isinstance(exc, (NotFound, LookupError)):
            code, kind = 404, "not_found"
        elif isinstance(exc, (AccessDenied, PermissionError)):
            code, kind = 403, "denied"
        elif isinstance(exc, (Invalid, ValueError, parsers.ParseError)):
            code, kind = 400, "invalid"
        else:
            traceback.print_exc()
            code, kind = 500, "server_error"
        msg = str(exc) if code != 500 else "server error"
        if code == 404:
            msg = "not found"            # never reveal whether another tenant's record exists
        if as_json:
            return self._send(code, dumps({"error": kind, "message": msg}).encode(), "application/json")
        return self._send(code, ui.page("Not completed", f"<p>{esc(msg)}</p><p><a href=\"/\">Back</a></p>", actor))

    # ------------------------------------------------------------ GET
    def do_GET(self):
        with self.st.db.lock:        # one request at a time against the single SQLite connection
            return self._do_get()

    def do_POST(self):
        with self.st.db.lock:
            return self._do_post()

    def _do_get(self):
        u = urllib.parse.urlparse(self.path)
        path, q = u.path, urllib.parse.parse_qs(u.query)
        one = lambda k, d="": (q.get(k) or [d])[0]
        actor = self._actor()
        if path == "/login":
            return self._send(200, _login_page(""))
        if path == "/logout":
            t = self._cookie(COOKIE)
            if t:
                self.app.auth.logout(t)
            return self._redirect("/login", [("Set-Cookie", f"{COOKIE}=; Max-Age=0; Path=/")])
        if path == "/health":
            return self._send(200, b"ok", "text/plain")
        if not actor:
            if path.startswith(("/api/", "/export/")):
                return self._json(401, {"error": "not_signed_in"})
            return self._redirect("/login")
        as_json = path.startswith("/api/")
        try:
            for rx, name in GET_ROUTES:
                m = re.fullmatch(rx, path)
                if m:
                    return getattr(self, name)(actor, *m.groups(), q=q, one=one)
            return self._send(404, ui.page("Not found", "<p>No such page.</p>", actor))
        except Exception as exc:
            return self._error(exc, as_json, actor)

    # ------------------------------------------------------------ POST
    def _do_post(self):
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        ctype = self.headers.get("Content-Type", "")
        if path == "/login":
            body = self.rfile.read(min(length, 64_000)).decode("utf-8", "replace")
            form = urllib.parse.parse_qs(body)
            uid, pw = (form.get("user_id") or [""])[0].strip(), (form.get("password") or [""])[0]
            try:
                token, _csrf = self.app.auth.authenticate(uid, pw)
            except ValueError as exc:
                time.sleep(0.3)
                return self._send(401, _login_page(str(exc)))
            secure = " Secure;" if self.headers.get("X-Forwarded-Proto") == "https" else ""
            return self._redirect("/", [("Set-Cookie", f"{COOKIE}={token}; HttpOnly; Path=/; SameSite=Strict;{secure} "
                                                       f"Max-Age={self.st.settings.session_ttl_seconds}")])
        actor = self._actor()
        if not actor:
            return self._json(401, {"error": "not_signed_in"})
        limit = self.st.settings.max_upload_bytes + 100_000 if ctype.startswith("multipart/") else MAX_JSON
        if length > limit:
            return self._json(413, {"error": "too_large"})
        raw = self.rfile.read(length)
        files = {}
        is_json = ctype.startswith("application/json")
        if is_json:
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except ValueError:
                return self._json(400, {"error": "bad_json"})
            token = self.headers.get("X-JMI-CSRF", "")
        elif ctype.startswith("multipart/form-data"):
            payload, files = _multipart(ctype, raw)
            token = payload.get("csrf", "")
        else:
            payload = {k: v[0] for k, v in urllib.parse.parse_qs(raw.decode("utf-8", "replace")).items()}
            token = payload.get("csrf", "")
        if not token or token != self._csrf():
            return self._json(400, {"error": "bad_csrf"}) if is_json else \
                self._send(400, ui.page("Form expired", "<p>Missing or invalid form token. Reload the page and retry.</p>", actor))
        m = re.fullmatch(r"/api/([a-z_.]+)", path)
        if not m or m.group(1) not in ACTIONS:
            return self._json(404, {"error": "no_such_action"})
        try:
            result = ACTIONS[m.group(1)](self.st, actor, payload, files)
        except Exception as exc:
            return self._error(exc, is_json, actor)
        nxt = payload.get("_next", "")
        if not is_json and nxt:
            nxt = nxt.replace("{id}", str((result or {}).get("id", "")))
            return self._redirect(nxt)
        return self._json(200, {"ok": True, "result": result})

    # ============================================================ views
    def v_whoami(self, a, **_):
        return self._json(200, {"user": a.user_id, "role": a.role, "tenant": a.tenant_id, "caps": sorted(a.caps),
                                "csrf": self._csrf()})

    def v_coverage(self, a, q, one, **_):
        st, csrf = self.st, self._csrf()
        wl = one("watchlist") or None
        rows = monitoring.watchlist_view(st, a, wl)
        trs = []
        for r in rows:
            c = r["company"]
            trs.append([f'<a href="/company/{esc(c["id"])}">{esc(c["name"])}</a>' +
                        (' <span class="note">(synthetic)</span>' if c["synthetic"] else ""),
                        "<br>".join(esc(f"{p['name']} — {p['commodity']}, {p['jurisdiction']}, "
                                        f"{D.STAGE_LABELS.get(p['stage'] or '', 'stage not recorded')}") for p in r["projects"]),
                        "<b>" + esc(r["status"].replace("_", " ")) + "</b>" +
                        (f"<br><span class=\"note\">also: {esc(', '.join(s for s in r['statuses'] if s != r['status']))}</span>"
                         if len(r["statuses"]) > 1 else ""),
                        "<br>".join(esc(x) for x in r["reasons"]) or "—", esc(r["evidence_cutoff"] or "none"),
                        str(r["new_events"])])
        feeds = st.find(a, "source_feeds", order="kind, name")
        frows = [[esc(f["name"]), esc(f["kind"]), "<b>" + esc(f["status"].replace("_", " ")) + "</b>",
                  esc(f["last_success_at"] or "—"), esc(f["last_error"] or ""), esc(f["licensing_note"])] for f in feeds]
        wls = st.find(a, "watchlists", order="name")
        body = ('<p class="note">Coverage status describes the evidence base — fresh, stale, incomplete or ingestion '
                'failed — not the company.</p>')
        if wls:
            body += "<p>Watchlists: " + " · ".join(f'<a href="/?watchlist={esc(w["id"])}">{esc(w["name"])}</a>' for w in wls) + \
                    ' · <a href="/">all companies</a></p>'
        body += ui.table(["Company", "Projects", "Coverage status", "Reasons", "Evidence cutoff", "New events"], trs,
                         "No companies yet.")
        body += "<h2>Sources and connectors</h2>" + ui.table(
            ["Source", "Kind", "Status", "Last success", "Last error", "Access / licensing note"], frows)
        if a.can("write"):
            body += "<h2>Add a company</h2>" + ui.form("/api/company.create", ui.inp("name", "Company name", required=True) +
                                                        ui.inp("reporting_currency", "Reporting currency (e.g. CAD)") +
                                                        ui.inp("aliases", "Former names (comma separated)"),
                                                        csrf, "Create company", "/company/{id}")
            body += "<h2>Upload a multi-company file (e.g. market snapshot)</h2>" + _upload_form(csrf, None, "/")
            body += "<h2>Watchlists</h2>" + ui.form("/api/watchlist.create", ui.inp("name", "New watchlist name", required=True),
                                                    csrf, "Create watchlist", "/")
            if wls and rows:
                body += ui.form("/api/watchlist.add", ui.sel("watchlist_id", "Watchlist", [(w["id"], w["name"]) for w in wls]) +
                                ui.sel("company_id", "Company", [(r["company"]["id"], r["company"]["name"]) for r in rows]),
                                csrf, "Add to watchlist", "/")
        return self._send(200, ui.page("Coverage", body, a))

    def _company(self, a, cid):
        return self.st.get(a, "companies", cid)

    def v_company(self, a, cid, q, one, **_):
        st, csrf = self.st, self._csrf()
        c = self._company(a, cid)
        cs = monitoring.coverage_status(st, a, cid)
        listings = st.find(a, "listings", company_id=cid)
        aliases = st.find(a, "entity_aliases", entity_kind="company", entity_id=cid)
        body = (f"<p><b>Coverage:</b> {esc(cs['status'].replace('_', ' '))} — {esc('; '.join(cs['reasons']) or 'no issues recorded')}</p>"
                + ui.coverage_block(cs["coverage"]))
        body += "<h2>Identity</h2>" + ui.table(["Legal / recorded names", "Listings", "Reporting currency"], [[
            "<br>".join(esc(f"{x['alias']} ({x['alias_kind']})") for x in aliases),
            "<br>".join(esc(f"{l['exchange']}:{l['ticker']} ({l['currency'] or '?'})") for l in listings) or ui.missing("no listing"),
            esc(c["reporting_currency"] or "not recorded")]])
        projs = entities.projects_of(st, a, cid)
        prow = []
        for p in projs:
            hist = st.find(a, "ownership_interests", company_id=cid, project_id=p["id"], order="effective_date")
            prow.append([f'<a href="/project/{esc(p["id"])}">{esc(p["name"])}</a>', esc(p["commodity"]), esc(p["jurisdiction"]),
                         esc(D.STAGE_LABELS.get(p["stage"] or "", "not recorded")), esc(p["deposit_type"]),
                         esc(p["process_route"]),
                         "<br>".join(esc(f"{h['interest_pct'] or 'not established'}% {h['interest_kind']} from "
                                         f"{h['effective_date'] or '?'}" + (f" to {h['end_date']}" if h["end_date"] else " (current)"))
                                     for h in hist)])
        body += "<h2>Projects (assets are modelled separately from the issuer)</h2>" + ui.table(
            ["Project", "Commodity", "Jurisdiction", "Stage", "Deposit", "Process", "Ownership history"], prow)
        groups = [("Capital structure and balance sheet", ["share_price", "average_daily_volume", "shares_outstanding_basic",
                                                            "warrants_outstanding", "options_outstanding", "cash_unrestricted",
                                                            "cash_restricted", "total_debt", "period_cash_outflow"]),
                  ("Resources and reserves", ["resource_contained_metal", "resource_tonnage", "resource_grade",
                                              "reserve_contained_metal", "reserve_tonnage", "reserve_grade",
                                              "historical_estimate_contained_metal"]),
                  ("Study economics (forecasts)", ["npv", "irr", "initial_capex", "aisc", "commodity_price_assumption",
                                                   "plant_recovery_assumption"]),
                  ("Metallurgy, drilling, permits, ownership, disclosures", ["met_test_recovery", "drill_intercept_length",
                                                                            "drill_intercept_grade", "true_width",
                                                                            "permit_status", "ownership_interest",
                                                                            "disclosure_signal"])]
        allf = [f for f in st.find(a, "facts", company_id=cid) if f["workflow_state"] in D.CURRENT_STATES]
        for title, metrics in groups:
            rows = [f for f in allf if f["metric_id"] in metrics]
            rows.sort(key=lambda f: (metrics.index(f["metric_id"]), f["effective_date"] or f["as_of_date"] or "",
                                     f["resource_category"] or ""))
            absent = [D.metric(m).label for m in metrics if not any(f["metric_id"] == m for f in allf)]
            body += f"<h2>{esc(title)}</h2>" + ui.table(ui.FACT_HEADERS, ui.fact_rows(rows), "No current records.")
            if absent:
                body += f'<p class="note">Not found in documents reviewed: {esc(", ".join(absent))}.</p>'
        body += (f'<p><a href="/company/{esc(cid)}/documents">Documents and upload</a> · '
                 f'<a href="/export/facts/{esc(cid)}.csv">Export fact register (CSV)</a></p>')
        if a.can("write"):
            body += "<h2>Add listing / project</h2>" + ui.form("/api/listing.add", ui.hid("company_id", cid) +
                                                                ui.inp("exchange", "Exchange") + ui.inp("ticker", "Ticker") +
                                                                ui.inp("currency", "Trading currency"), csrf, "Add listing",
                                                                f"/company/{cid}")
            body += ui.form("/api/project.create", ui.hid("company_id", cid) + ui.inp("name", "Project name", required=True) +
                            ui.inp("commodity", "Primary commodity") + ui.inp("jurisdiction", "Jurisdiction") +
                            ui.inp("country", "Country") + ui.sel("stage", "Stage", [(s, D.STAGE_LABELS[s]) for s in D.STAGES]) +
                            ui.inp("deposit_type", "Deposit type") + ui.inp("process_route", "Process route") +
                            ui.inp("interest_pct", "Ownership % (blank if not established)") +
                            ui.inp("effective_date", "Interest effective date (YYYY-MM-DD)"),
                            csrf, "Add project", f"/company/{cid}")
        return self._send(200, ui.page(c["name"], body, a, company=c))

    def v_project(self, a, pid, **_):
        st = self.st
        p = st.get(a, "projects", pid)
        oi = st.find(a, "ownership_interests", project_id=pid, order="effective_date")
        cid = oi[0]["company_id"] if oi else None
        c = st.get(a, "companies", cid) if cid else None
        rows = [f for f in st.find(a, "facts", project_id=pid) if f["workflow_state"] in D.CURRENT_STATES]
        rows.sort(key=lambda f: (f["metric_id"], f["effective_date"] or f["as_of_date"] or ""))
        aliases = st.find(a, "entity_aliases", entity_kind="project", entity_id=pid)
        body = (f"<p>{esc(p['commodity'])} · {esc(p['jurisdiction'])} · stage {esc(D.STAGE_LABELS.get(p['stage'] or '', 'not recorded'))}"
                f" · aliases: {esc(', '.join(x['alias'] for x in aliases))}</p>")
        body += ui.table(ui.FACT_HEADERS, ui.fact_rows(rows), "No current records for this project.")
        return self._send(200, ui.page(p["name"], body, a, company=c))

    def v_documents(self, a, cid, **_):
        st, csrf = self.st, self._csrf()
        c = self._company(a, cid)
        rows = []
        for d in [d for d in st.find(a, "documents", order="created_at") if d["company_id"] == cid]:
            for v in st.find(a, "document_versions", document_id=d["id"], order="version_no"):
                run = (st.find(a, "ingestion_runs", version_id=v["id"], order="created_at") or [None])[-1]
                status = esc(run["status"]) if run else "—"
                if run and run["error"]:
                    status += f'<br><span class="note">{esc(run["error"])}</span>'
                if v["mirror_of_version_id"]:
                    status += f'<br>mirror of <a href="/doc/{esc(v["mirror_of_version_id"])}">another release</a> ' \
                              f'(similarity {esc(v["mirror_similarity"])}); not extracted, not corroboration'
                if v["unreadable_pages"]:
                    status += f'<br>unreadable pages: {esc(", ".join(map(str, v["unreadable_pages"])))}'
                rows.append([f'<a href="/doc/{esc(v["id"])}">{esc(d["title"])}</a>', esc(d["doc_type"]), esc(d["publisher"]),
                             f"v{v['version_no']}", esc(v["publication_date"] or "undated"), esc(v["retrieved_at"]),
                             f'<span class="note">{esc(v["sha256"][:16])}…</span>', esc(v["parse_status"]), status,
                             str(run["candidates"]) if run else "—"])
        body = ui.table(["Document", "Type", "Publisher", "Version", "Published", "Retrieved", "SHA-256", "Parse",
                         "Ingestion", "Candidates"], rows, "No documents uploaded.")
        if a.can("write"):
            body += "<h2>Upload</h2>" + _upload_form(csrf, cid, f"/company/{cid}/documents")
            body += ui.form("/api/ingest.retry", "", csrf, "Retry failed ingestion runs", f"/company/{cid}/documents")
        return self._send(200, ui.page(f"{c['name']} — documents", body, a, company=c))

    def v_doc(self, a, vid, q, one, **_):
        st, csrf = self.st, self._csrf()
        v = st.get(a, "document_versions", vid)
        d = st.get(a, "documents", v["document_id"])
        c = st.get(a, "companies", d["company_id"]) if d["company_id"] else None
        st.audit(a, "document_viewed", vid)
        loc = st.get(a, "source_locations", one("loc")) if one("loc") else None
        if loc and loc["version_id"] != vid:
            raise NotFound("location")
        pages = st.find(a, "pages", version_id=vid, order="page_no")
        tables = st.find(a, "doc_tables", version_id=vid, order="table_index")
        meta = ui.table(["Field", "Value"], [[k, esc(x)] for k, x in [
            ("Title", d["title"]), ("Publisher", d["publisher"]), ("Type", d["doc_type"]),
            ("Issuer primary document", "yes" if d["is_issuer_primary"] else "no"), ("Version", v["version_no"]),
            ("File", v["filename"]), ("SHA-256", v["sha256"]), ("Bytes", v["size_bytes"]),
            ("Publication date", v["publication_date"] or "undated"), ("Retrieved / uploaded", v["retrieved_at"]),
            ("Parse status", v["parse_status"]), ("Warnings", "; ".join(v["parse_warnings"])),
            ("Unreadable pages", ", ".join(map(str, v["unreadable_pages"])) or "none"),
            ("Mirror of", v["mirror_of_version_id"] or "—"), ("Synthetic", "yes" if v["synthetic"] else "no")]])
        body = meta + f'<p><a href="/doc/{esc(vid)}/original">Download original bytes</a></p>'
        body += ('<p class="note">Document text is untrusted data. It is displayed and searched; instructions inside '
                 'it are never followed.</p>')
        if loc:
            body += (f'<h2 id="loc">Cited location</h2><p>Page {loc["page_no"]}'
                     + (f", table {loc['table_index'] + 1}, row {loc['row_index'] + 1}, column {loc['col_index'] + 1}"
                        f"{(' (' + loc['cell_ref'] + ')') if loc['cell_ref'] else ''} — row '{esc(loc['row_header'])}', "
                        f"column '{esc(loc['col_header'])}'" if loc["table_index"] is not None else
                        f", characters {loc['char_start']}–{loc['char_end']}") +
                     f'</p><blockquote>{esc(loc["quote"])}</blockquote>'
                     f'<p class="note">Context: {esc(loc["context"][:600])}</p>'
                     f'<p class="note">Coordinates: {esc(loc["bbox"]) if loc["bbox"] else "none"} — {esc(loc["bbox_note"])}</p>')
        lf = [f for f in st.find(a, "facts", version_id=vid)]
        body += "<h2>Records extracted from this version</h2>" + ui.table(
            ui.FACT_HEADERS, ui.fact_rows(sorted(lf, key=lambda f: f["created_at"])), "None.")
        for p in pages:
            txt = p["text"]
            if loc and loc["page_no"] == p["page_no"] and loc["char_start"] is not None:
                shown = esc(txt[:loc["char_start"]]) + "<mark>" + esc(txt[loc["char_start"]:loc["char_end"]]) + \
                        "</mark>" + esc(txt[loc["char_end"]:])
            else:
                shown = esc(txt)
            body += f"<h2>Page {p['page_no']}{(' — ' + esc(p['label'])) if p['label'] else ''}</h2>"
            if not p["readable"]:
                body += "<p><b>No usable text layer on this page (scanned image). It was not read; a person must read it.</b></p>"
            else:
                body += f'<pre class="page">{shown}</pre>'
            if v["filename"].lower().endswith(".pdf"):
                body += (f'<details><summary>Page image for checking</summary><img alt="page {p["page_no"]} image" '
                         f'src="/doc/{esc(vid)}/page/{p["page_no"]}.png" style="max-width:100%;border:1px solid #ccc"></details>')
            for t in [t for t in tables if t["page_no"] == p["page_no"]]:
                rws = []
                for ri, r in enumerate(t["rows"]):
                    cells = []
                    for ci, cell in enumerate(r):
                        hit = loc and loc["table_index"] == t["table_index"] and loc["row_index"] == ri and loc["col_index"] == ci
                        cells.append(f"<mark>{esc(cell)}</mark>" if hit else esc(cell))
                    rws.append(cells)
                body += f"<h3>Table {t['table_index'] + 1}: {esc(t['title'])}</h3>" + \
                        ("<table>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rws) + "</table>") + \
                        ("<p class=\"note\">Footnotes: " + esc(" | ".join(t["footnotes"])) + "</p>" if t["footnotes"] else "")
        if a.can("write"):
            body += "<h2>Cite a passage</h2>" + ui.form("/api/cite", ui.hid("version_id", vid) +
                                                       ui.inp("page_no", "Page", "1", size=4) + ui.ta("quote", "Exact text"),
                                                       csrf, "Create citation", f"/doc/{vid}?loc={{id}}#loc")
        return self._send(200, ui.page(d["title"], body, a, company=c))

    def v_page_png(self, a, vid, n, **_):
        st = self.st
        v = st.get(a, "document_versions", vid)          # tenant check first
        key = (a.tenant_id, vid, int(n))
        png = self.app.png_cache.get(key)
        if png is None:
            png = parsers.render_page_png(ingest.read_blob(st, a, vid), int(n))
            self.app.png_cache[key] = png
        return self._send(200, png, "image/png")

    def v_original(self, a, vid, **_):
        st = self.st
        v = st.get(a, "document_versions", vid)
        data = ingest.read_blob(st, a, vid)
        st.audit(a, "document_downloaded", vid)
        return self._send(200, data, "application/octet-stream",
                          [("Content-Disposition", f'attachment; filename="{v["filename"]}"')])

    def v_fact(self, a, fid, **_):
        st, csrf = self.st, self._csrf()
        det = F.detail(st, a, fid)
        f = det["fact"]
        c = st.get(a, "companies", f["company_id"])
        rows = [[esc(k), esc(v)] for k, v in [
            ("Metric", f"{det['definition']['label']} (definition v{f['definition_version']})"),
            ("Definition", det["definition"]["definition"]), ("Caution", det["definition"]["caution"]),
            ("Printed value", f["raw_value"]), ("Normalised value", f"{f['normalized_value']} {f['unit'] or ''}"),
            ("Implied precision", f"{f['precision_lo']} – {f['precision_hi']}"), ("Currency", f["currency"]),
            ("Transformations", " | ".join(f["transformations"]) or "none"), ("Qualifiers", ui.qualifiers_text(f)),
            ("As-of / effective / period", f"{f['as_of_date']} / {f['effective_date']} / {f['period_start']}–{f['period_end']}"),
            ("Published / retrieved", f"{f['publication_date']} / {f['retrieved_at']}"),
            ("Attribution", D.ATTRIBUTIONS[f["attribution"]]), ("Evidence type", D.EVIDENCE_TYPES[f["evidence_type"]]),
            ("Workflow state", D.WORKFLOW_STATES[f["workflow_state"]]), ("Missing information", f["missing_reason"] or "—"),
            ("Extractor", f"{f['extractor']} {f['extractor_version']}"), ("Revision of", f["revision_of"] or "—"),
            ("Relation", f["relation"] or "—"), ("Corroboration", det["corroboration_note"])]]
        body = ui.table(["Field", "Value"], rows)
        body += f'<p>{ui.src_link(f)}</p><blockquote>{esc(f["raw_text"])}</blockquote>'
        body += "<h2>Automated checks</h2>" + ui.table(["Check", "Result", "Detail"], [
            [esc(x["check"]), esc(x["status"]), esc(x["detail"])] for x in f["checks"]])
        body += "<h2>Review history</h2>" + ui.table(["When", "Who", "Decision", "From → to", "Reason"], [
            [esc(r["at"]), esc(r["actor"]), esc(r["decision"]), esc(f"{r['from_state']} → {r['to_state']}"), esc(r["reason"])]
            for r in det["reviews"]])
        body += "<h2>Revisions</h2>" + ui.table(["Fact", "Value", "State", "Relation"], [
            [f'<a href="/fact/{esc(x["id"])}">{esc(x["id"])}</a>', ui.fact_value(x), ui.state_word(x["workflow_state"]),
             esc(x["relation"] or "")] for x in det["earlier_revisions"] + det["later_revisions"]], "No other revisions.")
        body += "<h2>Downstream outputs using this record</h2>" + ui.table(["Kind", "Id"], [
            [esc(x["kind"]), esc(x["id"])] for x in det["dependents"]], "None.")
        if f["workflow_state"] not in ("superseded",):
            if a.can("review") and f["workflow_state"] != "rejected":
                body += "<h2>Review</h2>" + ui.form("/api/fact.review", ui.hid("fact_id", fid) +
                                                    ui.sel("decision", "Decision", [("approve", "Approve — matches source"),
                                                                                    ("reject", "Reject"),
                                                                                    ("needs_review", "Needs further review")]) +
                                                    ui.inp("reason", "Reason", size=60), csrf, "Record decision", f"/fact/{fid}")
            if a.can("write"):
                projs = entities.projects_of(st, a, f["company_id"])
                body += "<h2>Correct (creates a new revision; a different reviewer approves it)</h2>" + ui.form(
                    "/api/fact.correct", ui.hid("fact_id", fid) + ui.inp("raw_value", "Corrected printed value", f["raw_value"] or "") +
                    ui.sel("project_id", "Project", [("", "(unchanged)")] + [(p["id"], p["name"]) for p in projs]) +
                    ui.inp("reason", "Reason (required)", size=60, required=True), csrf, "Create corrected revision",
                    "/fact/{id}")
        return self._send(200, ui.page(f"Record: {det['definition']['label']}", body, a, company=c))

    def v_review(self, a, q, one, **_):
        st, csrf = self.st, self._csrf()
        states = ("candidate", "needs_review", "source_matched")
        rows = []
        for f in sorted([f for f in st.find(a, "facts") if f["workflow_state"] in states],
                        key=lambda f: (f["workflow_state"] != "needs_review", f["company_id"], f["metric_id"])):
            c = st.get(a, "companies", f["company_id"])
            issues = "<br>".join(esc(f"{x['check']}: {x['detail']}") for x in f["checks"] if x["status"] != "pass") or "all automated checks passed"
            act = ""
            if a.can("review") and f["created_by"] != a.user_id and f["normalized_value"] is not None:
                act = ui.form("/api/fact.review", ui.hid("fact_id", f["id"]) + ui.hid("decision", "approve") +
                              ui.hid("reason", "matches source (queue review)"), csrf, "Approve", "/review", inline=True)
            act += f' <a href="/fact/{esc(f["id"])}">open</a>'
            rows.append([esc(c["name"]), esc(D.metric(f["metric_id"]).label), ui.fact_value(f), ui.qualifiers_text(f),
                         ui.state_word(f["workflow_state"]), issues,
                         f'<q class="src">{esc(f["raw_text"][:200])}</q>{ui.src_link(f)}', act])
        body = ('<p class="note">Extraction proposes; checks re-derive; a reviewer decides. Approval means the record '
                'matches its source — not that the underlying claim is independently true.</p>')
        body += ui.table(["Company", "Metric", "Value", "Qualifiers", "State", "Open checks", "Source", "Action"], rows,
                         "Nothing awaiting review.")
        return self._send(200, ui.page("Extraction review queue", body, a))

    def v_discrepancies(self, a, **_):
        st = self.st
        rows = []
        for d in st.find(a, "discrepancies", order="created_at DESC"):
            c = st.get(a, "companies", d["company_id"])
            rows.append([f'<a href="/discrepancy/{esc(d["id"])}">{esc(d["kind"].replace("_", " "))}</a>', esc(c["name"]),
                         esc(d["detail"]), esc(d["status"]), esc(d["resolution"])])
        return self._send(200, ui.page("Discrepancies", ui.table(["Kind", "Company", "Detail", "Status", "Resolution"], rows,
                                                                 "No discrepancies."), a))

    def v_discrepancy(self, a, did, **_):
        st, csrf = self.st, self._csrf()
        d = st.get(a, "discrepancies", did)
        cols = []
        for side in ("fact_a", "fact_b"):
            if not d[side]:
                continue
            det = F.detail(st, a, d[side])
            f = det["fact"]
            cols.append(f"<div><h2>{esc(det['document']['title'] if det['document'] else 'no source')}</h2>"
                        f"<p>Published {esc(det['version']['publication_date'] if det['version'] else '')} · "
                        f"{esc(det['document']['publisher'] if det['document'] else '')} · page "
                        f"{esc(det['location']['page_no'] if det['location'] else '')}</p>"
                        f"<p><b>{ui.fact_value(f)}</b> — {ui.qualifiers_text(f)} — {ui.fact_date(f)} — "
                        f"{ui.state_word(f['workflow_state'])}</p>"
                        f"<blockquote>{esc(det['location']['context'][:800] if det['location'] else f['raw_text'])}</blockquote>"
                        f'<p><a href="/fact/{esc(f["id"])}">record</a> · {ui.src_link(f)}</p></div>')
        body = f"<p>{esc(d['detail'])} — status {esc(d['status'])}</p><div class=\"cols\">{''.join(cols)}</div>"
        if d["status"] == "open" and a.can("review"):
            opts = [("", "(record the resolution only)")] + [(d[s], f"keep {s[-1].upper()} ({d[s]})") for s in ("fact_a", "fact_b") if d[s]]
            body += ui.form("/api/discrepancy.resolve", ui.hid("discrepancy_id", did) + ui.sel("keep_fact_id", "Decision", opts) +
                            ui.ta("resolution", "Resolution and reasons (required)"), csrf, "Resolve", f"/discrepancy/{did}")
        c = st.get(a, "companies", d["company_id"])
        return self._send(200, ui.page("Discrepancy", body, a, company=c))

    def v_risks(self, a, cid, **_):
        st, csrf = self.st, self._csrf()
        c = self._company(a, cid)
        body = ('<p class="note">No risk scores and no high/medium/low grades. An open question is not an adverse '
                'finding. Items marked for attention carry the analyst\'s reason.</p>')
        for r in risks.register(st, a, cid):
            ev = lambda stance: "".join(
                f"<li>{esc(e['evidence_date'] or '')} — {esc(e['note'])} "
                + (f'<a href="/fact/{esc(e["fact_id"])}">fact</a>' if e["fact_id"] else "")
                + (f' <a href="/doc/{esc(st.get(a, "source_locations", e["location_id"])["version_id"])}?loc={esc(e["location_id"])}#loc">source</a>'
                   if e["location_id"] else "") + "</li>" for e in r["evidence"] if e["stance"] == stance) or "<li class=\"missing\">none recorded</li>"
            body += (f"<details open><summary>{esc(r['title'])} — {esc(D.RISK_CATEGORIES[r['category']])} — "
                     f"{esc(D.RISK_STATUSES[r['status']].split(' —')[0])}</summary>"
                     + (f"<p><b>Marked for attention:</b> {esc(r['attention_reason'])}</p>" if r["attention"] else "")
                     + ui.table(["Field", "Text"], [[k, esc(r[f]) or ui.missing("not recorded")] for k, f in [
                         ("Potential consequence", "consequence"), ("Dependencies / conditions", "dependencies_text"),
                         ("Mitigants", "mitigants"), ("Unresolved questions", "unresolved_questions"),
                         ("Monitoring trigger", "monitoring_trigger"), ("Owner", "owner"), ("Reviewer", "reviewer"),
                         ("Origin", "origin")]])
                     + f"<h3>Supporting evidence</h3><ul>{ev('supporting')}</ul><h3>Contrary evidence</h3><ul>{ev('contrary')}</ul>")
            if a.can("write"):
                body += ui.form("/api/risk.evidence", ui.hid("risk_id", r["id"]) +
                                ui.sel("stance", "Stance", [("supporting", "Supporting"), ("contrary", "Contrary")]) +
                                ui.inp("fact_id", "Fact id") + ui.inp("location_id", "or citation (location) id") +
                                ui.inp("note", "Note", size=50), csrf, "Add evidence", f"/risks/{cid}")
                body += ui.form("/api/risk.attention", ui.hid("risk_id", r["id"]) +
                                ui.sel("attention", "Attention", [("1", "Requires attention"), ("0", "No attention flag")]) +
                                ui.inp("reason", "Reason", size=50), csrf, "Set", f"/risks/{cid}")
                body += ui.form("/api/risk.status", ui.hid("risk_id", r["id"]) +
                                ui.sel("status", "Status", list((k, v.split(' —')[0]) for k, v in D.RISK_STATUSES.items())) +
                                ui.inp("reason", "Reason", size=50), csrf, "Change status", f"/risks/{cid}")
            body += "<h3>History</h3>" + ui.table(["When", "Who", "Change"], [
                [esc(h["at"]), esc(h["actor"]), esc(json.dumps(h["change"]))] for h in r["history"]]) + "</details>"
        if a.can("write"):
            body += "<h2>Record a risk or open question</h2>" + ui.form(
                "/api/risk.create", ui.hid("company_id", cid) +
                ui.sel("category", "Category", list(D.RISK_CATEGORIES.items())) + ui.inp("title", "Neutral title", size=80, required=True) +
                ui.ta("consequence", "Potential consequence") + ui.ta("dependencies_text", "Dependencies / conditions") +
                ui.ta("mitigants", "Mitigants") + ui.ta("unresolved_questions", "Unresolved questions") +
                ui.inp("monitoring_trigger", "Monitoring trigger", size=60), csrf, "Create", f"/risks/{cid}")
        return self._send(200, ui.page(f"{c['name']} — risk register", body, a, company=c))

    def v_diligence(self, a, cid, **_):
        st, csrf = self.st, self._csrf()
        c = self._company(a, cid)
        items = st.find(a, "diligence_items", company_id=cid, order="item_key")
        body = f"<p><b>{esc(diligence.checklist_status_label(items))}</b></p>"
        rows = []
        for it in items:
            act = ""
            if a.can("review") and it["status"] != "reviewed":
                act = ui.form("/api/diligence.review_item", ui.hid("item_id", it["id"]) + ui.inp("notes", "Notes", size=30),
                              csrf, "Mark reviewed", f"/diligence/{cid}", inline=True)
            rows.append([esc(it["title"]), esc(it["specialist"]), esc(it["status"].replace("_", " ")),
                         ", ".join(f'<a href="/fact/{esc(x)}">{esc(x[-6:])}</a>' for x in it["evidence"]) or ui.missing("none"),
                         esc(it["notes"]) + (f" ({esc(it['reviewed_by'])})" if it["reviewed_by"] else ""), act])
        body += ui.table(["Item", "Specialist", "Status", "Evidence", "Notes", "Action"], rows, "No checklist yet.")
        if a.can("write"):
            projs = entities.projects_of(st, a, cid)
            body += ui.form("/api/diligence.build", ui.hid("company_id", cid) +
                            ui.sel("project_id", "Project (stage sets the template)", [(p["id"], p["name"]) for p in projs]),
                            csrf, "Build / refresh stage-aware checklist", f"/diligence/{cid}")
        qs = st.find(a, "diligence_questions", company_id=cid, order="created_at")
        body += "<h2>Specialist questions and document requests</h2>" + ui.table(
            ["Question", "Specialist", "Document request", "Status", "Origin"],
            [[esc(x["question"]), esc(x["specialist"]), esc(x["document_request"]), esc(x["status"]), esc(x["origin"])] for x in qs])
        if a.can("write"):
            body += ui.form("/api/diligence.question", ui.hid("company_id", cid) + ui.inp("question", "Question", size=80) +
                            ui.inp("specialist", "Specialist") + ui.inp("document_request", "Document request", size=50),
                            csrf, "Add question", f"/diligence/{cid}")
        com = diligence.commitment_view(st, a, cid)
        body += "<h2>Management commitments (attributed, conditional statements)</h2>" + ui.table(
            ["Original wording", "Stated", "Target", "Window", "Status", "Updates"],
            [[f'<q class="src">{esc(x["original_wording"])}</q>', esc(x["stated_on"]), esc(x["target_text"]),
              esc(f"{x['target_window_start'] or '?'} – {x['target_window_end'] or '?'} ({x['window_note']})"),
              esc(x["display_status"]), "<br>".join(esc(f"{u['kind']}: {u['wording']}") for u in x["updates"]) or "—"]
             for x in com])
        return self._send(200, ui.page(f"{c['name']} — diligence", body, a, company=c))

    def v_peers(self, a, cid, **_):
        st, csrf = self.st, self._csrf()
        c = self._company(a, cid)
        projs = entities.projects_of(st, a, cid)
        body = ""
        for p in projs:
            cands = peers.generate_candidates(st, a, cid, p["id"])
            body += f"<h2>Candidate comparators for {esc(p['name'])}</h2>" + ui.table(
                ["Company / project", "Classification", "Why included", "Differences / limitations"],
                [[esc(f"{x['company']} — {x['project']}"), esc(x["classification"].replace("_", " ")),
                  "<br>".join(esc(r) for r in x["inclusion_reasons"]), "<br>".join(esc(r) for r in x["differences"])]
                 for x in cands], "No other companies in this workspace.")
            if a.can("write"):
                body += ui.form("/api/peerset.create", ui.hid("company_id", cid) + ui.hid("project_id", p["id"]) +
                                ui.inp("name", "Peer set name", f"{p['name']} peers", size=50), csrf,
                                "Create peer set from these candidates", "/peerset/{id}")
        sets = st.find(a, "peer_sets", subject_company_id=cid, order="created_at")
        body += "<h2>Peer sets</h2>" + ui.table(["Name", "Status", "Approved"], [
            [f'<a href="/peerset/{esc(s["id"])}">{esc(s["name"])}</a>', esc(s["status"]),
             esc(f"{s['approved_by'] or ''} {s['approved_at'] or ''}")] for s in sets])
        return self._send(200, ui.page(f"{c['name']} — peers", body, a, company=c))

    def v_peerset(self, a, sid, **_):
        st, csrf = self.st, self._csrf()
        s = st.get(a, "peer_sets", sid)
        c = st.get(a, "companies", s["subject_company_id"])
        rows = []
        for m in st.find(a, "peer_members", peer_set_id=sid):
            co = st.get(a, "companies", m["company_id"])
            act = ""
            if a.can("write") and s["status"] == "draft":
                act = ui.form("/api/peer.decide", ui.hid("member_id", m["id"]) +
                              ui.sel("decision", "Decision", [("approved", "Approve"), ("excluded", "Exclude")]) +
                              ui.sel("classification", "Classification", [("", "(keep)"), ("strict_peer", "strict peer"),
                                                                          ("broader_comparator", "broader comparator")]) +
                              ui.inp("rationale", "Rationale (required)", size=40), csrf, "Record", f"/peerset/{sid}")
            rows.append([esc(co["name"]), esc(m["classification"].replace("_", " ")),
                         "<br>".join(esc(x) for x in m["inclusion_reasons"]), "<br>".join(esc(x) for x in m["differences"]),
                         esc(m["decision"]) + (f"<br>{esc(m['decision_rationale'])} ({esc(m['decided_by'])})" if m["decided_by"] else ""),
                         act])
        body = f"<p>Status: <b>{esc(s['status'])}</b> {esc(s['approval_rationale'])}</p>"
        body += ui.table(["Company", "Classification", "Why included", "Differences", "Decision", "Action"], rows)
        if a.can("write") and s["status"] == "draft":
            body += ui.form("/api/peerset.approve", ui.hid("peer_set_id", sid) + ui.inp("rationale", "Approval rationale", size=60),
                            csrf, "Approve peer set", f"/peerset/{sid}")
        if s["status"] == "approved":
            if a.can("write"):
                body += ui.form("/api/snapshot.build", ui.hid("peer_set_id", sid) +
                                ui.inp("market_data_date", "Market-data date (YYYY-MM-DD)", config.today().isoformat()),
                                csrf, "Build comparison snapshot", "/snapshot/{id}")
            snaps = st.find(a, "comparison_snapshots", peer_set_id=sid, order="created_at DESC")
            body += "<h2>Snapshots</h2>" + ui.table(["Snapshot", "Market-data date", "Built", "Stale"], [
                [f'<a href="/snapshot/{esc(x["id"])}">{esc(x["id"])}</a>', esc(x["market_data_date"]), esc(x["created_at"]),
                 esc(x["stale_reason"]) if x["stale"] else "no"] for x in snaps])
        return self._send(200, ui.page(f"Peer set: {s['name']}", body, a, company=c))

    def v_snapshot(self, a, sid, q, one, **_):
        st = self.st
        s = st.get(a, "comparison_snapshots", sid)
        b = s["body"]
        ps = st.get(a, "peer_sets", s["peer_set_id"])
        c = st.get(a, "companies", ps["subject_company_id"])
        rows = b["rows"]
        sort_note = b["method"]["ordering"]
        if one("sort") in dict(b["metric_rows"]):
            rows, sort_note = peers.sort_rows(rows, one("sort"), one("desc") == "1")
        heads = ["Company / project", "Role"] + [
            f'{esc(label)} <a title="sort ascending" href="/snapshot/{esc(sid)}?sort={k}">↑</a> '
            f'<a title="sort descending" href="/snapshot/{esc(sid)}?sort={k}&amp;desc=1">↓</a>'
            for k, label in b["metric_rows"]]
        trs = []
        for r in rows:
            cells = []
            for k, _ in b["metric_rows"]:
                x = r["cells"].get(k, {})
                if x.get("status") in ("computed", "reported"):
                    extra = ""
                    if x.get("study_type"):
                        extra = f"<br><span class=\"note\">{esc(x['study_type'].upper())}, effective {esc(x.get('effective_date'))}</span>"
                    if x.get("calc_id"):
                        extra += f' <a href="/calc/{esc(x["calc_id"])}">calc</a>'
                    if x.get("fact_id"):
                        extra += f' <a href="/fact/{esc(x["fact_id"])}">fact</a>'
                    cells.append(f'<span class="num">{esc(x["display"])}</span>{extra}')
                else:
                    cells.append(f'<span class="withheld">Withheld: {esc(x.get("reason", ""))}</span>')
            trs.append([esc(f"{r['company']} — {r['project']}") + f"<br><span class=\"note\">{esc(r['stage'])}, {esc(r['jurisdiction'])}</span>",
                        esc(r["role"]) + ("<br>" + esc(r["classification"].replace("_", " ")) if r["role"] != "subject" else "")]
                       + cells)
        banner = (f"STALE: {s['stale_reason']}" if s["stale"] else None)
        body = (f"<p>Market-data date <b>{esc(b['market_data_date'])}</b> (one date for every company) · analysis "
                f"{esc(b['analysis_time'])} · peer set approved by {esc(b['method']['approval']['approved_by'])} "
                f"on {esc((b['method']['approval']['approved_at'] or '')[:10])}</p><p class=\"note\">{esc(sort_note)}</p>")
        body += ui.table(heads, trs, raw_headers=True).replace("<table>", '<table class="wide">', 1)
        body += "<details><summary>Method, definitions and assumptions</summary><ul>" + "".join(
            f"<li><b>{esc(k)}</b>: {esc(v)}</li>" for k, v in b["method"]["formulas"].items()) + "</ul>"
        body += "<ul>" + "".join(f"<li><b>{esc(r['company'])}</b>: included because " + esc("; ".join(r["reasons"]) or "subject") +
                                 (f" — analyst rationale: {esc(r['rationale'])}" if r.get("rationale") else "") + "</li>" for r in rows) + "</ul>"
        body += "<p>Excluded: " + (esc("; ".join(f"{x['company']} ({x['rationale']})" for x in b["excluded"])) or "none") + "</p></details>"
        body += "<h2>Comparability notes</h2><ul>" + "".join(
            f"<li>{esc(dict(b['metric_rows']).get(k, k))}: {esc(n)}</li>" for k, ns in b["comparability"].items() for n in ns) + "</ul>"
        body += "<h2>Observations on specified measures</h2><ul>" + "".join(f"<li>{esc(o)}</li>" for o in b["observations"]) + "</ul>"
        ex = b["explanations"]
        body += "<h2>What could explain the differences</h2>"
        for k, title in (("subject_disadvantages_that_could_explain_a_discount", "Subject characteristics that could explain a discount"),
                         ("peer_characteristics_that_could_justify_a_premium", "Peer characteristics that could justify a premium"),
                         ("missing_evidence_that_could_change_the_comparison", "Missing evidence that could change the comparison")):
            body += f"<h3>{esc(title)}</h3><ul>" + ("".join(f"<li>{esc(x)}</li>" for x in ex[k]) or "<li class=\"missing\">none recorded</li>") + "</ul>"
        body += f'<p><a href="/export/snapshot/{esc(sid)}.csv">Export snapshot (CSV)</a></p>'
        return self._send(200, ui.page(f"Comparison: {b['peer_set_name']}", body, a, company=c, notice=banner))

    def v_calcs(self, a, cid, **_):
        st, csrf = self.st, self._csrf()
        c = self._company(a, cid)
        allc = st.find(a, "calculations", company_id=cid, order="created_at DESC")
        latest, seen = [], set()
        for x in allc:
            k = (x["formula_id"], x["label"])
            if k not in seen:
                seen.add(k)
                latest.append(x)
        body = ('<p class="note">Deterministic, versioned formulas on reviewer-approved inputs. Missing inputs withhold '
                'the result. No price targets.</p>')
        if a.can("write"):
            body += ui.form("/api/calc.run", ui.hid("company_id", cid), csrf, "Run standard calculations", f"/calcs/{cid}")
        body += ui.table(["Calculation", "Result", "Inputs (source records)", "Warnings and caveats"], ui.calc_rows(latest),
                         "No calculations run yet.")
        asm = [x for x in st.find(a, "assumptions", order="created_at DESC") if x["company_id"] in (cid, None)]
        body += "<h2>Assumptions</h2>" + ui.table(["Name", "Value", "Unit", "As of", "Source", "Rationale", "By", "Superseded"], [
            [esc(x["name"]), esc(x["value"]), esc(x["unit"]), esc(x["as_of_date"]), esc(x["source"]), esc(x["rationale"]),
             esc(x["created_by"]), esc(x["superseded_by"] or "")] for x in asm])
        if a.can("write"):
            body += ui.form("/api/assumption.set", ui.sel("company_id", "Applies to", [(cid, c["name"]), ("", "all companies")]) +
                            ui.sel("name", "Assumption", [("fx_usd_cad", "FX: CAD per USD"), ("fx_cad_usd", "FX: USD per CAD"),
                                                          ("monthly_spend", "Monthly spend"), ("corporate_costs_pv", "Corporate costs (PV)"),
                                                          ("funding_dilution_adjustment", "Funding / dilution adjustment")]) +
                            ui.inp("value", "Value") + ui.inp("unit", "Unit") + ui.inp("as_of_date", "As of (YYYY-MM-DD)") +
                            ui.inp("source", "Source (required for FX)", size=40) + ui.inp("rationale", "Rationale (required)", size=60),
                            csrf, "Record assumption", f"/calcs/{cid}")
        return self._send(200, ui.page(f"{c['name']} — calculations", body, a, company=c))

    def v_calc(self, a, kid, **_):
        st = self.st
        x = st.get(a, "calculations", kid)
        c = st.get(a, "companies", x["company_id"]) if x["company_id"] else None
        rep = calc.recompute(st, a, kid)
        f = calc.FORMULAS[x["formula_id"]]
        body = ui.table(["Calculation", "Result", "Inputs (source records)", "Warnings and caveats"], ui.calc_rows([x]))
        body += ui.table(["Field", "Value"], [[k, esc(v)] for k, v in [
            ("Formula", f"{f.id} v{f.version}: {f.expression}"), ("Definition", f.definition), ("Rounding", calc.ROUNDING),
            ("Stored output", x["output_value"]), ("Reproduction", json.dumps(rep)), ("Parameters", json.dumps(x["parameters"]))]])
        return self._send(200, ui.page(x["label"], body, a, company=c))

    def v_memos(self, a, cid, **_):
        st, csrf = self.st, self._csrf()
        c = self._company(a, cid)
        rows = []
        for m in st.find(a, "memos", company_id=cid, order="created_at"):
            vs = st.find(a, "memo_versions", memo_id=m["id"], order="version_no")
            rows.append([f'<a href="/memo/{esc(m["id"])}">{esc(m["title"])}</a>', "<br>".join(
                esc(f"v{v['version_no']}: {v['status']}" + (" (stale)" if v["stale"] else "")) for v in vs)])
        body = ui.table(["Memo", "Versions"], rows, "No memos yet.")
        theses = st.find(a, "theses", company_id=cid)
        sets = [s for s in st.find(a, "peer_sets", subject_company_id=cid) if s["status"] == "approved"]
        if a.can("write"):
            body += "<h2>Record a thesis (with counter-thesis and tracked assumptions)</h2>" + ui.form(
                "/api/thesis.create", ui.hid("company_id", cid) + ui.inp("title", "Title", size=60, required=True) +
                ui.ta("thesis_text", "Thesis") + ui.ta("counter_thesis_text", "Counter-thesis (required)") +
                ui.inp("assumption_text", "Assumption to track", size=70) +
                ui.sel("assumption_metric", "Metric it depends on", [("", "(none)")] + [(k, v.label) for k, v in D.METRICS.items()]),
                csrf, "Record thesis", f"/memos/{cid}")
            body += "<h2>Draft a memo</h2>" + ui.form(
                "/api/memo.create", ui.hid("company_id", cid) + ui.inp("title", "Title", f"{c['name']} — investment memo", size=60) +
                ui.sel("thesis_id", "Thesis", [("", "(none)")] + [(t["id"], t["title"]) for t in theses]) +
                ui.sel("peer_set_id", "Approved peer set", [("", "(none)")] + [(s["id"], s["name"]) for s in sets]),
                csrf, "Draft memo from approved records", "/memo/{id}")
        return self._send(200, ui.page(f"{c['name']} — memos", body, a, company=c))

    def v_memo(self, a, mid, q, one, **_):
        st, csrf = self.st, self._csrf()
        m = st.get(a, "memos", mid)
        c = st.get(a, "companies", m["company_id"])
        vs = st.find(a, "memo_versions", memo_id=mid, order="version_no")
        v = next((x for x in vs if x["id"] == one("v")), vs[-1])
        r = M.render(st, a, v["id"])
        body = ui.coverage_block({"analysis_time": r["analysis_time"], "evidence_cutoff": r["evidence_cutoff"],
                                  "documents_reviewed": r["coverage"]["documents"]})
        body += f'<p class="note">{esc(r["notice"])}</p>'
        body += "<p>Versions: " + " · ".join(f'<a href="/memo/{esc(mid)}?v={esc(x["id"])}">v{x["version_no"]} {esc(x["status"])}'
                                             f'{" (stale)" if x["stale"] else ""}</a>' for x in vs) + "</p>"
        if r["unresolved"]:
            body += "<h2>Unresolved items</h2><ul>" + "".join(f"<li>{esc(u)}</li>" for u in r["unresolved"]) + "</ul>"
        for s in r["sections"]:
            body += f"<h2>{esc(s['title'])}</h2>"
            if not s["items"]:
                body += ui.missing("nothing recorded")
            for it in s["items"]:
                val = it.get("validation", {})
                state = f"{it['kind']}" + (f" · {val.get('status')}" if val else "") + f" · review: {it['review'].get('status')}"
                body += f"<p><b>[{esc(it['id'])}]</b> {esc(it['text'])} <span class=\"note\">({esc(state)})</span></p>"
                if it.get("changed_since_approval"):
                    body += ("<p class=\"note\"><b>Changed since approval (content unchanged):</b> "
                             + esc("; ".join(it["changed_since_approval"])) + "</p>")
                for e in it["evidence"]:
                    if "fact_id" in e:
                        body += (f'<blockquote>{esc(e["quote"])}</blockquote><p class="note">{esc(e["document"])}, p.{esc(e["page"])} · '
                                 f'{esc(e["state"])} · <a href="/fact/{esc(e["fact_id"])}">record</a></p>')
                    elif "calc_id" in e:
                        body += f'<p class="note">calculation <a href="/calc/{esc(e["calc_id"])}">{esc(e["formula"])}</a>' \
                                f'{" — STALE" if e["stale"] else ""}</p>'
                if it.get("risk"):
                    rk = it["risk"]
                    body += (f"<p class=\"note\">{esc(rk['category'])} — {esc(rk['status'])} {esc(rk['attention'])}</p>"
                             "<p class=\"note\">Supporting: " + esc("; ".join(f"{x.get('document', '')} p.{x.get('page', '')} ({x.get('date')})"
                                                                            for x in rk["supporting"]) or "none") +
                             "<br>Contrary: " + esc("; ".join(f"{x.get('document', '')} p.{x.get('page', '')} ({x.get('date')})"
                                                             for x in rk["contrary"]) or rk.get("contrary_note", "none")) + "</p>")
                if a.can("review") and v["status"] in ("draft", "in_review") and it["kind"] in ("factual", "interpretive", "comparison") \
                        and it["review"].get("status") != "approved" and v["author"] != a.user_id:
                    body += ui.form("/api/memo.review_claim", ui.hid("version_id", v["id"]) + ui.hid("claim_id", it["id"]) +
                                    ui.hid("decision", "approved") + ui.hid("reason", "checked against cited sources"),
                                    csrf, "Approve claim", f"/memo/{mid}?v={v['id']}", inline=True)
        if r["withheld_claims"]:
            body += "<h2>Withheld claims (not part of the memo)</h2>" + ui.table(["Claim", "Text", "Why withheld"], [
                [esc(x["id"]), esc(x["text"]), esc("; ".join(x["reasons"]))] for x in r["withheld_claims"]])
        if v["status"] == "draft" and a.can("write"):
            body += "<h2>Add a claim</h2>" + ui.form(
                "/api/memo.claim", ui.hid("version_id", v["id"]) + ui.sel("section", "Section", M.SECTIONS) +
                ui.sel("kind", "Kind", [("factual", "Factual (must cite records)"), ("interpretive", "Interpretive (reviewer approval)")]) +
                ui.ta("text", "Claim text") + ui.inp("fact_ids", "Fact ids (comma separated)", size=60) +
                ui.inp("calc_ids", "Calculation ids", size=60) + ui.inp("risk_ids", "Risk ids", size=60),
                csrf, "Add claim (validated immediately)", f"/memo/{mid}?v={v['id']}")
            body += ui.form("/api/memo.submit", ui.hid("version_id", v["id"]), csrf, "Submit for review", f"/memo/{mid}?v={v['id']}")
        if v["status"] in ("draft", "in_review") and a.can("review") and v["author"] != a.user_id:
            body += ui.form("/api/memo.review_supported", ui.hid("version_id", v["id"]) +
                            ui.inp("reason", "Review note", "checked against cited sources", size=50), csrf,
                            "Approve every claim that passes validation (each recorded individually)", f"/memo/{mid}?v={v['id']}")
        if v["status"] == "in_review":
            bl = M.approval_blockers(st, a, v["id"])
            body += "<h2>Approval checks</h2>" + ("<ul>" + "".join(f"<li>{esc(x)}</li>" for x in bl) + "</ul>" if bl else
                                                  "<p>No blockers for this reviewer.</p>")
            if a.can("review") and not bl:
                body += ui.form("/api/memo.approve", ui.hid("version_id", v["id"]) + ui.inp("rationale", "Approval rationale", size=60),
                                csrf, "Approve memo version", f"/memo/{mid}?v={v['id']}")
        if v["status"] in ("approved", "superseded", "in_review") and a.can("write"):
            body += ui.form("/api/memo.new_version", ui.hid("memo_id", mid) +
                            ui.sel("refresh", "Contents", [("1", "regenerate from current approved records"), ("0", "copy this version")]),
                            csrf, "Start a new draft version", f"/memo/{mid}")
        if a.can("export"):
            body += "<p>Export this version: " + " · ".join(
                f'<a href="/export/memo/{esc(v["id"])}.{f}">{f.upper()}</a>' for f in ("pdf", "csv", "json")) + "</p>"
        notice = r["status_label"] + (" · SYNTHETIC DATA" if r["synthetic"] else "")
        return self._send(200, ui.page(r["title"], body, a, company=c, notice=notice))

    def v_ask(self, a, cid, q, one, **_):
        st = self.st
        c = self._company(a, cid)
        question = one("q")
        body = ('<form method="get"><label>Question (answered only from cited records in this workspace)<br>'
                f'<input name="q" size="80" value="{esc(question)}"></label><button>Ask</button></form>')
        if question:
            ans = answers.ask(st, a, cid, question)
            body += f"<p><b>{esc(ans['status'].replace('_', ' '))}</b> — {esc(ans.get('message', ''))}</p>"
            for ln in ans.get("answer", []):
                body += f"<p>{esc(ln['statement'])}</p><blockquote>{esc(ln['quote'])}</blockquote>" \
                        f'<p class="note"><a href="/fact/{esc(ln["fact_id"])}">record</a></p>'
            for ln in ans.get("unapproved", []):
                body += f"<p>{esc(ln['statement'])} <i>{esc(ln['caveat'])}</i></p>"
            for p in ans.get("passages", []):
                body += f'<p class="note">{esc(p["document"])}, p.{esc(p["page"])}' + (" (mirrored release)" if p["mirror"] else "") + \
                        f'</p><blockquote>{esc(p["excerpt"])}</blockquote>'
            if ans.get("document_request"):
                body += f"<p>Document that would answer this: {esc(ans['document_request'])}</p>"
            for line in ans.get("coverage", []):
                body += f'<p class="note">{esc(line)}</p>'
        return self._send(200, ui.page(f"{c['name']} — ask", body, a, company=c))

    def v_inbox(self, a, q, one, **_):
        st, csrf = self.st, self._csrf()
        allv = one("all") == "1"
        rows = []
        for e in monitoring.inbox(st, a, include_closed=allv):
            c = st.get(a, "companies", e["company_id"]) if e["company_id"] else None
            links = "<br>".join(esc(f"{l['kind']}: {l['target_id']}") for l in e["links"][:6])
            act = ""
            if a.can("write") and e["status"] == "new":
                act = ui.form("/api/event.status", ui.hid("event_id", e["id"]) +
                              ui.sel("status", "", [("reviewed", "Reviewed"), ("resolved", "Resolved"), ("dismissed", "Dismiss")]) +
                              ui.inp("reason", "Reason", size=24), csrf, "Save", "/inbox", inline=True)
            rows.append([esc(e["created_at"]), esc(c["name"] if c else "—"), esc(e["kind"].replace("_", " ")), esc(e["title"]),
                         links, esc(e["status"]) + (f"<br>{esc(e['status_reason'])}" if e["status_reason"] else ""), act])
        body = ('<p class="note">One event system feeds news, milestones, restatements and thesis changes. '
                'Notifications are in-app only.</p><p><a href="/inbox?all=1">show reviewed and dismissed</a></p>')
        body += ui.table(["When", "Company", "Kind", "Event", "Linked records", "Status", "Action"], rows, "No new events.")
        return self._send(200, ui.page("Change inbox", body, a))

    def v_portfolio(self, a, q, one, **_):
        st, csrf = self.st, self._csrf()
        name = one("name") or "Fund I"
        ex = monitoring.exposures(st, a, name)
        body = f"<p>Portfolio <b>{esc(name)}</b>. {esc(ex['note'])}</p>"
        body += ui.table(["Company", "Shares", "As of"], [[esc(st.get(a, "companies", h["company_id"])["name"]), esc(h["shares"]),
                                                          esc(h["as_of_date"])] for h in ex["holdings"]], "No holdings.")
        for dim, groups in ex["groups"].items():
            body += f"<h2>{esc(dim.replace('_', ' ').capitalize())}</h2>" + ui.table(["Exposure", "Holdings"], [
                [esc(k), "<br>".join(esc(x) for x in v)] for k, v in groups.items()], "None established.")
        body += "<h2>Not established (unknown, not absent)</h2><ul>" + "".join(f"<li>{esc(x)}</li>" for x in ex["not_established"]) + "</ul>"
        body += "<h2>Liquidity scenarios</h2>" + ui.table(["Company", "Shares", "Days at participation rates", "Notes"], [
            [esc(x["company"]), esc(x["shares"]), esc("; ".join(f"{t['participation_rate']}: {t['days']} days" for t in x["table"] or []))
             or f'<span class="withheld">Withheld: {esc("; ".join(x["missing"]))}</span>',
             esc(f"ADV as at {x['adv_date']}. " + " ".join(x["caveats"]))] for x in ex["liquidity"]])
        if a.can("write"):
            body += ui.form("/api/holding.add", ui.hid("portfolio", name) +
                            ui.sel("company_id", "Company", [(c["id"], c["name"]) for c in st.find(a, "companies", order="name")]) +
                            ui.inp("shares", "Shares") + ui.inp("as_of_date", "As of (YYYY-MM-DD)"), csrf, "Add holding",
                            f"/portfolio?name={urllib.parse.quote(name)}")
        return self._send(200, ui.page("Portfolio exposures", body, a))

    def v_definitions(self, a, **_):
        reg = D.registry()
        body = f"<p>Metric registry version {esc(reg['registry_version'])}. Not reviewed by a qualified person; not a compliance opinion.</p>"
        body += ui.table(["Metric", "Version", "Dimension", "Level", "Requires", "Definition", "Caution"], [
            [esc(m["label"]), str(m["version"]), esc(m["dimension"]), esc(m["level"]), esc(", ".join(m["requires"])),
             esc(m["definition"]), esc(m["caution"])] for m in reg["metrics"].values()])
        body += "<h2>Calculations</h2>" + ui.table(["Formula", "Version", "Expression", "Definition"], [
            [esc(f["label"]), str(f["version"]), esc(f["expression"]), esc(f["definition"])] for f in calc.definitions()["formulas"].values()])
        body += "<h2>Workflow states</h2>" + ui.table(["State", "Meaning"], [[esc(k), esc(v)] for k, v in reg["workflow_states"].items()])
        body += "<h2>Evidence types</h2>" + ui.table(["Type", "Meaning"], [[esc(k), esc(v)] for k, v in reg["evidence_types"].items()])
        return self._send(200, ui.page("Definitions", body, a))

    def v_admin_audit(self, a, **_):
        if not a.can("admin"):
            raise AccessDenied("administrative")
        chain = AU.verify_chain(self.st.db)
        rows = [[esc(e["ts"]), esc(e["actor"]), esc(e["role"]), esc(e["action"]), esc(e["target"]), esc(e["detail"][:160])]
                for e in AU.tail(self.st.db, a.tenant_id, 300)]
        body = (f"<p>Chain {'verifies over ' + str(chain['rows']) + ' events' if chain['ok'] else 'BROKEN at seq ' + str(chain.get('broken_at_seq'))}"
                ". Each row carries the SHA-256 of the previous row.</p>") + ui.table(["UTC", "Actor", "Role", "Action", "Target", "Detail"], rows)
        return self._send(200, ui.page("Audit (this tenant)", body, a))

    def v_admin_usage(self, a, **_):
        if not a.can("admin"):
            raise AccessDenied("administrative")
        st = self.st
        rows = st.db.all("SELECT kind, unit, COUNT(*) n, SUM(CAST(quantity AS REAL)) q, SUM(COALESCE(tokens_in,0)) ti, "
                         "SUM(COALESCE(tokens_out,0)) tout FROM usage_ledger WHERE tenant_id=? GROUP BY kind, unit",
                         (a.tenant_id,))
        t = st.db.one("SELECT * FROM tenants WHERE id=?", (a.tenant_id,))
        body = ui.table(["Subscription", "Plan", "Seats", "Entitlements"], [[esc(t["name"]), esc(t["plan"]), esc(t["seats"]),
                                                                             esc(t["entitlements"])]])
        body += ui.table(["Usage kind", "Unit", "Events", "Quantity", "Model tokens in", "Model tokens out"], [
            [esc(r["kind"]), esc(r["unit"]), str(r["n"]), esc(r["q"]), str(r["ti"]), str(r["tout"])] for r in rows])
        body += '<p class="note">No model provider is configured; model calls and cost are zero. Prices and limits are configuration, not validated market pricing. No payment is collected.</p>'
        return self._send(200, ui.page("Usage and subscription", body, a))

    def v_admin_users(self, a, **_):
        if not a.can("admin"):
            raise AccessDenied("administrative")
        csrf = self._csrf()
        users = self.app.auth.users(a)
        body = ui.table(["User", "Role", "Active", "Created"], [[esc(u["user_id"]), esc(u["role"]), esc(u["active"]),
                                                                esc(u["created_at"])] for u in users])
        body += ui.form("/api/user.create", ui.inp("user_id", "User id") + ui.sel("role", "Role", [(r, r) for r in ROLES]) +
                        ui.inp("password", "Initial password (12+ characters)", type="password"), csrf, "Create user", "/admin/users")
        return self._send(200, ui.page("Users", body, a))

    # ------------------------------------------------------------ exports and JSON API
    def v_export_memo(self, a, vid, fmt, **_):
        data, ctype, rec = exports.memo_export(self.st, a, vid, fmt)
        return self._send(200, data, ctype, [("Content-Disposition", f'attachment; filename="memo-{vid}.{fmt}"'),
                                             ("X-JMI-Export-SHA256", rec["sha256"])])

    def v_export_facts(self, a, cid, **_):
        data, rec = exports.facts_csv(self.st, a, cid)
        return self._send(200, data, "text/csv", [("Content-Disposition", f'attachment; filename="facts-{cid}.csv"')])

    def v_export_snapshot(self, a, sid, **_):
        data, rec = exports.snapshot_csv(self.st, a, sid)
        return self._send(200, data, "text/csv", [("Content-Disposition", f'attachment; filename="snapshot-{sid}.csv"')])

    def api_companies(self, a, **_):
        return self._json(200, {"companies": monitoring.watchlist_view(self.st, a)})

    def api_company(self, a, cid, **_):
        st = self.st
        c = st.get(a, "companies", cid)
        return self._json(200, {"company": c, "projects": entities.projects_of(st, a, cid),
                                "facts": st.find(a, "facts", company_id=cid), "coverage": monitoring.coverage_status(st, a, cid)})

    def api_fact(self, a, fid, **_):
        return self._json(200, F.detail(self.st, a, fid))

    def api_doc(self, a, vid, **_):
        st = self.st
        v = st.get(a, "document_versions", vid)
        return self._json(200, {"version": v, "document": st.get(a, "documents", v["document_id"]),
                                "pages": st.find(a, "pages", version_id=vid, order="page_no"),
                                "tables": st.find(a, "doc_tables", version_id=vid)})

    def api_blob(self, a, vid, **_):
        return self._send(200, ingest.read_blob(self.st, a, vid), "application/octet-stream")

    def api_search(self, a, q, one, **_):
        tenant = self.st.scope(a)
        term = one("q")
        cid = one("company")
        if cid:
            self.st.get(a, "companies", cid)
        terms = [w for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9-]{1,}", term)][:8]
        if not terms:
            return self._json(200, {"results": []})
        match = " OR ".join('"' + t + '"' for t in terms)
        sql = ("SELECT version_id, page_no, snippet(passages_fts,0,'[',']',' … ',16) s FROM passages_fts "
               "WHERE passages_fts MATCH ? AND tenant_id=?" + (" AND company_id=?" if cid else "") +
               " ORDER BY bm25(passages_fts) LIMIT 20")
        rows = self.st.db.all(sql, [match, tenant] + ([cid] if cid else []))
        self.st.audit(a, "search", cid or "*", term[:200], len(rows))
        return self._json(200, {"results": [{"version_id": r["version_id"], "page": r["page_no"], "excerpt": r["s"]} for r in rows]})

    def api_ask(self, a, q, one, **_):
        return self._json(200, answers.ask(self.st, a, one("company"), one("q")))

    def api_snapshot(self, a, sid, **_):
        return self._json(200, self.st.get(a, "comparison_snapshots", sid))

    def api_memo(self, a, vid, **_):
        return self._json(200, M.render(self.st, a, vid))

    def api_inbox(self, a, **_):
        return self._json(200, {"events": monitoring.inbox(self.st, a)})

    def api_definitions(self, a, **_):
        return self._json(200, {"metrics": D.registry(), "calculations": calc.definitions()})

    def api_coverage(self, a, cid, **_):
        return self._json(200, monitoring.coverage_status(self.st, a, cid))


ID = r"([A-Za-z0-9_]+)"
GET_ROUTES = [
    (r"/", "v_coverage"), (r"/company/" + ID, "v_company"), (r"/company/" + ID + "/documents", "v_documents"),
    (r"/project/" + ID, "v_project"), (r"/doc/" + ID, "v_doc"), (r"/doc/" + ID + r"/page/(\d+)\.png", "v_page_png"),
    (r"/doc/" + ID + "/original", "v_original"), (r"/fact/" + ID, "v_fact"), (r"/review", "v_review"),
    (r"/discrepancies", "v_discrepancies"), (r"/discrepancy/" + ID, "v_discrepancy"), (r"/risks/" + ID, "v_risks"),
    (r"/diligence/" + ID, "v_diligence"), (r"/peers/" + ID, "v_peers"), (r"/peerset/" + ID, "v_peerset"),
    (r"/snapshot/" + ID, "v_snapshot"), (r"/calcs/" + ID, "v_calcs"), (r"/calc/" + ID, "v_calc"),
    (r"/memos/" + ID, "v_memos"), (r"/memo/" + ID, "v_memo"), (r"/ask/" + ID, "v_ask"), (r"/inbox", "v_inbox"),
    (r"/portfolio", "v_portfolio"), (r"/definitions", "v_definitions"), (r"/admin/audit", "v_admin_audit"),
    (r"/admin/usage", "v_admin_usage"), (r"/admin/users", "v_admin_users"),
    (r"/export/memo/" + ID + r"\.(pdf|csv|json)", "v_export_memo"), (r"/export/facts/" + ID + r"\.csv", "v_export_facts"),
    (r"/export/snapshot/" + ID + r"\.csv", "v_export_snapshot"),
    (r"/api/whoami", "v_whoami"), (r"/api/companies", "api_companies"), (r"/api/company/" + ID, "api_company"),
    (r"/api/fact/" + ID, "api_fact"), (r"/api/doc/" + ID, "api_doc"), (r"/api/blob/" + ID, "api_blob"),
    (r"/api/search", "api_search"), (r"/api/ask", "api_ask"), (r"/api/snapshot/" + ID, "api_snapshot"),
    (r"/api/memo/" + ID, "api_memo"), (r"/api/inbox", "api_inbox"), (r"/api/definitions", "api_definitions"),
    (r"/api/coverage/" + ID, "api_coverage"),
]


# ------------------------------------------------------------------ actions
def _bool(v) -> bool:
    return str(v).lower() in ("1", "true", "yes", "on")


def _a_upload(st, a, p, files):
    f = files.get("file")
    if not f:
        raise Invalid("no file attached")
    res = ingest.upload(st, a, filename=f["filename"], data=f["data"], title=p.get("title") or f["filename"],
                        doc_type=p.get("doc_type") or "other", company_id=p.get("company_id") or None,
                        publisher=p.get("publisher", ""), publication_date=p.get("publication_date") or None,
                        source_url=p.get("source_url", ""), reporting_currency=p.get("reporting_currency") or None,
                        is_issuer_primary=_bool(p.get("is_issuer_primary")), synthetic=_bool(p.get("synthetic")),
                        new_version_of=p.get("new_version_of") or None)
    return {"id": res["version"]["id"], "duplicate": res["duplicate"],
            "run_status": res["run"]["status"] if res["run"] else None}


def _a_thesis(st, a, p, files):
    asm = []
    if p.get("assumption_text"):
        asm.append({"text": p["assumption_text"], "metric_ids": [p["assumption_metric"]] if p.get("assumption_metric") else []})
    for x in p.get("assumptions", []) if isinstance(p.get("assumptions"), list) else []:
        asm.append(x)
    r = M.create_thesis(st, a, p["company_id"], p["title"], p.get("thesis_text", ""), p.get("counter_thesis_text", ""), asm)
    return {"id": r["thesis"]["id"], "version_id": r["version"]["id"]}


def _ids(v):
    return v if isinstance(v, list) else _split(v)


def _a_user_create(st, a, p, files):
    if not a.can("admin"):
        raise AccessDenied("administrative")
    st.auth.create_user(p["user_id"], p["password"], p["role"], a.tenant_id)
    st.audit(a, "user_created_by_admin", p["user_id"], f"role={p['role']}")
    return {"id": p["user_id"]}


ACTIONS = {
    "company.create": lambda st, a, p, f: entities.create_company(st, a, p["name"], reporting_currency=p.get("reporting_currency") or None,
                                                                  aliases=_split(p.get("aliases", ""))),
    "listing.add": lambda st, a, p, f: entities.add_listing(st, a, p["company_id"], p["exchange"], p["ticker"], p.get("currency") or None),
    "project.create": lambda st, a, p, f: entities.create_project(
        st, a, p["company_id"], p["name"], commodity=p.get("commodity", ""), jurisdiction=p.get("jurisdiction", ""),
        country=p.get("country", ""), stage=p.get("stage") or None, deposit_type=p.get("deposit_type", ""),
        process_route=p.get("process_route", ""), interest_pct=p.get("interest_pct") or None,
        interest_kind=p.get("interest_kind") or "direct", effective_date=p.get("effective_date") or None),
    "ownership.change": lambda st, a, p, f: entities.change_ownership(st, a, p["company_id"], p["project_id"], p["interest_pct"],
                                                                      p["effective_date"], p.get("interest_kind", "direct"),
                                                                      notes=p.get("notes", "")),
    "document.upload": _a_upload,
    "ingest.retry": lambda st, a, p, f: {"runs": [r["status"] for r in ingest.retry_failed(st, a)]},
    "cite": lambda st, a, p, f: ingest.cite(st, a, p["version_id"], int(p["page_no"]), p["quote"]),
    "fact.review": lambda st, a, p, f: F.review(st, a, p["fact_id"], p["decision"], p.get("reason", "")),
    "fact.correct": lambda st, a, p, f: F.correct_fact(st, a, p["fact_id"], p.get("reason", ""),
                                                       raw_value=p.get("raw_value") or None, project_id=p.get("project_id") or None),
    "discrepancy.resolve": lambda st, a, p, f: F.resolve_discrepancy(st, a, p["discrepancy_id"], p.get("resolution", ""),
                                                                     p.get("keep_fact_id") or None),
    "assumption.set": lambda st, a, p, f: calc.set_assumption(st, a, p["name"], p["value"], p.get("rationale", ""),
                                                              unit=p.get("unit", ""), company_id=p.get("company_id") or None,
                                                              as_of_date=p.get("as_of_date") or None, source=p.get("source", "")),
    "calc.run": lambda st, a, p, f: {"calculations": [c["id"] for c in calc.run_standard(st, a, p["company_id"])]},
    "risk.create": lambda st, a, p, f: risks.create(st, a, p["company_id"], p["category"], p["title"],
                                                    project_id=p.get("project_id") or None, consequence=p.get("consequence", ""),
                                                    dependencies_text=p.get("dependencies_text", ""), mitigants=p.get("mitigants", ""),
                                                    unresolved_questions=p.get("unresolved_questions", ""),
                                                    monitoring_trigger=p.get("monitoring_trigger", "")),
    "risk.evidence": lambda st, a, p, f: risks.add_evidence(st, a, p["risk_id"], p["stance"], fact_id=p.get("fact_id") or None,
                                                            location_id=p.get("location_id") or None, note=p.get("note", "")),
    "risk.status": lambda st, a, p, f: risks.set_status(st, a, p["risk_id"], p["status"], p.get("reason", "")),
    "risk.attention": lambda st, a, p, f: risks.set_attention(st, a, p["risk_id"], _bool(p.get("attention")), p.get("reason", "")),
    "diligence.build": lambda st, a, p, f: {"items": len(diligence.build_checklist(st, a, p["company_id"], p.get("project_id") or None))},
    "diligence.question": lambda st, a, p, f: diligence.add_question(st, a, p["company_id"], p["question"], p.get("specialist", ""),
                                                                     p.get("document_request", "")),
    "diligence.review_item": lambda st, a, p, f: diligence.review_item(st, a, p["item_id"], p.get("notes", "")),
    "peerset.create": lambda st, a, p, f: peers.create_peer_set(st, a, p["company_id"], p["project_id"], p.get("name") or "Peer set"),
    "peer.decide": lambda st, a, p, f: peers.decide(st, a, p["member_id"], p["decision"], p.get("rationale", ""),
                                                    p.get("classification") or None),
    "peerset.approve": lambda st, a, p, f: peers.approve_set(st, a, p["peer_set_id"], p.get("rationale", "")),
    "snapshot.build": lambda st, a, p, f: {"id": peers.build_snapshot(st, a, p["peer_set_id"], p["market_data_date"])["id"]},
    "thesis.create": _a_thesis,
    "memo.create": lambda st, a, p, f: {"id": M.create_memo(st, a, p["company_id"], p.get("title") or "Memo",
                                                            p.get("thesis_id") or None, p.get("peer_set_id") or None)["memo"]["id"]},
    "memo.claim": lambda st, a, p, f: M.add_claim(st, a, p["version_id"], p["section"], p["kind"], p["text"],
                                                  _ids(p.get("fact_ids", "")), _ids(p.get("calc_ids", "")), _ids(p.get("risk_ids", ""))),
    "memo.remove_claim": lambda st, a, p, f: M.remove_claim(st, a, p["version_id"], p["claim_id"], p.get("reason", "")),
    "memo.review_claim": lambda st, a, p, f: M.review_claim(st, a, p["version_id"], p["claim_id"], p["decision"], p.get("reason", "")),
    "memo.review_supported": lambda st, a, p, f: M.review_supported_claims(st, a, p["version_id"], p.get("reason", "")),
    "memo.submit": lambda st, a, p, f: M.submit(st, a, p["version_id"]),
    "memo.approve": lambda st, a, p, f: M.approve(st, a, p["version_id"], p.get("rationale", "")),
    "memo.new_version": lambda st, a, p, f: M.new_version(st, a, p["memo_id"], refresh=_bool(p.get("refresh"))),
    "event.status": lambda st, a, p, f: events.set_status(st, a, p["event_id"], p["status"], p.get("reason", "")),
    "watchlist.create": lambda st, a, p, f: monitoring.create_watchlist(st, a, p["name"]),
    "watchlist.add": lambda st, a, p, f: monitoring.watch(st, a, p["watchlist_id"], p["company_id"]),
    "holding.add": lambda st, a, p, f: monitoring.add_holding(st, a, p.get("portfolio") or "Fund I", p["company_id"], p["shares"],
                                                              p["as_of_date"]),
    "ask": lambda st, a, p, f: answers.ask(st, a, p["company_id"], p.get("question", ""), p.get("project_id") or None),
    "user.create": _a_user_create,
}


def _upload_form(csrf, company_id, nxt) -> str:
    return ui.form("/api/document.upload",
                   (ui.hid("company_id", company_id) if company_id else "") +
                   '<label>File (PDF, XLSX, CSV, TXT)<br><input type="file" name="file" required></label>' +
                   ui.inp("title", "Title", size=60) +
                   ui.sel("doc_type", "Type", [(t, t.replace("_", " ")) for t in ingest.DOC_TYPES]) +
                   ui.inp("publisher", "Publisher") + ui.inp("publication_date", "Publication date (YYYY-MM-DD)") +
                   ui.inp("reporting_currency", "Declared reporting currency (only used for bare '$')") +
                   ui.sel("is_issuer_primary", "Issuer primary document?", [("0", "no"), ("1", "yes")]) +
                   ui.sel("synthetic", "Synthetic test file?", [("0", "no"), ("1", "yes")]),
                   csrf, "Upload and ingest", nxt, multipart=True)


def _login_page(err: str) -> bytes:
    body = ('<form method="post" action="/login"><label>User ID<br><input name="user_id" required autofocus></label>'
            '<label>Password<br><input name="password" type="password" required minlength="12"></label>'
            '<p><button>Sign in</button></p></form>' + (f"<p><b>{esc(err)}</b></p>" if err else "") +
            '<p class="note">Authorized access only. Sign-ins are recorded in a tamper-evident audit.</p>')
    return ui.page("Sign in", body)


def _multipart(ctype: str, raw: bytes) -> tuple[dict, dict]:
    msg = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
        b"Content-Type: " + ctype.encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + raw)
    fields, files = {}, {}
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_param("filename", header="content-disposition")
        data = part.get_payload(decode=True) or b""
        if filename:
            files[name] = {"filename": filename, "data": data}
        else:
            fields[name] = data.decode("utf-8", "replace")
    return fields, files


def make_server(store: Store, auth: Auth, host: str = "127.0.0.1", port: int = 8780, quiet: bool = False):
    store.auth = auth
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.app = App(store, auth)
    httpd.quiet = quiet
    return httpd
