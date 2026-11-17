"""Tenant-scoped record access.

Provenance (adapted): asevy/vision-edge-gateway @ 592cbff, ve_db.py
Store._scope(). The rule carried over: scope is not a filter a caller may
forget — every read and write takes an Actor and derives the tenant predicate
itself, and an unrecognised role RAISES rather than widening the query. A
record belonging to another tenant is reported as not found (404), because
"exists but denied" is itself information about another customer.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path

from . import audit, config
from .auth import ROLES, Actor
from .db import Database, dumps


class AccessDenied(Exception):
    pass


class NotFound(Exception):
    pass


class Invalid(ValueError):
    pass


# Tables that hold tenant-owned rows. Anything not listed cannot be reached
# through the generic accessors.
TENANT_TABLES = frozenset({
    "workspaces", "companies", "projects", "entity_aliases", "listings", "ownership_interests",
    "counterparties", "counterparty_links", "documents", "document_versions", "pages",
    "doc_tables", "source_locations", "ingestion_runs", "facts", "review_decisions",
    "discrepancies", "assumptions", "calculations", "risk_findings", "risk_evidence",
    "risk_history", "diligence_items", "diligence_questions", "commitments",
    "commitment_updates", "peer_sets", "peer_members", "comparison_snapshots", "theses",
    "thesis_versions", "thesis_assumptions", "memos", "memo_versions", "events",
    "notifications", "watchlists", "holdings", "source_feeds", "usage_ledger", "exports",
})

JSON_COLUMNS = {
    "projects": {"infrastructure"},
    "document_versions": {"unreadable_pages", "parse_warnings"},
    "doc_tables": {"rows", "footnotes"},
    "source_locations": {"footnotes", "bbox"},
    "facts": {"transformations", "qualifiers", "checks"},
    "calculations": {"inputs", "missing", "warnings", "caveats", "parameters"},
    "diligence_items": {"required_metrics", "evidence"},
    "peer_members": {"inclusion_reasons", "differences"},
    "comparison_snapshots": {"body"},
    "thesis_assumptions": {"metric_ids", "fact_ids", "calc_ids", "commitment_ids"},
    "memo_versions": {"body"},
    "events": {"detail"},
    "risk_history": {"change"},
}

# Columns a generic update may change. Evidence values are deliberately absent:
# a fact's value, source or dates never change in place — a correction is a
# new revision row (see facts.correct_fact).
MUTABLE = {
    "facts": {"workflow_state", "checks", "updated_at"},
    "document_versions": {"parse_status", "parse_warnings", "page_count", "unreadable_pages",
                          "text_fingerprint", "mirror_of_version_id", "mirror_similarity"},
    "ingestion_runs": {"status", "attempts", "error", "parser", "parser_version", "extractor",
                       "extractor_version", "candidates", "started_at", "finished_at"},
    "discrepancies": {"status", "resolution", "resolved_by", "resolved_at"},
    "calculations": {"stale", "stale_reason"},
    "assumptions": {"superseded_by"},
    "risk_findings": {"title", "consequence", "dependencies_text", "mitigants",
                      "unresolved_questions", "monitoring_trigger", "owner", "reviewer", "status",
                      "attention", "attention_reason", "updated_at", "project_id", "category"},
    "diligence_items": {"status", "evidence", "notes", "reviewed_by", "reviewed_at"},
    "diligence_questions": {"status", "answer_fact_id"},
    "commitments": {"status"},
    "peer_sets": {"status", "approved_by", "approved_at", "approval_rationale", "name"},
    "peer_members": {"decision", "decision_rationale", "decided_by", "decided_at",
                     "classification"},
    "comparison_snapshots": {"stale", "stale_reason"},
    "thesis_assumptions": {"status", "status_reason", "updated_at"},
    "memo_versions": {"status", "submitted_at", "approved_by", "approved_at", "content_sha256",
                      "stale", "stale_reason", "body", "evidence_cutoff"},
    "events": {"status", "status_reason", "reviewed_by", "reviewed_at"},
    "notifications": {"read_at"},
    "source_feeds": {"status", "last_success_at", "last_attempt_at", "last_error"},
    "ownership_interests": {"end_date"},
    "entity_aliases": {"valid_to"},
    "listings": {"valid_to"},
    "projects": {"stage", "stage_source_location_id", "deposit_type", "process_route",
                 "infrastructure", "jurisdiction", "country", "commodity"},
}


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


ID_PREFIX = {
    "companies": "co", "projects": "proj", "entity_aliases": "alias", "listings": "lst",
    "ownership_interests": "own", "counterparties": "cp", "counterparty_links": "cpl", "documents": "doc",
    "document_versions": "ver", "pages": "pg", "doc_tables": "tbl", "source_locations": "loc",
    "ingestion_runs": "run", "facts": "fact", "review_decisions": "rev", "discrepancies": "disc",
    "assumptions": "asm", "calculations": "calc", "risk_findings": "risk", "risk_evidence": "rev_ev",
    "risk_history": "rhist", "diligence_items": "dil", "diligence_questions": "dq", "commitments": "cmt",
    "commitment_updates": "cmtu", "peer_sets": "pset", "peer_members": "pmem", "comparison_snapshots": "snap",
    "theses": "th", "thesis_versions": "thv", "thesis_assumptions": "tha", "memos": "memo",
    "memo_versions": "mver", "events": "evt", "notifications": "ntf", "watchlists": "wl", "holdings": "hold",
    "source_feeds": "feed", "usage_ledger": "use", "exports": "exp", "workspaces": "ws",
}


class Store:
    def __init__(self, db: Database, data_dir: Path, settings=None):
        self.db = db
        self.data_dir = Path(data_dir)
        self.settings = settings or config.load_settings({"JMI_DATA_DIR": str(data_dir)})
        self._cols: dict[str, list[str]] = {}

    # ------------------------------------------------------------ authority
    def scope(self, actor: Actor) -> str:
        """Return the tenant id the actor may touch, or raise. Never widens."""
        if actor is None:
            raise AccessDenied("not signed in")
        if actor.role not in ROLES and actor.role != "system":
            raise AccessDenied(f"unknown role: {actor.role!r}")
        if not actor.tenant_id:
            raise AccessDenied("actor has no tenant")
        if actor.role == "system" and not actor.user_id.startswith("system:"):
            raise AccessDenied("malformed system principal")
        return actor.tenant_id

    def require(self, actor: Actor, cap: str) -> str:
        tenant = self.scope(actor)
        if not actor.can(cap):
            raise AccessDenied(f"role '{actor.role}' lacks capability '{cap}'")
        return tenant

    # ------------------------------------------------------------ helpers
    def _table(self, table: str) -> str:
        if table not in TENANT_TABLES:
            raise AccessDenied(f"table not accessible: {table}")
        return table

    def _columns(self, table: str) -> list[str]:
        if table not in self._cols:
            self._cols[table] = self.db.columns(table)
        return self._cols[table]

    def decode(self, table: str, row: dict | None) -> dict | None:
        if row is None:
            return None
        for c in JSON_COLUMNS.get(table, ()):
            if c in row and isinstance(row[c], str):
                try:
                    row[c] = json.loads(row[c])
                except ValueError:
                    pass
        return row

    def _encode(self, table: str, row: dict) -> dict:
        out = {}
        for k, v in row.items():
            if k in JSON_COLUMNS.get(table, ()) and not isinstance(v, str) and v is not None:
                v = dumps(v)
            elif isinstance(v, bool):
                v = int(v)
            out[k] = v
        return out

    # ------------------------------------------------------------ generic CRUD
    def get(self, actor: Actor, table: str, rid: str) -> dict:
        tenant = self.require(actor, "read")
        t = self._table(table)
        row = self.db.one(f"SELECT * FROM {t} WHERE id=? AND tenant_id=?", (rid, tenant))
        if row is None:
            raise NotFound(f"{table} {rid}")
        return self.decode(t, row)

    def find(self, _actor: Actor, table: str, order: str = "", limit: int | None = None,
             **where) -> list[dict]:
        # parameter named _actor so a column called "actor" can be filtered on
        tenant = self.require(_actor, "read")
        t = self._table(table)
        cols = self._columns(t)
        clauses, params = ["tenant_id=?"], [tenant]
        for k, v in where.items():
            if k not in cols:
                raise Invalid(f"unknown column {k}")
            if v is None:
                clauses.append(f"{k} IS NULL")
            elif isinstance(v, (list, tuple, set, frozenset)):
                vals = list(v)
                if not vals:
                    return []
                clauses.append(f"{k} IN ({','.join('?' * len(vals))})")
                params.extend(vals)
            else:
                clauses.append(f"{k}=?")
                params.append(v)
        sql = f"SELECT * FROM {t} WHERE " + " AND ".join(clauses)
        if order:
            for part in order.split(","):
                name = part.strip().split()[0]
                if name not in cols:
                    raise Invalid(f"unknown order column {name}")
            sql += " ORDER BY " + order
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [self.decode(t, r) for r in self.db.all(sql, params)]

    def insert(self, actor: Actor, table: str, row: dict, cap: str = "write") -> dict:
        tenant = self.require(actor, cap)
        t = self._table(table)
        row = dict(row)
        row["tenant_id"] = tenant
        if "id" in self._columns(t) and not row.get("id"):
            row["id"] = new_id(ID_PREFIX.get(t, t[:4].rstrip("_")))
        cols = self._columns(t)
        unknown = set(row) - set(cols)
        if unknown:
            raise Invalid(f"unknown columns for {t}: {sorted(unknown)}")
        enc = self._encode(t, row)
        keys = list(enc)
        self.db.execute(f"INSERT INTO {t}({','.join(keys)}) VALUES({','.join('?' * len(keys))})",
                        [enc[k] for k in keys])
        return row

    def update(self, actor: Actor, table: str, rid: str, patch: dict, cap: str = "write") -> None:
        tenant = self.require(actor, cap)
        t = self._table(table)
        allowed = MUTABLE.get(t, set())
        bad = set(patch) - allowed
        if bad:
            raise Invalid(f"columns not mutable on {t}: {sorted(bad)}")
        if not patch:
            return
        enc = self._encode(t, patch)
        sets = ", ".join(f"{k}=?" for k in enc)
        cur = self.db.execute(f"UPDATE {t} SET {sets} WHERE id=? AND tenant_id=?",
                              [*enc.values(), rid, tenant])
        if cur.rowcount == 0:
            raise NotFound(f"{table} {rid}")

    def audit(self, actor: Actor, action: str, target: str = "", detail="", count: int = 0) -> None:
        audit.append(self.db, actor, action, target, detail, count)

    def usage(self, actor: Actor, kind: str, quantity, unit: str = "", detail: str = "",
              model: str | None = None, tokens_in: int | None = None,
              tokens_out: int | None = None, cost_usd: str | None = None) -> None:
        """Usage ledger (adapted from mso-ip-lab storage/audit.log_call)."""
        tenant = self.scope(actor)
        self.db.execute(
            "INSERT INTO usage_ledger(id,tenant_id,at,kind,quantity,unit,model,tokens_in,tokens_out,"
            "cost_usd,detail) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (new_id("use"), tenant, config.iso_now(), kind, str(quantity), unit, model,
             tokens_in, tokens_out, cost_usd, detail))

    # ------------------------------------------------------------ blobs
    def blob_path(self, tenant_id: str, sha256: str) -> Path:
        # Per-tenant directories: identical bytes uploaded by two customers are
        # stored twice. Cross-tenant de-duplication would leak existence.
        return self.data_dir / "blobs" / tenant_id / sha256[:2] / sha256
