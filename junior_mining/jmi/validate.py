"""Candidate validation: re-derive every claimed field from the cited text.

A schema-valid candidate is not thereby correct. For each candidate this module
independently re-reads the cited location and checks identity (company and
project), period/dates, value and scale, unit, currency, category, basis/scope,
sign, study qualifiers, and mining-specific distinctions. Outcomes:

  fail  -> workflow state "rejected", reasons preserved
  warn / missing information -> "needs_review", with a missing_reason
  all pass -> "source_matched" (the text is at the location and the automated
              checks agree; NOT independent verification of the claim)

The correct number with the wrong entity, period, currency, scale or scope is
therefore rejected or flagged (brief §17 case 1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from . import definitions as D
from .db import dumps
from .extract import Candidate, EntityAlias, mentions, norm_ws
from .quantities import (METAL, MASS, all_dates, as_of_dates, currency_code, interval, parse_number,
                         scale_exp)


@dataclass
class Validated:
    state: str
    checks: list
    company_id: str | None
    project_id: str | None
    normalized_value: str | None
    value_kind: str
    unit: str | None
    currency: str | None
    precision: tuple | None
    fields: dict
    qualifiers: dict
    transformations: list
    missing_reason: str | None
    equivalence_key: str
    evidence_type: str
    attribution: str


@dataclass
class VContext:
    company_id: str | None
    company_projects: dict            # project_id -> name for the doc's company
    aliases: list                     # EntityAlias, tenant-wide
    reporting_currency: str | None = None
    doc_heading: str = ""
    page_texts: dict = field(default_factory=dict)   # page_no -> text
    table_cells: dict = field(default_factory=dict)  # (table_index,row,col) -> text
    projects_by_company: dict = field(default_factory=dict)


class _Checks:
    def __init__(self):
        self.items = []

    def add(self, name, status, detail=""):
        self.items.append({"check": name, "status": status, "detail": detail})

    def ok(self, name, detail=""):
        self.add(name, "pass", detail)

    def fail(self, name, detail):
        self.add(name, "fail", detail)

    def warn(self, name, detail):
        self.add(name, "warn", detail)

    @property
    def failed(self):
        return [c for c in self.items if c["status"] == "fail"]

    @property
    def warned(self):
        return [c for c in self.items if c["status"] == "warn"]


def _scope_text(c: Candidate) -> str:
    return " ".join([c.quote, c.context, " ".join(c.location.footnotes or [])])


def equivalence_key(metric_id: str, company_id, project_id, fields: dict, qualifiers: dict) -> str:
    d = D.metric(metric_id)
    parts = {}
    for k in d.key_fields:
        if k == "company_id":
            parts[k] = company_id
        elif k == "project_id":
            parts[k] = project_id
        elif k == "metric_id":
            parts[k] = metric_id
        else:
            parts[k] = fields.get(k, qualifiers.get(k))
    return dumps(parts)


def _resolve_entities(c: Candidate, v: VContext, chk: _Checks, d: D.MetricDef):
    tr = []
    # Company
    company_id = c.company_hint if c.rule_id.startswith("market.") else v.company_id
    if c.rule_id.startswith("market."):
        if not company_id:
            chk.fail("entity", f"listing {c.qualifiers.get('listing')} is not recorded for any company in "
                               "this workspace")
            return None, None, tr
        chk.ok("entity", f"company resolved from listing {c.qualifiers.get('listing')}")
        return company_id, None, tr
    if not company_id:
        chk.fail("entity", "document is not linked to a company")
        return None, None, tr
    text = c.quote + " " + c.context
    found = mentions(text, v.aliases)
    own_projects = [a for a in found if a.kind == "project" and a.company_id == company_id]
    other_projects = [a for a in found if a.kind == "project" and a.company_id != company_id]
    other_companies = [a for a in found if a.kind == "company" and a.entity_id != company_id]
    # A passage about another company's project is not evidence about this one. The sentence is
    # re-derived from the stored page text, independently of whatever proposed the candidate.
    sentence = c.quote
    if c.location.char_start is not None and c.location.page_no in v.page_texts:
        from .extract import sentence_bounds
        ptxt = v.page_texts[c.location.page_no]
        sa, sb = sentence_bounds(ptxt, c.location.char_start, c.location.char_end)
        sentence = ptxt[sa:sb]
    sent_found = mentions(sentence + " " + c.quote, v.aliases)
    sent_other = [a for a in sent_found if (a.kind == "project" and a.company_id != company_id)
                  or (a.kind == "company" and a.entity_id != company_id)]
    sent_own = [a for a in sent_found if a.kind == "project" and a.company_id == company_id]
    if sent_other and not sent_own:
        names = ", ".join(sorted({a.alias for a in sent_other}))
        chk.fail("entity", f"the cited sentence refers to {names}, recorded as a different entity "
                           "than the document's company/project")
        return company_id, None, tr
    if d.level != "project":
        chk.ok("entity", "company from the document's company link")
        return company_id, None, tr
    project_id = None
    own_ids = sorted({a.entity_id for a in own_projects})
    if len(own_ids) == 1:
        project_id = own_ids[0]
        chk.ok("entity", "project named in the cited context")
    elif len(own_ids) > 1:
        chk.warn("entity", "several of the company's projects are named in the cited context; "
                           "reviewer must assign the project")
        return company_id, None, tr
    else:
        hint = c.project_mention
        if hint:
            hits = [a for a in v.aliases if a.kind == "project" and a.alias == hint]
            mine = [a for a in hits if a.company_id == company_id]
            if mine:
                project_id = mine[0].entity_id
                chk.ok("entity", f"project named in table title / heading ('{hint}')")
            elif hits:
                chk.fail("entity", f"'{hint}' is recorded as another company's project")
                return company_id, None, tr
        if not project_id:
            head = mentions(v.doc_heading, v.aliases)
            mine = sorted({a.entity_id for a in head if a.kind == "project" and a.company_id == company_id})
            if len(mine) == 1:
                project_id = mine[0]
                tr.append("project identified from the document heading")
                chk.ok("entity", "project named in the document heading")
            elif len(v.company_projects) == 1:
                project_id = next(iter(v.company_projects))
                chk.warn("entity", "no project is named near the value; the company has one recorded "
                                   "project — reviewer to confirm the assignment")
            else:
                chk.warn("entity", "project not identified in the cited context")
    if other_projects and not own_projects and project_id:
        chk.warn("entity", "the paragraph also names another company's project: "
                 + ", ".join(sorted({a.alias for a in other_projects})))
    if other_companies and not own_projects:
        chk.warn("entity", "the paragraph names another company: "
                 + ", ".join(sorted({a.alias for a in other_companies})))
    return company_id, project_id, tr


def _following_scale(c: Candidate, v: VContext) -> str | None:
    """Independently read the scale word printed right after the number."""
    loc = c.location
    if loc.char_start is None or c.raw_value is None:
        return None
    text = v.page_texts.get(loc.page_no, "")
    seg = text[loc.char_start:loc.char_end + 20]
    i = seg.find(c.raw_value)
    if i < 0:
        return None
    m = re.match(r"\s*(million|billion|thousand)\b", seg[i + len(c.raw_value):], re.I)
    return m.group(1).lower() if m else ""


def _preceding_currency(c: Candidate, v: VContext) -> str | None:
    loc = c.location
    if loc.char_start is None or c.raw_value is None:
        return None
    text = v.page_texts.get(loc.page_no, "")
    seg = text[loc.char_start:loc.char_end]
    i = seg.find(c.raw_value)
    if i < 0:
        return None
    m = re.search(r"(US\$|C\$|A\$|CDN\$|USD|CAD|\$)\s?$", seg[:i])
    return m.group(1) if m else None


def validate(c: Candidate, v: VContext) -> Validated:
    chk = _Checks()
    d = D.metric(c.metric_id)
    fields = dict(c.fields)
    quals = dict(c.qualifiers)
    tr = list(c.transformations)
    missing = []

    # 1. the quote is really at the cited location
    loc = c.location
    if loc.char_start is not None:
        txt = v.page_texts.get(loc.page_no, "")
        if txt[loc.char_start:loc.char_end] == c.quote and c.quote:
            chk.ok("source_text_present", f"page {loc.page_no}, characters {loc.char_start}–{loc.char_end}")
        else:
            chk.fail("source_text_present", "quoted text is not at the cited location")
    elif loc.table_index is not None:
        cell = v.table_cells.get((loc.table_index, loc.row_index, loc.col_index))
        if cell is not None and cell == c.quote:
            chk.ok("source_text_present", f"table {loc.table_index + 1}, row {loc.row_index + 1}, "
                                          f"column {loc.col_index + 1}" + (f" ({loc.cell_ref})" if loc.cell_ref else ""))
        else:
            chk.fail("source_text_present", "quoted cell text is not at the cited table cell")
    else:
        chk.fail("source_text_present", "no location")
    if c.raw_value and c.raw_value not in c.quote and c.raw_value not in ("no debt",) \
            and not c.raw_value.startswith("No ") and c.value_kind == "decimal":
        chk.fail("source_text_present", f"value token '{c.raw_value}' does not occur in the quote")

    # 2. identity
    company_id, project_id, etr = _resolve_entities(c, v, chk, d)
    tr.extend(etr)

    # 3. value, unit, scale, currency
    normalized, unit, currency, prec, kind = None, None, None, None, c.value_kind
    if d.dimension in ("status", "text"):
        kind = "enum"
        normalized = c.claimed_value
        if d.dimension == "status":
            if normalized not in D.PERMIT_STATUSES:
                chk.fail("value", f"unknown permit status '{normalized}'")
            else:
                derived = _status_from_quote(c.quote)
                if derived != normalized:
                    chk.fail("value", f"claimed status '{normalized}' is not what the quoted words state "
                                      f"('{derived or 'unclear'}'). An application is not an issued permit.")
                else:
                    chk.ok("value", D.PERMIT_STATUSES[normalized])
        else:
            chk.ok("value", f"disclosure quoted: {quals.get('label', normalized)}")
    elif c.raw_value in ("no debt",) or (c.raw_value or "").startswith("No "):
        if not re.search(r"\b[Nn]o\b", c.quote):
            chk.fail("value", "a zero is recorded only where the source states 'no'/'nil' explicitly")
        normalized, prec = "0", (Decimal(0), Decimal(0))
        unit = {"money": None, "mass": "t", "metal": "oz"}.get(d.dimension)
        if d.dimension == "money":
            currency = None
            quals["currency_note"] = "zero has no currency"
        chk.ok("value", "explicitly stated nil, recorded as zero")
    else:
        p = parse_number(c.raw_value or "")
        tr.extend(p.transformations)
        if p.value is None:
            chk.warn("value", "; ".join(p.warnings) or "value not readable")
            missing.append("value not readable from the source text (possible OCR/extraction error)")
        else:
            exp = 0
            if d.dimension in ("money", "count") and c.location.char_start is not None:
                claimed_scale = quals.get("scale_word", "")
                printed = _following_scale(c, v)
                if printed is not None and claimed_scale is not None and printed != (claimed_scale or ""):
                    chk.fail("scale", f"claimed scale '{claimed_scale or 'units'}' but the source prints "
                                      f"'{printed or 'no scale word'}' after the number")
                se = scale_exp(printed if printed is not None else claimed_scale)
                exp = se or 0
                if exp:
                    tr.append(f"scale '{printed or claimed_scale}' applied (×10^{exp})")
                if not any(x["check"] == "scale" for x in chk.items):
                    chk.ok("scale", f"×10^{exp}" if exp else "no scale word")
            if d.dimension == "money" or d.dimension == "price_per_metal":
                tok = quals.get("currency_token") or ""
                printed_cur = _preceding_currency(c, v) if c.location.char_start is not None else tok
                code = currency_code(tok) if tok else None
                if printed_cur is not None and tok and printed_cur.strip() != tok.strip():
                    chk.fail("currency", f"claimed currency token '{tok}' but the source prints '{printed_cur}'")
                if c.claimed_currency and code and c.claimed_currency != code:
                    chk.fail("currency", f"claimed currency {c.claimed_currency} but the source prints '{tok}' ({code})")
                if code is None or code == "?":
                    if tok == "$" and v.reporting_currency:
                        code = v.reporting_currency
                        tr.append(f"'$' read as {code} from the uploader-declared reporting currency")
                        chk.warn("currency", "currency printed only as '$'; uploader-declared reporting "
                                             f"currency {code} applied — reviewer to confirm")
                    else:
                        chk.warn("currency", f"currency not determinable from '{tok or 'nothing'}'")
                        missing.append("currency not stated unambiguously")
                        code = None
                elif not any(x["check"] == "currency" for x in chk.items):
                    chk.ok("currency", code)
                currency = code
            val = p.value * (Decimal(10) ** exp)
            if d.dimension == "mass":
                ut = (quals.get("unit_token") or "t").lower()
                cu, e2 = MASS.get(ut, (None, None))
                if cu is None:
                    chk.warn("unit", f"mass unit '{ut}' not recognised")
                    missing.append("unit not recognised")
                else:
                    val, exp = val * Decimal(10) ** e2, e2
                    if e2:
                        tr.append(f"unit {quals.get('unit_token')} → tonnes (×10^{e2})")
                    unit = "t"
                    chk.ok("unit", f"{quals.get('unit_token')} → t")
            elif d.dimension == "metal":
                ut = (quals.get("unit_token") or "oz").lower()
                cu, e2 = METAL.get(ut, (None, None))
                if cu is None:
                    chk.warn("unit", f"metal unit '{ut}' not recognised")
                    missing.append("unit not recognised")
                else:
                    val, exp = val * Decimal(10) ** e2, e2
                    if e2:
                        tr.append(f"unit {quals.get('unit_token')} → oz (×10^{e2})")
                    unit = "oz"
                    chk.ok("unit", f"{quals.get('unit_token')} → oz")
            elif d.dimension == "grade":
                unit = c.claimed_unit or quals.get("unit_token") or "g/t"
                if unit not in ("g/t", "%"):
                    chk.warn("unit", f"grade unit '{unit}' not recognised")
                else:
                    chk.ok("unit", unit)
            elif d.dimension == "length":
                unit = "m"
                chk.ok("unit", "m")
            elif d.dimension == "percent":
                unit = "%"
                chk.ok("unit", "%")
            elif d.dimension == "count":
                unit = "shares" if d.id != "average_daily_volume" else "shares/day"
                if val != val.to_integral_value():
                    chk.fail("value", "a share count must be a whole number")
            elif d.dimension == "money":
                unit = currency
            elif d.dimension == "price_per_metal":
                unit = f"{currency}/oz" if currency else "/oz"
            normalized = str(val.quantize(Decimal(1))) if val == val.to_integral_value() else str(val)
            prec = interval(val, p.decimals, exp)       # centred on the SCALED value
            if c.claimed_value is not None and Decimal(str(c.claimed_value)) != Decimal(normalized):
                chk.fail("value", f"claimed value {c.claimed_value} differs from the value derived from the "
                                  f"source text ({normalized})")
            elif not any(x["check"] == "value" for x in chk.items):
                chk.ok("value", normalized)
            if d.nonnegative and val < 0:
                chk.fail("sign", "negative value for a quantity that cannot be negative")

    # 4. dates and period
    scope_text = _scope_text(c)
    ctx_dates = set(all_dates(scope_text))
    if c.metric_id == "period_cash_outflow" and fields.get("period_end") and fields.get("period_months"):
        e = date.fromisoformat(fields["period_end"])
        m = int(fields.pop("period_months"))
        y, mo = e.year, e.month - m + 1
        while mo <= 0:
            mo += 12
            y -= 1
        fields["period_start"] = date(y, mo, 1).isoformat()
        tr.append(f"period start derived from '{m} months ended {e.isoformat()}'")
    for f in ("as_of_date", "effective_date", "period_end"):
        val = fields.get(f)
        if f in d.requires and not val:
            label = f.replace("_", " ")
            if c.metric_id == "disclosure_signal":
                continue
            chk.warn("period", f"{label} not stated in the cited context")
            missing.append(f"{label} not stated in the cited context")
        elif val:
            pub_fallback = any("publication date" in t for t in tr)
            local = getattr(c, "_sentence", None) or scope_text
            asof = as_of_dates(local) if f == "as_of_date" else []
            if val not in ctx_dates and not pub_fallback:
                chk.fail("period", f"claimed {f.replace('_', ' ')} {val} does not appear in the cited "
                                   f"context (dates found: {', '.join(sorted(ctx_dates)) or 'none'})")
            elif f == "as_of_date" and asof and val not in asof and not pub_fallback:
                chk.warn("period", f"claimed as-of date {val} appears, but the source introduces "
                                   f"{', '.join(asof)} as the as-at date; reviewer to confirm which applies")
                missing.append("as-of date ambiguous")
            elif val in ctx_dates or pub_fallback:
                chk.ok("period", f"{f.replace('_', ' ')} {val} appears in the cited context"
                       if not pub_fallback else f"{f.replace('_', ' ')} from publication date")
            else:
                chk.fail("period", f"claimed {f.replace('_', ' ')} {val} does not appear in the cited "
                                   f"context (dates found: {', '.join(sorted(ctx_dates)) or 'none'})")

    # 5. categories: resources are not reserves; inferred never becomes a reserve
    if c.metric_id in D.RESOURCE_METRICS | D.RESERVE_METRICS:
        cat = fields.get("resource_category")
        if not cat:
            chk.warn("category", "resource/reserve category not stated")
            missing.append("category not stated")
        elif cat not in d.allowed_categories:
            if c.metric_id in D.RESERVE_METRICS and cat in D.RESOURCE_CATEGORIES:
                chk.fail("category", f"'{D.CATEGORY_LABELS[cat]}' is a resource category, not a reserve "
                                     "category; resources are not reported as reserves")
            else:
                chk.fail("category", f"category '{cat}' is not valid for {d.label}")
        else:
            if _category_stated(cat, c):
                chk.ok("category", D.CATEGORY_LABELS[cat])
            else:
                chk.fail("category", f"claimed category {D.CATEGORY_LABELS[cat]} is not stated at the source")
        local = getattr(c, "_sentence", None) or (quals.get("table_title") or "") + " " + c.quote
        if fields.get("estimate_status") != "historical" and re.search(r"\bhistorical\b", local, re.I):
            chk.fail("category", "the source describes a historical estimate; it cannot be recorded "
                                 "as a current estimate")
    if c.metric_id == "historical_estimate_contained_metal":
        chk.ok("category", "historical estimate kept separate from current estimates")

    # 6. scope / basis
    if d.level == "project" and c.metric_id in (D.RESOURCE_METRICS | D.RESERVE_METRICS | {"npv"}):
        b = fields.get("scope_basis")
        if not b:
            chk.warn("scope", "ownership basis (100% vs attributable) not stated in the cited context")
            missing.append("ownership basis not stated")
        elif b == "100%" and not re.search(r"100\s*%\s*(?:project\s+)?basis", scope_text, re.I):
            chk.fail("scope", "claimed 100% basis is not stated in the cited context")
        elif b == "attributable" and not re.search(r"attributable", scope_text, re.I):
            chk.fail("scope", "claimed attributable basis is not stated in the cited context")
        else:
            chk.ok("scope", f"{b} basis stated")

    # 7. study qualifiers
    if c.metric_id in ("npv", "irr", "initial_capex", "aisc", "commodity_price_assumption",
                       "plant_recovery_assumption"):
        st = fields.get("study_type")
        if not st:
            chk.warn("study", "study type not stated near the value")
            missing.append("study type not stated")
        elif quals.get("study_type_scope") == "page":
            chk.warn("study", "study type found elsewhere on the page, not in the value's paragraph")
        else:
            chk.ok("study", st.upper())
        if c.metric_id in ("npv", "irr"):
            tb = fields.get("tax_basis")
            pat = {"after_tax": r"after[- ]tax", "pre_tax": r"pre[- ]tax"}.get(tb or "", "$^")
            if not tb or not re.search(pat, c.quote, re.I):
                chk.fail("study", f"tax basis '{tb}' is not stated in the quote")
        if c.metric_id == "npv":
            dr = fields.get("discount_rate")
            if not dr or not re.search(re.escape(str(dr)) + r"\s*%", c.quote):
                chk.fail("study", f"discount rate '{dr}' is not stated in the quote")

    # 8. drilling: true width only when stated
    if c.metric_id == "true_width":
        if not re.search(r"true\s+width\s+of\s+" + re.escape(c.raw_value or "~") + r"\s*(?:m|metres)", c.context, re.I):
            chk.fail("drilling", "true width is not explicitly stated at the source; an intercept "
                                 "length is not a true width")
        else:
            chk.ok("drilling", "true width explicitly stated")
    if c.metric_id == "drill_intercept_length":
        chk.ok("drilling", "recorded as down-hole length; true width: " + str(quals.get("true_width_status")))

    if c.metric_id == "met_test_recovery" and not quals.get("test_type"):
        chk.warn("metallurgy", "test conditions (test type) not stated near the result")

    # outcome
    if chk.failed:
        state = "rejected"
    elif chk.warned or missing:
        state = "needs_review"
    else:
        state = "source_matched"
    evidence = c.evidence_type or d.default_evidence
    key = equivalence_key(c.metric_id, company_id, project_id, fields, quals)
    return Validated(state=state, checks=chk.items, company_id=company_id, project_id=project_id,
                     normalized_value=normalized, value_kind=kind, unit=unit, currency=currency,
                     precision=prec, fields=fields, qualifiers=quals, transformations=tr,
                     missing_reason="; ".join(missing) or None, equivalence_key=key,
                     evidence_type=evidence, attribution=c.attribution)


def _category_stated(cat: str, c: Candidate) -> bool:
    """Re-derive the category from the row label (tables) or the quote (prose)."""
    from .extract import category_of
    if c.location.row_header:
        derived, _ = category_of(c.location.row_header)
        return derived == cat
    q = norm_ws(c.quote)
    combined = {"measured_indicated": r"Measured\s*(?:&|and)\s*Indicated",
                "proven_probable": r"Proven\s*(?:&|and)\s*Probable"}
    if cat in combined:
        return bool(re.search(combined[cat], q, re.I))
    word = D.CATEGORY_LABELS[cat]
    for m in re.finditer(r"\b" + word + r"\b", q, re.I):
        before, after = q[:m.start()], q[m.end():]
        if re.search(r"(?:&|and)\s*$", before) or re.match(r"\s*(?:&|and)\s", after):
            continue          # part of a combined category phrase
        return True
    return False


def _status_from_quote(q: str) -> str | None:
    ql = norm_ws(q).lower()
    if re.search(r"\b(issued|granted|received)\b", ql):
        return "issued"
    if "conditional" in ql:
        return "conditional_approval"
    if re.search(r"accepted|deemed complete", ql):
        return "accepted_for_review"
    if re.search(r"has not", ql):
        return "not_applied"
    if re.search(r"submitted|filed", ql):
        return "applied"
    return None
