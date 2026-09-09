"""Claim-ledger schema for the Caribbean wealth graph.

The claim is the atomic unit of data (DATA_MODEL_AND_METHODOLOGY.md 2a):

    Subject -> Predicate -> Object/value -> Valid dates -> Sources ->
    Evidence strength -> Analyst -> Verification date -> Status ->
    Superseded-by

Rules enforced here, from the methodology and the playbook template:
- Claims are never deleted; supersession chains preserve history.
- A LEAD may be unsourced (research layer). PROPOSED requires a source.
  APPROVED additionally requires an analyst and a verification date.
- Registry-derived predicates must carry the registry's verbatim wording:
  the graph preserves exactly what the registry says.
- Beneficial-ownership predicates must carry the statutory basis (test,
  threshold, regime version, as-of date). "Not found" is only what the
  statute makes it.
- A claim is publishable only if every load-bearing source is.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Optional


CLAIM_STATUSES = ("LEAD", "PROPOSED", "APPROVED", "SUPERSEDED", "RETRACTED")
EVIDENCE_TIERS = (1, 2, 3, 4)  # per DATA_MODEL section 6
SOURCE_ACCESS = ("internal", "publishable")  # I / P; possession implies O
CONFIDENCE = ("HIGH", "MODERATE", "LOW")
DEBT_STATES = ("VERIFIED", "ESTIMATED", "UNKNOWN")
VALUATION_STATES = ("LIVE", "FX_LINKED", "MODELLED", "TRANSACTION_MARKED",
                    "PROPERTY_MARKED", "STALE", "UNDER_REVIEW")
ENTITY_STATUSES = ("operating_company", "holdco", "nominee", "trustee",
                   "foundation", "spv", "employee_plan", "institutional",
                   "government", "estate", "unknown")
ENTITY_TYPES = ("person", "family", "branch", "company", "asset",
                "institution")

# Predicates whose object is the registry's own assertion.
REGISTRY_PREDICATES_PREFIX = "registry_"
# Predicates derived from a beneficial-ownership regime.
BO_PREDICATES_PREFIX = "bo_"


@dataclass
class Entity:
    id: str                      # stable slug; name-as-key forbidden
    name: str
    type: str                    # ENTITY_TYPES
    jurisdiction: Optional[str] = None
    status: Optional[str] = None  # ENTITY_STATUSES, for intermediaries
    notes: str = ""

    def validate(self) -> None:
        if self.type not in ENTITY_TYPES:
            raise ValueError(f"{self.id}: bad entity type {self.type!r}")
        if self.status is not None and self.status not in ENTITY_STATUSES:
            raise ValueError(f"{self.id}: bad entity status {self.status!r}")


@dataclass
class Source:
    id: str
    description: str
    tier: int                    # EVIDENCE_TIERS
    retrieval_date: str          # ISO date
    url_or_registry_id: str = ""
    passage: str = ""            # the relevant passage/page
    analyst: str = ""
    access: str = "internal"     # SOURCE_ACCESS - the P determination
    preserved: bool = False      # archive copy/hash exists
    archive_ref: str = ""
    notes: str = ""

    def validate(self) -> None:
        if self.tier not in EVIDENCE_TIERS:
            raise ValueError(f"{self.id}: bad tier {self.tier!r}")
        if self.access not in SOURCE_ACCESS:
            raise ValueError(f"{self.id}: bad access {self.access!r}")


@dataclass
class Claim:
    id: str
    subject: str                 # entity id
    predicate: str
    object: object               # entity id, value, or dict
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    sources: list = field(default_factory=list)   # source ids
    status: str = "LEAD"
    analyst: str = ""
    verified_date: Optional[str] = None
    superseded_by: Optional[str] = None
    registry_verbatim: str = ""  # required for registry_* predicates
    statutory_basis: Optional[dict] = None  # required for bo_* predicates:
    # {"test": shares|voting|control, "threshold": str,
    #  "regime_version": str, "as_of": ISO date}
    methodology_version: str = ""  # required for APPROVED
    notes: str = ""

    def validate(self) -> None:
        if self.status not in CLAIM_STATUSES:
            raise ValueError(f"{self.id}: bad status {self.status!r}")
        if self.status in ("PROPOSED", "APPROVED") and not self.sources:
            raise ValueError(
                f"{self.id}: {self.status} claims require at least one "
                f"source (unsourced hypotheses stay LEAD in the research "
                f"layer)")
        if self.status == "APPROVED" and not (self.analyst and
                                              self.verified_date):
            raise ValueError(
                f"{self.id}: APPROVED requires analyst and verified_date")
        if (self.predicate.startswith(REGISTRY_PREDICATES_PREFIX)
                and not self.registry_verbatim):
            raise ValueError(
                f"{self.id}: registry-derived claims must preserve the "
                f"registry's exact words (registry_verbatim)")
        if self.predicate.startswith(BO_PREDICATES_PREFIX):
            b = self.statutory_basis or {}
            missing = [k for k in ("test", "threshold", "regime_version",
                                   "as_of") if not b.get(k)]
            if missing:
                raise ValueError(
                    f"{self.id}: beneficial-ownership claims must record "
                    f"the statutory basis; missing {missing}")

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def publishable(claim: Claim, sources_by_id: dict) -> bool:
    """A claim may be republished only if every source may be."""
    if not claim.sources:
        return False
    return all(sources_by_id[s].access == "publishable"
               for s in claim.sources if s in sources_by_id)


def evidence_path_gaps(claim: Claim, sources_by_id: dict) -> list:
    """The reproducible-evidence-path invariant.

    An APPROVED claim must always answer: which document, which page/
    passage, which analyst, which methodology version, which approval.
    Returns a list of human-readable gaps; empty means the path is
    complete. Enforced at approval time and re-checked by Ledger.audit(),
    which demotes any approved claim whose path has broken.
    """
    gaps = []
    if not claim.sources:
        gaps.append("no sources")
    for sid in claim.sources:
        s = sources_by_id.get(sid)
        if s is None:
            gaps.append(f"source {sid} missing from ledger")
            continue
        if not s.passage:
            gaps.append(f"{sid}: no passage/page recorded")
        if not (s.preserved and s.archive_ref):
            gaps.append(f"{sid}: document not preserved (archive)")
        if not s.analyst:
            gaps.append(f"{sid}: no reviewing analyst recorded")
    if not claim.analyst:
        gaps.append("no approving analyst")
    if not claim.verified_date:
        gaps.append("no approval date")
    if not claim.methodology_version:
        gaps.append("no methodology version")
    return gaps
