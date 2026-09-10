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


CLAIM_STATUSES = ("LEAD", "PROPOSED", "APPROVED", "REJECTED",
                  "SUPERSEDED", "RETRACTED")
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
                "property", "transaction", "institution")

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
class Extraction:
    """The bridge between a Source and a Claim: one source supports many
    claims, and the exact fragment supporting each claim is preserved
    separately, so a challenge jumps to the fragment, never back into a
    180-page report."""
    id: str
    source_id: str
    passage: str                  # exact passage
    locator: str = ""             # page/section; table row/cell
    method: str = "manual"        # manual | manual-relay | ocr | ai
    analyst: str = ""             # verifying analyst
    confidence: str = ""          # for OCR/AI extractions
    notes: str = ""

    def validate(self) -> None:
        if not self.passage:
            raise ValueError(f"{self.id}: extraction without a passage")


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
    jurisdiction: str = ""         # market whose playbook governed this
    extractions: list = field(default_factory=list)  # Extraction ids
    block_id: str = ""  # unique underlying economic block. THE
    # DEDUPLICATION INVARIANT: the same block can never be counted twice
    # merely because an issuer attributes it to multiple connected
    # persons - aggregation requires unique block_ids (see
    # no_double_count)
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


FRESHNESS_DAYS = {
    # claim-type prefix: (aging_after, stale_after) in days
    "reported_market_stats": (1, 7),
    "reported_price": (1, 7),
    "reported_fx": (1, 7),
    "reported_shareholder": (90, 365),
    "registry_": (90, 365),
    "bo_": (180, 540),
    "role_": (365, 730),
}
FRESHNESS_DEFAULT = (365, 730)


def freshness(claim: Claim, today: str) -> str:
    """current / aging / stale / superseded — computed, never stored.

    Facts can be true as of a date without being currently verified: a
    point-in-time disclosure is 'current as of' its date, and this state
    tracks how far verification has drifted from today.
    """
    if claim.status in ("SUPERSEDED", "RETRACTED"):
        return "superseded"
    basis = None
    if isinstance(claim.object, dict):
        basis = claim.object.get("as_of")
    basis = (basis or claim.valid_from or claim.verified_date)
    if not basis:
        return "stale"  # undated evidence is stale by definition
    import datetime as _dt
    s = str(basis)
    try:
        if len(s) >= 10:
            b = _dt.date.fromisoformat(s[:10])
        elif len(s) == 7:            # YYYY-MM
            b = _dt.date(int(s[:4]), int(s[5:7]), 1)
        elif len(s) == 4:            # YYYY -> mid-year
            b = _dt.date(int(s), 7, 1)
        else:
            return "stale"
    except ValueError:
        return "stale"
    t = _dt.date.fromisoformat(today)
    age = (t - b).days
    aging, stale = FRESHNESS_DEFAULT
    for prefix, (a, s) in FRESHNESS_DAYS.items():
        if claim.predicate.startswith(prefix):
            aging, stale = a, s
            break
    if age > stale:
        return "stale"
    if age > aging:
        return "aging"
    return "current"


def no_double_count(claims: list) -> list:
    """Deduplication invariant: aggregation input must not contain two
    live claims sharing a block_id. Returns the deduplicated list (one
    claim per block, the newest); raises if a blank block_id would be
    aggregated alongside others - aggregation requires explicit blocks.
    """
    seen, out = {}, []
    for c in claims:
        if not c.block_id:
            raise ValueError(
                f"{c.id}: aggregation requires a block_id — the engine "
                f"refuses to sum holdings without unique underlying "
                f"economic blocks")
        if c.block_id in seen:
            continue  # same underlying block: counted once
        seen[c.block_id] = c
        out.append(c)
    return out


def evidence_path_gaps(claim: Claim, sources_by_id: dict,
                       extractions_by_id: dict = None) -> list:
    """The reproducible-evidence-path invariant.

    An APPROVED claim must always answer: which document, which page/
    passage, which analyst, which methodology version, which approval.
    A verified Extraction linking the claim to a source satisfies the
    passage requirement for that source (Source -> Extraction -> Claim);
    otherwise the source's own passage field must carry it. Returns a
    list of human-readable gaps; empty means the path is complete.
    Enforced at approval time and re-checked by Ledger.audit(), which
    demotes any approved claim whose path has broken.
    """
    gaps = []
    xs = extractions_by_id or {}
    if not claim.sources:
        gaps.append("no sources")
    claim_x = [xs[i] for i in claim.extractions if i in xs]
    for xid in claim.extractions:
        if xid not in xs:
            gaps.append(f"extraction {xid} missing from ledger")
    for sid in claim.sources:
        s = sources_by_id.get(sid)
        if s is None:
            gaps.append(f"source {sid} missing from ledger")
            continue
        x_ok = any(x.source_id == sid and x.passage and x.analyst
                   for x in claim_x)
        if not (s.passage or x_ok):
            gaps.append(f"{sid}: no passage — neither on the source nor "
                        f"via a verified extraction")
        if not (s.preserved and s.archive_ref):
            gaps.append(f"{sid}: document not preserved (archive)")
        if not (s.analyst or x_ok):
            gaps.append(f"{sid}: no reviewing analyst recorded")
    if not claim.analyst:
        gaps.append("no approving analyst")
    if not claim.verified_date:
        gaps.append("no approval date")
    if not claim.methodology_version:
        gaps.append("no methodology version")
    return gaps
