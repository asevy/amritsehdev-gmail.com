"""Domain vocabulary and the canonical metric-definition registry.

A label must not silently change meaning across companies, so every fact and
calculation is stamped with the definition id AND version it was produced
under (the "history, not a flag" principle adapted from Vision//Edge's
certification records). Changing a definition means adding a version, never
editing one in place.

These definitions are a development baseline written from general industry
usage. They have NOT been reviewed by a Qualified Person, securities counsel
or a mining-disclosure specialist; automated extraction against them is not
professional certification or a compliance opinion (brief §8).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

REGISTRY_VERSION = "2026-11-17.1"

# Evidence type (what kind of statement) and workflow state (what checks were
# completed) are SEPARATE axes. A forecast can be source-matched and approved
# and remain a forecast.
EVIDENCE_TYPES = {
    "observed": "Measured/observed (e.g. a market price on a stated date)",
    "reported": "Reported by the issuer or a named third party",
    "calculated": "Calculated by this application from recorded inputs",
    "forecast": "Estimate or forecast (study economics, management targets)",
    "unknown_disputed": "Unknown or disputed",
}

WORKFLOW_STATES = {
    "candidate": "Candidate — proposed by extraction; no checks completed",
    "source_matched": "Source-matched — the quoted text was found at the cited location and the "
                      "automated identity/period/unit checks passed. Not independently verified.",
    "needs_review": "Needs review — at least one automated check could not be completed",
    "conflicting": "Conflicting — another source reports a different value for the same defined metric",
    "reviewer_approved": "Reviewer-approved — a reviewer confirmed the extraction matches the source. "
                         "This does not independently establish the underlying geological, legal "
                         "or commercial claim.",
    "superseded": "Superseded — replaced by a later correction or restatement (preserved)",
    "rejected": "Rejected — failed a check or was rejected by a reviewer (preserved)",
}

TRANSITIONS = {
    "candidate": {"source_matched", "needs_review", "rejected", "conflicting"},
    "source_matched": {"reviewer_approved", "rejected", "needs_review", "conflicting", "superseded"},
    "needs_review": {"reviewer_approved", "rejected", "conflicting", "superseded"},
    "conflicting": {"reviewer_approved", "rejected", "superseded", "needs_review"},
    "reviewer_approved": {"superseded", "conflicting", "needs_review", "rejected"},
    "superseded": set(),
    "rejected": set(),
}

CURRENT_STATES = ("source_matched", "needs_review", "conflicting", "reviewer_approved")

ATTRIBUTIONS = {
    "issuer_management": "Issuer / management statement",
    "qualified_person": "Issuer disclosure prepared under a named qualified person",
    "regulator": "Regulator or official record",
    "market_data": "Market-data file (as uploaded; source stated in the file)",
    "third_party": "Named third party",
    "analyst": "Analyst entry",
}

RESOURCE_CATEGORIES = ("measured", "indicated", "measured_indicated", "inferred")
RESERVE_CATEGORIES = ("proven", "probable", "proven_probable")
CATEGORY_LABELS = {
    "measured": "Measured", "indicated": "Indicated", "measured_indicated": "Measured & Indicated",
    "inferred": "Inferred", "proven": "Proven", "probable": "Probable",
    "proven_probable": "Proven & Probable",
}

STAGES = ("exploration", "resource", "pea", "pfs", "fs", "construction", "operating")
STAGE_LABELS = {"exploration": "Exploration", "resource": "Resource definition",
                "pea": "Preliminary economic assessment", "pfs": "Pre-feasibility",
                "fs": "Feasibility", "construction": "Construction", "operating": "Operating"}
STAGE_GROUP = {"exploration": "exploration", "resource": "resource", "pea": "study",
               "pfs": "study", "fs": "study", "construction": "build", "operating": "producing"}

# Ordered by process position. Position does NOT imply the next step occurs.
PERMIT_STATUSES = {
    "not_applied": "No application disclosed",
    "applied": "Application submitted",
    "accepted_for_review": "Application accepted for review",
    "conditional_approval": "Conditional approval",
    "issued": "Authorization issued",
    "refused": "Refused",
    "withdrawn": "Withdrawn",
}

RISK_CATEGORIES = {
    "geology_resource": "Geology / resource quality",
    "metallurgy_process": "Metallurgy / process",
    "engineering_construction": "Engineering / construction",
    "infrastructure": "Infrastructure",
    "permitting_environment": "Permitting / environment",
    "land_community": "Land / community / Indigenous relationships",
    "management_governance": "Management / governance",
    "financing_shareholder": "Financing / shareholder outcomes",
    "commercial_jurisdiction": "Commercial / jurisdiction",
    "execution_catalysts": "Execution / catalysts",
    "liquidity_portfolio": "Liquidity / portfolio",
    "relative_value": "Relative value / opportunity cost",
    "evidence_quality": "Evidence quality",
}

RISK_STATUSES = {
    "open_question": "Open question — not an established adverse finding",
    "documented_finding": "Documented finding — supported by cited evidence and reviewer-confirmed",
    "mitigated": "Mitigated — mitigant documented",
    "resolved": "Resolved",
    "dismissed": "Dismissed with reason",
}


@dataclass(frozen=True)
class MetricDef:
    id: str
    version: int
    label: str
    dimension: str      # money | count | mass | metal | grade | length | percent | price_per_metal | status | text
    level: str          # company | project
    default_evidence: str
    requires: tuple = ()          # fields that must be established for source-match
    key_fields: tuple = ()        # fields that define "the same metric" for reconciliation
    allowed_categories: tuple = ()
    nonnegative: bool = True
    display_decimals: int = 2
    display_divisor: str = "1"    # e.g. "1000000" to display millions
    display_suffix: str = ""
    definition: str = ""
    caution: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


_BASE_KEY = ("company_id", "project_id", "metric_id")

_DEFS = [
    MetricDef("share_price", 1, "Share price (close)", "money", "company", "observed",
              requires=("as_of_date", "currency"), key_fields=_BASE_KEY + ("as_of_date", "listing"),
              display_decimals=2,
              definition="Closing price of one common share on the stated listing and date."),
    MetricDef("average_daily_volume", 1, "Average daily traded volume", "count", "company", "observed",
              requires=("as_of_date",), key_fields=_BASE_KEY + ("as_of_date", "window", "listing"),
              display_decimals=0,
              definition="Average shares traded per day over the stated window, as given in the uploaded file."),
    MetricDef("shares_outstanding_basic", 1, "Basic shares outstanding", "count", "company", "reported",
              requires=("as_of_date",), key_fields=_BASE_KEY + ("as_of_date",), display_decimals=0,
              definition="Issued and outstanding common shares on the stated date. Excludes warrants, "
                         "options and other convertibles."),
    MetricDef("warrants_outstanding", 1, "Warrants outstanding (tranche)", "count", "company", "reported",
              requires=("as_of_date",),
              key_fields=_BASE_KEY + ("as_of_date", "exercise_price", "expiry"), display_decimals=0,
              definition="Number of warrants in one tranche, with its exercise price and expiry. "
                         "Exercise proceeds are hypothetical, not cash held."),
    MetricDef("options_outstanding", 1, "Options outstanding (tranche)", "count", "company", "reported",
              requires=("as_of_date",),
              key_fields=_BASE_KEY + ("as_of_date", "exercise_price", "expiry"), display_decimals=0,
              definition="Number of stock options in one tranche with its exercise price."),
    MetricDef("cash_unrestricted", 1, "Cash and cash equivalents (unrestricted)", "money", "company",
              "reported", requires=("as_of_date", "currency"), key_fields=_BASE_KEY + ("as_of_date",),
              display_decimals=1, display_divisor="1000000", display_suffix=" million",
              definition="Unrestricted cash and cash equivalents on the stated balance-sheet date. "
                         "Dated cash is not current cash.",
              caution="Restricted cash is a separate metric and is excluded from enterprise value."),
    MetricDef("cash_restricted", 1, "Restricted cash", "money", "company", "reported",
              requires=("as_of_date", "currency"), key_fields=_BASE_KEY + ("as_of_date",),
              display_decimals=1, display_divisor="1000000", display_suffix=" million",
              definition="Cash subject to restrictions (e.g. reclamation bonds) on the stated date."),
    MetricDef("total_debt", 1, "Total debt", "money", "company", "reported",
              requires=("as_of_date", "currency"), key_fields=_BASE_KEY + ("as_of_date",),
              display_decimals=1, display_divisor="1000000", display_suffix=" million",
              definition="Borrowings (loans, notes, drawn facilities) on the stated date. A disclosed "
                         "'no debt' is recorded as zero; silence is recorded as unknown."),
    MetricDef("period_cash_outflow", 1, "Cash used in operating and investing activities", "money",
              "company", "reported", requires=("period_end", "currency"),
              key_fields=_BASE_KEY + ("period_start", "period_end"), display_decimals=1,
              display_divisor="1000000", display_suffix=" million",
              definition="Cash used in operating and investing activities over the stated period."),
    MetricDef("resource_tonnage", 1, "Mineral resource tonnage", "mass", "project", "reported",
              requires=("effective_date", "resource_category"),
              key_fields=_BASE_KEY + ("effective_date", "resource_category", "scope_basis",
                                      "reporting_basis", "zone", "estimate_status"),
              allowed_categories=RESOURCE_CATEGORIES, display_decimals=1,
              display_divisor="1000000", display_suffix=" Mt",
              definition="Tonnes in one resource category, on the stated effective date and basis."),
    MetricDef("resource_grade", 1, "Mineral resource grade", "grade", "project", "reported",
              requires=("effective_date", "resource_category"),
              key_fields=_BASE_KEY + ("effective_date", "resource_category", "scope_basis",
                                      "reporting_basis", "zone", "estimate_status"),
              allowed_categories=RESOURCE_CATEGORIES, display_decimals=2,
              definition="Average grade for one resource category."),
    MetricDef("resource_contained_metal", 1, "Mineral resource contained metal", "metal", "project",
              "reported", requires=("effective_date", "resource_category"),
              key_fields=_BASE_KEY + ("effective_date", "resource_category", "scope_basis",
                                      "reporting_basis", "zone", "estimate_status"),
              allowed_categories=RESOURCE_CATEGORIES, display_decimals=0,
              display_divisor="1000", display_suffix=" koz",
              definition="Contained metal in one resource category. Categories are never added "
                         "together automatically; Inferred is never combined with Measured & Indicated.",
              caution="Mineral resources are not mineral reserves and do not have demonstrated "
                      "economic viability."),
    MetricDef("reserve_tonnage", 1, "Mineral reserve tonnage", "mass", "project", "reported",
              requires=("effective_date", "resource_category"),
              key_fields=_BASE_KEY + ("effective_date", "resource_category", "scope_basis", "zone"),
              allowed_categories=RESERVE_CATEGORIES, display_decimals=1,
              display_divisor="1000000", display_suffix=" Mt",
              definition="Tonnes in one reserve category (Proven/Probable only)."),
    MetricDef("reserve_grade", 1, "Mineral reserve grade", "grade", "project", "reported",
              requires=("effective_date", "resource_category"),
              key_fields=_BASE_KEY + ("effective_date", "resource_category", "scope_basis", "zone"),
              allowed_categories=RESERVE_CATEGORIES, display_decimals=2,
              definition="Average grade for one reserve category."),
    MetricDef("reserve_contained_metal", 1, "Mineral reserve contained metal", "metal", "project",
              "reported", requires=("effective_date", "resource_category"),
              key_fields=_BASE_KEY + ("effective_date", "resource_category", "scope_basis", "zone"),
              allowed_categories=RESERVE_CATEGORIES, display_decimals=0,
              display_divisor="1000", display_suffix=" koz",
              definition="Contained metal in one reserve category (Proven/Probable only)."),
    MetricDef("historical_estimate_contained_metal", 1, "Historical estimate (not current)", "metal",
              "project", "reported", requires=(),
              key_fields=_BASE_KEY + ("source_year",), display_decimals=0,
              display_divisor="1000", display_suffix=" koz",
              definition="A historical estimate that a qualified person has not classified as a "
                         "current mineral resource. Never compared with current estimates."),
    MetricDef("npv", 1, "Net present value (study)", "money", "project", "forecast",
              requires=("effective_date", "currency", "study_type", "tax_basis", "discount_rate"),
              key_fields=_BASE_KEY + ("effective_date", "study_type", "tax_basis", "discount_rate",
                                      "scope_basis", "price_case"),
              nonnegative=False, display_decimals=0, display_divisor="1000000",
              display_suffix=" million",
              definition="Study NPV with its tax basis, discount rate, commodity-price case, study type "
                         "and effective date. Project NPV is not company equity value.",
              caution="A PEA may include Inferred resources and is preliminary in nature."),
    MetricDef("irr", 1, "Internal rate of return (study)", "percent", "project", "forecast",
              requires=("effective_date", "study_type", "tax_basis"),
              key_fields=_BASE_KEY + ("effective_date", "study_type", "tax_basis", "price_case"),
              nonnegative=False, display_decimals=1,
              definition="Study IRR with tax basis and price case."),
    MetricDef("initial_capex", 1, "Initial capital cost (study)", "money", "project", "forecast",
              requires=("effective_date", "currency", "study_type"),
              key_fields=_BASE_KEY + ("effective_date", "study_type"), display_decimals=0,
              display_divisor="1000000", display_suffix=" million",
              definition="Pre-production capital estimate from the stated study."),
    MetricDef("aisc", 1, "All-in sustaining cost (study or reported)", "price_per_metal", "project",
              "forecast", requires=("currency", "study_type"),
              key_fields=_BASE_KEY + ("effective_date", "study_type", "period_end"),
              display_decimals=0,
              definition="AISC per ounce as defined by the issuer. Definitions differ between "
                         "issuers; values are compared only with that caveat shown."),
    MetricDef("commodity_price_assumption", 1, "Commodity price assumption (study base case)",
              "price_per_metal", "project", "forecast",
              requires=("currency", "study_type"),
              key_fields=_BASE_KEY + ("effective_date", "study_type", "price_case"), display_decimals=0,
              definition="Base-case commodity price used by the study."),
    MetricDef("met_test_recovery", 1, "Metallurgical test recovery", "percent", "project", "reported",
              requires=(), key_fields=_BASE_KEY + ("test_type", "bound"), display_decimals=1,
              definition="Recovery measured in laboratory testwork under the stated test conditions. "
                         "Not the same as proposed plant performance."),
    MetricDef("plant_recovery_assumption", 1, "Process recovery assumed in study", "percent", "project",
              "forecast", requires=("study_type",), key_fields=_BASE_KEY + ("study_type",),
              display_decimals=1, definition="Recovery assumed for the proposed plant in a study."),
    MetricDef("drill_intercept_length", 1, "Drill intercept length (core length)", "length", "project",
              "reported", requires=(), key_fields=_BASE_KEY + ("hole_id", "interval"),
              display_decimals=1,
              definition="Down-hole sample length. Not true width. Where true width is unknown it "
                         "stays unknown."),
    MetricDef("drill_intercept_grade", 1, "Drill intercept grade", "grade", "project", "reported",
              requires=(), key_fields=_BASE_KEY + ("hole_id", "interval"), display_decimals=2,
              definition="Grade over the stated down-hole interval."),
    MetricDef("true_width", 1, "True width (explicitly stated)", "length", "project", "reported",
              requires=(), key_fields=_BASE_KEY + ("hole_id", "interval"), display_decimals=1,
              definition="True thickness, only when the source states it explicitly."),
    MetricDef("permit_status", 1, "Permit / authorization status", "status", "project", "reported",
              requires=("as_of_date",), key_fields=_BASE_KEY + ("permit", "as_of_date"),
              display_decimals=0,
              definition="Status of a named authorization. Application, acceptance for review, "
                         "conditional approval and issuance are distinct states."),
    MetricDef("ownership_interest", 1, "Ownership interest in project", "percent", "project", "reported",
              requires=(), key_fields=_BASE_KEY + ("as_of_date",), display_decimals=1,
              definition="The company's percentage interest in the project on the stated date."),
    MetricDef("disclosure_signal", 1, "Disclosure signal", "text", "company", "reported",
              requires=(), key_fields=_BASE_KEY + ("signal", "as_of_date"), display_decimals=0,
              definition="A specific disclosure (e.g. going-concern material uncertainty) quoted from "
                         "the source. It prompts diligence; it is not a verdict."),
]

METRICS: dict[str, MetricDef] = {d.id: d for d in _DEFS}

RESOURCE_METRICS = {"resource_tonnage", "resource_grade", "resource_contained_metal"}
RESERVE_METRICS = {"reserve_tonnage", "reserve_grade", "reserve_contained_metal"}


def metric(mid: str) -> MetricDef:
    if mid not in METRICS:
        raise KeyError(f"no metric definition: {mid}")
    return METRICS[mid]


def registry() -> dict:
    return {"registry_version": REGISTRY_VERSION,
            "metrics": {k: v.as_dict() for k, v in METRICS.items()},
            "evidence_types": EVIDENCE_TYPES, "workflow_states": WORKFLOW_STATES,
            "permit_statuses": PERMIT_STATUSES, "stages": STAGE_LABELS,
            "risk_categories": RISK_CATEGORIES, "risk_statuses": RISK_STATUSES}
