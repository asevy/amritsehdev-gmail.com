"""Claude connector (Model Context Protocol server).

Lets an analyst work with this application from Claude — Claude Desktop or
Claude Code — under their own firm's Claude plan. Claude can READ the firm's
evidence records through these tools; it cannot write, approve, or see
another firm's data.

    python -m jmi create-api-token analyst.a --label "Claude Desktop"   # shown once
    JMI_DATA_DIR=... JMI_API_TOKEN=jmit_... python -m jmi mcp            # stdio

Claude Desktop config (claude_desktop_config.json):
    {"mcpServers": {"junior-mining": {"command": "python", "args": ["-m", "jmi", "mcp"],
      "cwd": "/path/to/junior_mining",
      "env": {"JMI_DATA_DIR": "/path/to/data", "JMI_API_TOKEN": "jmit_..."}}}}

Claude Code:
    claude mcp add junior-mining --env JMI_DATA_DIR=/path/to/data --env JMI_API_TOKEN=jmit_... \
        -- python -m jmi mcp

Controls carried over unchanged
  * The token acts as its user in its user's tenant, with READ capability
    only (auth.actor_for_api_token), whatever the user's role.
  * Every tool goes through the same tenant-scoped store; another firm's
    record is "not found".
  * Facts are returned with their workflow state, evidence type, attribution,
    dates and exact source quote; by default only reviewer-approved facts.
  * `ask` is the same constrained answerer as the web app (refusals,
    not-found with coverage, no free-form answers).
  * Every result passes the no-score policy scan before it leaves the process.
  * Every tool call is audited as the user.

claude.ai custom connectors on the web need a public HTTPS endpoint with
connector authentication; that deployment is not built here (see
docs/CLAUDE_INTEGRATION.md).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from . import answers, config, facts as F, ingest, memo as M, monitoring, policy, risks
from . import definitions as D
from .auth import Actor, Auth
from .db import Database
from .store import NotFound, Store

INSTRUCTIONS = (
    "Junior Mining Intelligence: evidence records for junior-mining diligence. When you use these results: "
    "(1) attribute issuer statements ('the company reports') and keep each figure's date, category, basis and "
    "study qualifiers; (2) cite the fact id and the quoted source text; (3) say when a value is a forecast or "
    "estimate; (4) treat 'not found in documents reviewed' as unknown, not as absence or zero; (5) resources are "
    "not reserves, project NPV is not equity value, an application is not an issued permit; (6) this system "
    "produces no scores, ratings, probabilities, price targets or recommendations — do not invent them from these "
    "records. Reviewer approval means a record matches its source, not that the claim is independently true.")

NOTICE = ("Evidence records from Junior Mining Intelligence. Not a recommendation, rating or price target. "
          "Reviewer-approved means matches its cited source; not independent verification.")


class ConnectorError(Exception):
    pass


def _resolve_company(store: Store, actor: Actor, company: str) -> dict:
    try:
        return store.get(actor, "companies", company)
    except NotFound:
        pass
    want = company.strip().lower()
    for c in store.find(actor, "companies"):
        if c["name"].lower() == want:
            return c
    for a in store.find(actor, "entity_aliases", entity_kind="company"):
        if a["alias"].lower() == want:
            return store.get(actor, "companies", a["entity_id"])
    raise ConnectorError(f"no company named {company!r} in your workspace (use list_companies)")


def _fact_out(store, actor, f) -> dict:
    loc = store.get(actor, "source_locations", f["location_id"]) if f["location_id"] else None
    ver = store.get(actor, "document_versions", f["version_id"]) if f["version_id"] else None
    doc = store.get(actor, "documents", ver["document_id"]) if ver else None
    return {"fact_id": f["id"], "metric": D.metric(f["metric_id"]).label, "statement": M.fact_claim_text(store, actor, f),
            "value": f["normalized_value"], "unit": f["unit"], "currency": f["currency"],
            "as_of_date": f["as_of_date"], "effective_date": f["effective_date"],
            "category": f["resource_category"], "basis": f["scope_basis"], "study_type": f["study_type"],
            "evidence_type": f["evidence_type"], "attribution": f["attribution"],
            "workflow_state": f["workflow_state"],
            "source": {"document": doc["title"] if doc else None, "published": ver["publication_date"] if ver else None,
                       "page": loc["page_no"] if loc else None, "cell": loc["cell_ref"] if loc else None,
                       "quote": loc["quote"] if loc else None}}


class Connector:
    """Tool implementations, independent of the MCP transport (and testable)."""

    def __init__(self, store: Store, actor: Actor):
        if actor is None or actor.caps != frozenset({"read"}):
            raise ConnectorError("the connector runs only with a read-only token actor")
        self.store, self.actor = store, actor

    def _done(self, tool: str, target: str, data) -> dict:
        out = {"notice": NOTICE, "workspace": self.actor.tenant_id, "analysis_time": config.iso_now(), "data": data}
        bad = policy.scan(out)
        if bad:
            raise ConnectorError("result withheld by the no-score policy guard")
        self.store.audit(self.actor, f"mcp_{tool}", target)
        return out

    def _company(self, company: str) -> dict:
        return _resolve_company(self.store, self.actor, company)

    def list_companies(self) -> dict:
        rows = monitoring.watchlist_view(self.store, self.actor)
        return self._done("list_companies", "*", [
            {"company_id": r["company"]["id"], "name": r["company"]["name"],
             "synthetic": bool(r["company"]["synthetic"]), "coverage_status": r["status"],
             "coverage_reasons": r["reasons"], "evidence_cutoff": r["evidence_cutoff"],
             "projects": [{"name": p["name"], "commodity": p["commodity"], "jurisdiction": p["jurisdiction"],
                           "stage": D.STAGE_LABELS.get(p["stage"] or "", "not recorded")} for p in r["projects"]]}
            for r in rows])

    def get_facts(self, company: str, metric: str | None = None, include_unapproved: bool = False) -> dict:
        c = self._company(company)
        if metric and metric not in D.METRICS:
            matches = [k for k, d in D.METRICS.items() if metric.lower() in (k + " " + d.label).lower()]
            if len(matches) != 1:
                raise ConnectorError(f"unknown metric {metric!r}; use list_definitions")
            metric = matches[0]
        rows = F.current(self.store, self.actor, c["id"], metric, approved_only=not include_unapproved)
        rows = sorted(rows, key=lambda f: (f["metric_id"], f["effective_date"] or f["as_of_date"] or ""))
        return self._done("get_facts", c["id"], {
            "company": c["name"], "filter": metric, "approved_only": not include_unapproved,
            "facts": [_fact_out(self.store, self.actor, f) for f in rows],
            "note": "Absence from this list means not established in documents reviewed, not zero or absent."})

    def ask(self, company: str, question: str) -> dict:
        c = self._company(company)
        return self._done("ask", c["id"], answers.ask(self.store, self.actor, c["id"], question))

    def get_coverage(self, company: str) -> dict:
        c = self._company(company)
        cs = monitoring.coverage_status(self.store, self.actor, c["id"])
        return self._done("get_coverage", c["id"], {k: cs[k] for k in ("status", "all", "reasons", "evidence_cutoff")}
                          | {"documents_reviewed": [f"{d['title']} ({d['publication_date']})"
                                                    for d in cs["coverage"]["documents_reviewed"]]})

    def get_risks(self, company: str) -> dict:
        c = self._company(company)
        out = []
        for r in risks.register(self.store, self.actor, c["id"]):
            out.append({"risk_id": r["id"], "title": r["title"], "category": D.RISK_CATEGORIES[r["category"]],
                        "status": D.RISK_STATUSES[r["status"]],
                        "marked_for_attention": r["attention_reason"] if r["attention"] else None,
                        "consequence": r["consequence"], "unresolved_questions": r["unresolved_questions"],
                        "supporting_evidence": len([e for e in r["evidence"] if e["stance"] == "supporting"]),
                        "contrary_evidence": len([e for e in r["evidence"] if e["stance"] == "contrary"])})
        return self._done("get_risks", c["id"], {"company": c["name"], "risks": out,
                                                 "note": "Open questions are not adverse findings."})

    def get_comparison(self, company: str) -> dict:
        c = self._company(company)
        sets = self.store.find(self.actor, "peer_sets", subject_company_id=c["id"], status="approved")
        snaps = sorted([s for ps in sets for s in self.store.find(self.actor, "comparison_snapshots", peer_set_id=ps["id"])],
                       key=lambda s: s["created_at"])
        if not snaps:
            return self._done("get_comparison", c["id"], {"company": c["name"], "comparison": None,
                                                          "note": "No approved peer comparison exists yet."})
        s = snaps[-1]
        b = s["body"]
        rows = [{"company": r["company"], "project": r["project"], "role": r["role"], "classification": r["classification"],
                 "metrics": {label: (r["cells"].get(k, {}).get("display") if r["cells"].get(k, {}).get("status") in
                                     ("computed", "reported") else "withheld: " + r["cells"].get(k, {}).get("reason", ""))
                             for k, label in b["metric_rows"]}} for r in b["rows"]]
        return self._done("get_comparison", c["id"], {
            "company": c["name"], "snapshot_id": s["id"], "market_data_date": b["market_data_date"],
            "stale": s["stale_reason"] if s["stale"] else None, "rows": rows, "comparability": b["comparability"],
            "observations": b["observations"], "explanations": b["explanations"],
            "note": "Comparisons are per specified measure; they do not establish an overall preference."})

    def get_memo(self, company: str) -> dict:
        c = self._company(company)
        memos = self.store.find(self.actor, "memos", company_id=c["id"], order="created_at")
        if not memos:
            return self._done("get_memo", c["id"], {"company": c["name"], "memo": None})
        vs = self.store.find(self.actor, "memo_versions", memo_id=memos[-1]["id"], order="version_no")
        approved = [v for v in vs if v["status"] == "approved"]
        v = approved[-1] if approved else vs[-1]
        r = M.render(self.store, self.actor, v["id"])
        return self._done("get_memo", c["id"], {
            "title": r["title"], "status": r["status_label"], "evidence_cutoff": r["evidence_cutoff"],
            "unresolved": r["unresolved"],
            "sections": [{"title": s["title"], "claims": [{"id": it["id"], "text": it["text"],
                                                           "review": it["review"].get("status"),
                                                           "changed_since_approval": it.get("changed_since_approval")}
                                                          for it in s["items"]]} for s in r["sections"]],
            "withheld_claims": r["withheld_claims"]})

    def search_documents(self, company: str, query: str) -> dict:
        c = self._company(company)
        res = answers._passages(self.store, self.actor, c["id"], query)
        return self._done("search_documents", c["id"], {"company": c["name"], **res})

    def list_definitions(self, metric: str | None = None) -> dict:
        reg = D.registry()["metrics"]
        if metric:
            reg = {k: v for k, v in reg.items() if metric.lower() in (k + " " + v["label"]).lower()}
        return self._done("list_definitions", metric or "*", {
            "registry_version": D.REGISTRY_VERSION,
            "metrics": {k: {"label": v["label"], "definition": v["definition"], "caution": v["caution"]}
                        for k, v in reg.items()}})


def build_server(store: Store, actor: Actor):
    """Register the connector's tools on an MCP 2.x MCPServer (all read-only)."""
    from mcp.server.mcpserver import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
    from mcp.types import ToolAnnotations
    conn = Connector(store, actor)
    server = MCPServer(name="junior-mining-intelligence", title="Junior Mining Intelligence",
                       instructions=INSTRUCTIONS, version="0.1.0")
    ro = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

    def guarded(fn):
        def run(*a, **kw):
            try:
                with store.db.lock:
                    return fn(*a, **kw)
            except ConnectorError as exc:
                raise ToolError(str(exc)) from exc
            except NotFound as exc:
                raise ToolError("not found in your workspace") from exc
        return run

    @server.tool(annotations=ro)
    def list_companies() -> dict:
        """List the companies in your workspace with coverage status (fresh/stale/incomplete/ingestion failed),
        evidence cutoff and projects. Coverage status describes the evidence base, not the company."""
        return guarded(conn.list_companies)()

    @server.tool(annotations=ro)
    def get_facts(company: str, metric: str | None = None, include_unapproved: bool = False) -> dict:
        """Source-linked facts for a company (name or id): value, date, qualifiers, evidence type, attribution,
        workflow state and the exact source quote. Reviewer-approved only unless include_unapproved is true.
        Optional metric filter, e.g. 'npv', 'cash_unrestricted', 'resource_contained_metal', 'permit_status'."""
        return guarded(conn.get_facts)(company, metric, include_unapproved)

    @server.tool(annotations=ro)
    def ask(company: str, question: str) -> dict:
        """Ask a factual question about a company. The answer is assembled only from stored, cited records;
        it may say 'not found in documents reviewed' or decline (recommendations, probabilities, scores,
        price targets and misconduct judgements are out of scope)."""
        return guarded(conn.ask)(company, question)

    @server.tool(annotations=ro)
    def get_coverage(company: str) -> dict:
        """What the evidence base for a company consists of: documents reviewed, failed or unreadable
        material, stale data and the evidence cutoff date."""
        return guarded(conn.get_coverage)(company)

    @server.tool(annotations=ro)
    def get_risks(company: str) -> dict:
        """The company's risk register: neutral titles, categories, status (open question vs documented
        finding), attention reasons and counts of supporting and contrary evidence. No risk scores exist."""
        return guarded(conn.get_risks)(company)

    @server.tool(annotations=ro)
    def get_comparison(company: str) -> dict:
        """The latest analyst-approved peer comparison for a company on one market-data date, with withheld
        metrics, comparability notes, observations and possible explanations. No overall ranking."""
        return guarded(conn.get_comparison)(company)

    @server.tool(annotations=ro)
    def get_memo(company: str) -> dict:
        """The latest approved (or else latest draft) memo version for a company, with status, unresolved items
        and claims. Approved versions are shown exactly as approved."""
        return guarded(conn.get_memo)(company)

    @server.tool(annotations=ro)
    def search_documents(company: str, query: str) -> dict:
        """Search the company's documents for passages containing the query terms. Passages are for reading;
        they are not verified answers."""
        return guarded(conn.search_documents)(company, query)

    @server.tool(annotations=ro)
    def list_definitions(metric: str | None = None) -> dict:
        """Metric definitions used by the workspace (e.g. what 'resource contained metal' or 'NPV' means here)."""
        return guarded(conn.list_definitions)(metric)

    return server


def main() -> int:
    settings = config.load_settings()
    token = os.environ.get("JMI_API_TOKEN", "")
    db = Database(Path(settings.data_dir) / "jmi.sqlite3")
    auth = Auth(db)
    actor = auth.actor_for_api_token(token)
    if actor is None:
        print("JMI_API_TOKEN is missing, revoked or invalid. Create one with: "
              "python -m jmi create-api-token <user>", file=sys.stderr)
        return 2
    store = Store(db, settings.data_dir, settings)
    build_server(store, actor).run("stdio")
    return 0
