"""Deterministic, versioned calculations with recorded inputs.

* The language model is never the arithmetic authority; nothing here calls one.
* Inputs are reviewer-approved facts and analyst assumptions with rationale.
  A missing input WITHHOLDS the result and says what is missing. Nothing is
  zero-filled, and nothing is inferred to make a valuation work.
* Each result stores formula id + version, every input value with its unit,
  date and source id, warnings (e.g. date gaps) and caveats. recompute()
  re-runs the pure function on the stored inputs and must reproduce the stored
  output exactly (brief §17 case 10).
* Market capitalisation is not enterprise value. Warrant proceeds are not cash
  held. Project NPV is not company equity value, and multiplying by ownership
  does not complete the bridge. Resource categories are never added across
  M&I and Inferred.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from . import config, entities, facts as F, lineage
from .auth import Actor
from .definitions import CATEGORY_LABELS
from .quantities import fmt, quantize
from .store import Invalid, Store

ROUNDING = "ROUND_HALF_EVEN at display only; stored outputs keep full Decimal precision (34 digits)"


@dataclass(frozen=True)
class Formula:
    id: str
    version: int
    label: str
    expression: str
    output: str
    display_decimals: int
    display_divisor: str = "1"
    definition: str = ""


FORMULAS = {f.id: f for f in [
    Formula("market_cap", 1, "Basic market capitalisation", "share_price × basic_shares",
            "currency", 1, "1000000",
            "Price on a stated date times basic shares on a stated date. Not enterprise value. "
            "Excludes warrants, options and convertibles."),
    Formula("enterprise_value", 1, "Enterprise value (explicit bridge)",
            "market_cap + total_debt − unrestricted_cash (each converted with a stated FX rate if needed)",
            "currency", 1, "1000000",
            "Each component is dated. Restricted cash is excluded. Warrant proceeds are not added. "
            "No other adjustments unless entered as assumptions."),
    Formula("diluted_shares", 1, "Diluted share scenario", "basic_shares + Σ included tranches",
            "shares", 0, "1",
            "Scenario: which tranches are assumed exercised is a stated parameter. Exercise proceeds are "
            "reported separately as hypothetical and are not cash held."),
    Formula("runway", 1, "Cash runway scenario (from the cash date)",
            "unrestricted_cash ÷ monthly_spend", "months", 1, "1",
            "Months from the balance-sheet date, not from today. Spending is an assumption or a "
            "historical average; future spending may differ."),
    Formula("attributable_npv", 1, "Attributable share of reported project NPV",
            "project_npv(100% basis) × ownership_interest", "currency", 0, "1000000",
            "Not company equity value. Excludes corporate costs, cash, debt, financing dilution, "
            "corporate taxes and the time and risk to reach production."),
    Formula("equity_bridge", 1, "Project-to-equity bridge (analyst scenario)",
            "attributable_npv + unrestricted_cash − total_debt − corporate_costs_pv − funding_dilution_adjustment",
            "currency", 0, "1000000",
            "Computed only when every component is specified. A scenario, not a price target or a "
            "recommendation."),
    Formula("ev_per_contained_oz", 1, "EV per contained ounce (single category set)",
            "enterprise_value ÷ contained_oz(category set, basis)", "currency/oz", 2, "1",
            "Uses one category set only (M&I, or P&P). Inferred is never added. Basis (100% or "
            "attributable) and effective date are stated."),
    Formula("inferred_share", 1, "Inferred share of reported resource ounces",
            "inferred_oz ÷ (measured_indicated_oz + inferred_oz)", "percent", 1, "1",
            "Objective composition ratio on one effective date and basis. Not a quality grade."),
    Formula("liquidity_days", 1, "Days to trade a position at stated participation rates",
            "position_shares ÷ (ADV × participation_rate)", "days", 1, "1",
            "Mechanical scenario over the stated ADV window. Market impact, liquidity changes and "
            "block trades are not modelled; there is no universally valid exit estimate."),
    Formula("fx_convert", 1, "Currency conversion", "amount × fx_rate", "currency", 2, "1",
            "Uses an analyst-entered rate with its source and date."),
]}


@dataclass
class CalcInput:
    name: str
    kind: str              # fact | assumption | calculation | parameter
    ref_id: str | None
    value: str | None
    unit: str | None = None
    date: str | None = None
    note: str = ""


@dataclass
class CalcResult:
    formula_id: str
    label: str
    status: str = "computed"          # computed | withheld
    value: Decimal | None = None
    unit: str | None = None
    inputs: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    caveats: list = field(default_factory=list)
    parameters: dict = field(default_factory=dict)
    calc_id: str | None = None

    @property
    def formula(self) -> Formula:
        return FORMULAS[self.formula_id]

    def display(self) -> str:
        if self.status != "computed" or self.value is None:
            return "Withheld — " + "; ".join(self.missing)
        f = self.formula
        s = fmt(self.value, f.display_decimals, f.display_divisor)
        suffix = " million" if f.display_divisor == "1000000" else ""
        unit = self.unit or ""
        if f.output == "percent":
            return f"{s}%"
        if f.output in ("months", "days", "shares"):
            return f"{s} {f.output}"
        return f"{unit} {s}{suffix}".strip()

    def withhold(self, what: str) -> "CalcResult":
        self.status = "withheld"
        self.value = None
        self.missing.append(what)
        return self


# ------------------------------------------------------------------ pure functions
def f_market_cap(price: Decimal, shares: Decimal) -> Decimal:
    return price * shares


def f_enterprise_value(mcap: Decimal, debt: Decimal, cash: Decimal) -> Decimal:
    return mcap + debt - cash


def f_runway(cash: Decimal, monthly: Decimal) -> Decimal:
    if monthly <= 0:
        raise ValueError("monthly spend must be positive")
    return cash / monthly


def f_attributable(npv: Decimal, pct: Decimal) -> Decimal:
    return npv * pct / Decimal(100)


def f_ratio(num: Decimal, den: Decimal) -> Decimal:
    if den == 0:
        raise ValueError("denominator is zero")
    return num / den


PURE = {
    "market_cap": lambda i: f_market_cap(i["share_price"], i["basic_shares"]),
    "enterprise_value": lambda i: f_enterprise_value(i["market_cap"], i["total_debt"], i["unrestricted_cash"]),
    "runway": lambda i: f_runway(i["unrestricted_cash"], i["monthly_spend"]),
    "attributable_npv": lambda i: f_attributable(i["project_npv"], i["ownership_pct"]),
    "equity_bridge": lambda i: (i["attributable_npv"] + i["unrestricted_cash"] - i["total_debt"]
                                - i["corporate_costs_pv"] - i["funding_dilution_adjustment"]),
    "ev_per_contained_oz": lambda i: f_ratio(i["enterprise_value"], i["contained_oz"]),
    "inferred_share": lambda i: f_ratio(i["inferred_oz"], i["measured_indicated_oz"] + i["inferred_oz"]) * 100,
    "diluted_shares": lambda i: i["basic_shares"] + sum((v for k, v in i.items() if k.startswith("tranche:")),
                                                        Decimal(0)),
    "liquidity_days": lambda i: f_ratio(i["position_shares"], i["adv"] * i["participation_rate"]),
    "fx_convert": lambda i: i["amount"] * i["fx_rate"],
}


def _converted_inputs(inputs: list) -> dict:
    """Values as used by the pure function (after any recorded conversion)."""
    out = {}
    for x in inputs:
        if x["value"] is None:
            continue
        out[x["name"]] = Decimal(x["value"])
    return out


# ------------------------------------------------------------------ helpers
def _fact_input(name: str, f: dict, value: Decimal | None = None, note: str = "") -> CalcInput:
    return CalcInput(name, "fact", f["id"], str(value if value is not None else Decimal(f["normalized_value"])),
                     f["unit"] or f["currency"], f["as_of_date"] or f["effective_date"] or f["period_end"], note)


def _need_fact(r: CalcResult, store, actor, company_id, metric, label, project_id=None, **match):
    store.get(actor, "companies", company_id)          # 404 for another tenant's company
    f = F.latest(store, actor, company_id, metric, project_id, approved_only=True, **match)
    if f is None:
        pending = F.latest(store, actor, company_id, metric, project_id, approved_only=False, **match)
        if pending:
            r.withhold(f"{label}: extracted but not reviewer-approved (state: {pending['workflow_state']})")
        else:
            r.withhold(f"{label}: not established in documents reviewed")
    return f


def assumption(store: Store, actor: Actor, name: str, company_id: str | None = None) -> dict | None:
    rows = [a for a in store.find(actor, "assumptions", name=name, superseded_by=None)
            if a["company_id"] in (company_id, None)]
    rows.sort(key=lambda a: (a["company_id"] is None, a["created_at"]))
    return rows[0] if rows else None


def set_assumption(store: Store, actor: Actor, name: str, value: str, rationale: str, *, unit: str = "",
                   company_id: str | None = None, as_of_date: str | None = None, source: str = "") -> dict:
    if not rationale.strip():
        raise Invalid("every assumption needs a rationale")
    Decimal(str(value))
    if name.startswith("fx_") and (not source.strip() or not as_of_date):
        raise Invalid("an exchange rate needs its source and date")
    with store.db.tx():
        prior = [a for a in store.find(actor, "assumptions", name=name, superseded_by=None)
                 if a["company_id"] == company_id]
        row = store.insert(actor, "assumptions", {
            "company_id": company_id, "name": name, "value": str(value), "unit": unit, "as_of_date": as_of_date,
            "source": source, "rationale": rationale, "created_by": actor.user_id, "created_at": config.iso_now()})
        for p in prior:
            store.update(actor, "assumptions", p["id"], {"superseded_by": row["id"]})
            lineage.invalidate(store, actor, "assumption", p["id"], f"assumption '{name}' replaced")
        store.audit(actor, "assumption_set", row["id"], f"{name}={value}")
    return row


def _to_currency(r: CalcResult, store, actor, amount: Decimal, frm: str | None, to: str, name: str,
                 company_id) -> Decimal | None:
    if amount == 0 or frm is None or frm == to:
        return amount
    a = assumption(store, actor, f"fx_{frm.lower()}_{to.lower()}", company_id)
    if not a:
        r.withhold(f"{name}: reported in {frm}; no {frm}→{to} exchange rate entered (rate, source and date required)")
        return None
    rate = Decimal(a["value"])
    r.inputs.append(CalcInput(f"fx_{frm}_{to}", "assumption", a["id"], a["value"], f"{to} per {frm}",
                              a["as_of_date"], f"source: {a['source']}"))
    r.warnings.append(f"{name} converted from {frm} at {a['value']} {to}/{frm} ({a['source']}, {a['as_of_date']})")
    return amount * rate


def _days(a: str | None, b: str | None) -> int | None:
    if not a or not b:
        return None
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


# ------------------------------------------------------------------ formulas
def market_cap(store: Store, actor: Actor, company_id: str, on_or_before: str | None = None) -> CalcResult:
    r = CalcResult("market_cap", FORMULAS["market_cap"].label)
    price = _need_fact(r, store, actor, company_id, "share_price", "share price", on_or_before=on_or_before)
    shares = _need_fact(r, store, actor, company_id, "shares_outstanding_basic", "basic shares outstanding")
    r.caveats.append("Basic market capitalisation; not enterprise value; excludes dilutive securities.")
    if r.status == "withheld":
        return r
    r.inputs = [_fact_input("share_price", price), _fact_input("basic_shares", shares)]
    r.value = f_market_cap(Decimal(price["normalized_value"]), Decimal(shares["normalized_value"]))
    r.unit = price["currency"]
    gap = _days(shares["as_of_date"], price["as_of_date"])
    if gap:
        r.warnings.append(f"basic shares as at {shares['as_of_date']}; price as at {price['as_of_date']} "
                          f"({abs(gap)} days apart) — later issuances are not reflected")
    r.parameters = {"price_date": price["as_of_date"], "listing": price["qualifiers"].get("listing")}
    return r


def enterprise_value(store: Store, actor: Actor, company_id: str, on_or_before: str | None = None) -> CalcResult:
    r = CalcResult("enterprise_value", FORMULAS["enterprise_value"].label)
    mc = market_cap(store, actor, company_id, on_or_before)
    if mc.status != "computed":
        for m in mc.missing:
            r.withhold(m)
        return r
    debt = _need_fact(r, store, actor, company_id, "total_debt", "total debt (silence is not zero)")
    cash = _need_fact(r, store, actor, company_id, "cash_unrestricted", "unrestricted cash")
    if r.status == "withheld":
        return r
    cur = mc.unit
    d_val = _to_currency(r, store, actor, Decimal(debt["normalized_value"]), debt["currency"], cur, "total debt",
                         company_id)
    c_val = _to_currency(r, store, actor, Decimal(cash["normalized_value"]), cash["currency"], cur,
                         "unrestricted cash", company_id)
    if r.status == "withheld":
        return r
    mc_saved = save(store, actor, mc, company_id)
    r.inputs = [CalcInput("market_cap", "calculation", mc_saved, str(mc.value), cur, mc.parameters["price_date"]),
                _fact_input("total_debt", debt, d_val), _fact_input("unrestricted_cash", cash, c_val)] + r.inputs
    r.value = f_enterprise_value(mc.value, d_val, c_val)
    r.unit = cur
    gap = _days(cash["as_of_date"], mc.parameters["price_date"])
    if gap and gap > 0:
        r.warnings.append(f"cash and debt as at {cash['as_of_date']}, {gap} days before the price date "
                          f"{mc.parameters['price_date']}; dated cash is not current cash")
    restricted = F.latest(store, actor, company_id, "cash_restricted", approved_only=False)
    r.caveats += ["Restricted cash excluded" + (f" ({restricted['raw_text']})" if restricted else "") + ".",
                  "Warrant/option exercise proceeds are not added (not cash held).",
                  "No adjustment for leases, working capital or other liabilities unless entered."]
    r.parameters = {"price_date": mc.parameters["price_date"], "balance_sheet_date": cash["as_of_date"]}
    return r


def diluted_shares(store: Store, actor: Actor, company_id: str, scenario: str = "all_outstanding") -> CalcResult:
    if scenario not in ("all_outstanding", "in_the_money"):
        raise Invalid("scenario must be all_outstanding or in_the_money")
    r = CalcResult("diluted_shares", FORMULAS["diluted_shares"].label)
    basic = _need_fact(r, store, actor, company_id, "shares_outstanding_basic", "basic shares outstanding")
    if r.status == "withheld":
        return r
    price = None
    if scenario == "in_the_money":
        price = _need_fact(r, store, actor, company_id, "share_price", "share price (to test moneyness)")
        if r.status == "withheld":
            return r
    r.inputs.append(_fact_input("basic_shares", basic))
    total = Decimal(basic["normalized_value"])
    proceeds = Decimal(0)
    included, excluded = [], []
    for metric in ("warrants_outstanding", "options_outstanding"):
        for t in F.current(store, actor, company_id, metric, approved_only=True):
            px = Decimal(t["qualifiers"].get("exercise_price") or "0")
            label = f"{metric.split('_')[0]} {t['raw_value']} @ {t['qualifiers'].get('exercise_currency_token')}{px}"
            if scenario == "in_the_money":
                from .quantities import currency_code
                ex_cur = currency_code(t["qualifiers"].get("exercise_currency_token"))
                if ex_cur != price["currency"]:
                    excluded.append(f"{label} (exercise-price currency '{ex_cur or 'unstated'}' differs from "
                                    f"price currency {price['currency']}; moneyness not tested)")
                    continue
                if px >= Decimal(price["normalized_value"]):
                    excluded.append(f"{label} (out of the money at {price['normalized_value']})")
                    continue
            n = Decimal(t["normalized_value"])
            r.inputs.append(_fact_input(f"tranche:{t['id']}", t))
            total += n
            proceeds += n * px
            included.append(label)
    pending = [f for m in ("warrants_outstanding", "options_outstanding")
               for f in F.current(store, actor, company_id, m) if f["workflow_state"] != "reviewer_approved"]
    if pending:
        r.warnings.append(f"{len(pending)} tranche(s) extracted but not reviewer-approved are not included")
    r.value = total
    r.unit = "shares"
    r.parameters = {"scenario": scenario, "included": included, "excluded": excluded,
                    "hypothetical_exercise_proceeds": str(proceeds)}
    r.caveats.append(f"Hypothetical exercise proceeds {fmt(proceeds, 0)} are NOT cash held and are not added "
                     "to cash in any other calculation.")
    return r


def runway(store: Store, actor: Actor, company_id: str) -> CalcResult:
    r = CalcResult("runway", FORMULAS["runway"].label)
    cash = _need_fact(r, store, actor, company_id, "cash_unrestricted", "unrestricted cash")
    a = assumption(store, actor, "monthly_spend", company_id)
    spend, spend_input = None, None
    if a:
        spend = Decimal(a["value"])
        spend_input = CalcInput("monthly_spend", "assumption", a["id"], a["value"], a["unit"], a["as_of_date"],
                                f"analyst assumption: {a['rationale']}")
    else:
        out = F.latest(store, actor, company_id, "period_cash_outflow", approved_only=True)
        if out and out["period_start"] and out["period_end"]:
            s, e = date.fromisoformat(out["period_start"]), date.fromisoformat(out["period_end"])
            months = Decimal((e.year - s.year) * 12 + e.month - s.month + 1)
            spend = Decimal(out["normalized_value"]) / months
            spend_input = CalcInput("monthly_spend", "fact", out["id"], str(spend), out["currency"], out["period_end"],
                                    f"historical average: {out['raw_value']} over {months} months "
                                    f"({out['period_start']}–{out['period_end']}); future spending may differ")
            if cash and out["currency"] != cash["currency"]:
                r.withhold("spend and cash are in different currencies")
        else:
            r.withhold("monthly spending: no approved spending history and no analyst assumption")
    if r.status == "withheld":
        return r
    r.inputs = [_fact_input("unrestricted_cash", cash), spend_input]
    r.value = f_runway(Decimal(cash["normalized_value"]), spend)
    r.unit = "months"
    end = date.fromisoformat(cash["as_of_date"]) + timedelta(days=int(r.value * Decimal("30.4375")))
    elapsed = _days(cash["as_of_date"], config.today().isoformat())
    r.parameters = {"cash_date": cash["as_of_date"], "indicative_end_if_spend_unchanged": end.isoformat()}
    r.warnings.append(f"Runway counts from the cash date {cash['as_of_date']}, not from today; "
                      f"{elapsed} days have elapsed since that date.")
    r.caveats.append("Excludes financing, warrant exercise and any change in spending.")
    return r


def attributable_npv(store: Store, actor: Actor, company_id: str, project_id: str,
                     tax_basis: str = "after_tax") -> CalcResult:
    r = CalcResult("attributable_npv", FORMULAS["attributable_npv"].label)
    npv = _need_fact(r, store, actor, company_id, "npv", f"{tax_basis.replace('_', '-')} project NPV",
                     project_id=project_id, tax_basis=tax_basis)
    if r.status == "withheld":
        return r
    if npv["scope_basis"] != "100%":
        return r.withhold(f"NPV basis is '{npv['scope_basis'] or 'not stated'}'; the ownership bridge requires a "
                          "stated 100% project basis (otherwise it would double-count or guess)")
    oi = entities.ownership_on(store, actor, company_id, project_id)
    if not oi or oi["interest_pct"] is None:
        return r.withhold("ownership interest in the project not established")
    r.inputs = [_fact_input("project_npv", npv),
                CalcInput("ownership_pct", "ownership_record", oi["id"], oi["interest_pct"], "%",
                          oi["effective_date"], f"{oi['interest_kind']} interest")]
    r.value = f_attributable(Decimal(npv["normalized_value"]), Decimal(oi["interest_pct"]))
    r.unit = npv["currency"]
    r.caveats.append(FORMULAS["attributable_npv"].definition)
    if npv["study_type"] == "pea":
        r.caveats.append("The NPV is from a PEA: preliminary, and may rely on Inferred resources.")
    r.parameters = {"study_type": npv["study_type"], "discount_rate": npv["discount_rate"],
                    "effective_date": npv["effective_date"], "tax_basis": tax_basis,
                    "price_case": npv["qualifiers"].get("price_case")}
    return r


def equity_bridge(store: Store, actor: Actor, company_id: str, project_id: str) -> CalcResult:
    r = CalcResult("equity_bridge", FORMULAS["equity_bridge"].label)
    att = attributable_npv(store, actor, company_id, project_id)
    if att.status != "computed":
        for m in att.missing:
            r.withhold(m)
    cash = _need_fact(r, store, actor, company_id, "cash_unrestricted", "unrestricted cash")
    debt = _need_fact(r, store, actor, company_id, "total_debt", "total debt")
    extra = {}
    for name in ("corporate_costs_pv", "funding_dilution_adjustment"):
        a = assumption(store, actor, name, company_id)
        if not a:
            r.withhold(f"{name.replace('_', ' ')}: no analyst assumption entered")
        else:
            extra[name] = a
    if r.status == "withheld":
        return r
    cur = att.unit
    c_val = _to_currency(r, store, actor, Decimal(cash["normalized_value"]), cash["currency"], cur, "cash", company_id)
    d_val = _to_currency(r, store, actor, Decimal(debt["normalized_value"]), debt["currency"], cur, "debt", company_id)
    if r.status == "withheld":
        return r
    att_id = save(store, actor, att, company_id)
    r.inputs = [CalcInput("attributable_npv", "calculation", att_id, str(att.value), cur),
                _fact_input("unrestricted_cash", cash, c_val), _fact_input("total_debt", debt, d_val)] + r.inputs
    for n, a in extra.items():
        r.inputs.append(CalcInput(n, "assumption", a["id"], a["value"], a["unit"], a["as_of_date"], a["rationale"]))
    r.value = PURE["equity_bridge"](_converted_inputs([asdict(x) for x in r.inputs]))
    r.unit = cur
    r.caveats.append("Analyst scenario built from stated components. Not a price target and not a recommendation.")
    return r


def _contained(store, actor, company_id, project_id, cats: str, r: CalcResult) -> tuple[Decimal | None, list, dict]:
    """Contained ounces for ONE category set on one effective date and basis."""
    metric = "reserve_contained_metal" if cats == "proven_probable" else "resource_contained_metal"
    rows = [f for f in F.current(store, actor, company_id, metric, project_id, approved_only=True)
            if f["estimate_status"] != "historical" and not f["qualifiers"].get("zone")]
    if not rows:
        return None, [], {}
    latest_eff = max(f["effective_date"] or "" for f in rows)
    rows = [f for f in rows if (f["effective_date"] or "") == latest_eff]
    direct = [f for f in rows if f["resource_category"] == cats]
    if direct:
        f = direct[0]
        return Decimal(f["normalized_value"]), [_fact_input("contained_oz", f)], \
            {"effective_date": latest_eff, "scope_basis": f["scope_basis"], "reporting_basis": f["reporting_basis"],
             "category": CATEGORY_LABELS[cats], "derivation": "reported combined category"}
    parts = {"measured_indicated": ("measured", "indicated"), "proven_probable": ("proven", "probable")}[cats]
    got = {c: next((f for f in rows if f["resource_category"] == c), None) for c in parts}
    if any(v is None for v in got.values()):
        miss = [CATEGORY_LABELS[c] for c, v in got.items() if v is None]
        r.withhold(f"{CATEGORY_LABELS[cats]} not reported and {', '.join(miss)} not established on "
                   f"{latest_eff} (an absent category is not assumed to be zero)")
        return None, [], {}
    bases = {(f["scope_basis"], f["reporting_basis"]) for f in got.values()}
    if len(bases) > 1:
        r.withhold("component categories are on different bases; not added")
        return None, [], {}
    total = sum((Decimal(f["normalized_value"]) for f in got.values()), Decimal(0))
    f0 = next(iter(got.values()))
    return total, [_fact_input(f"contained_oz:{c}", f) for c, f in got.items()], \
        {"effective_date": latest_eff, "scope_basis": f0["scope_basis"], "reporting_basis": f0["reporting_basis"],
         "category": CATEGORY_LABELS[cats],
         "derivation": f"sum of {' + '.join(CATEGORY_LABELS[c] for c in parts)} (same date and basis)"}


def ev_per_contained_oz(store: Store, actor: Actor, company_id: str, project_id: str,
                        categories: str = "measured_indicated", basis: str = "100%",
                        on_or_before: str | None = None) -> CalcResult:
    if categories not in ("measured_indicated", "proven_probable"):
        raise Invalid("categories must be measured_indicated or proven_probable (Inferred is never included)")
    r = CalcResult("ev_per_contained_oz", f"EV per {CATEGORY_LABELS[categories]} oz ({basis} basis)")
    ev = enterprise_value(store, actor, company_id, on_or_before)
    if ev.status != "computed":
        for m in ev.missing:
            r.withhold(m)
        return r
    oz, oz_inputs, meta = _contained(store, actor, company_id, project_id, categories, r)
    if r.status == "withheld":
        return r
    if oz is None:
        hist = F.current(store, actor, company_id, "historical_estimate_contained_metal", project_id)
        return r.withhold(f"no current {CATEGORY_LABELS[categories]} estimate established"
                          + ("; a historical estimate exists but is not comparable" if hist else ""))
    if meta["scope_basis"] != "100%":
        return r.withhold(f"resource basis '{meta['scope_basis'] or 'not stated'}' — 100% basis required as the "
                          "starting point")
    if basis == "attributable":
        oi = entities.ownership_on(store, actor, company_id, project_id)
        if not oi or oi["interest_pct"] is None:
            return r.withhold("ownership interest not established for the attributable basis")
        oz = oz * Decimal(oi["interest_pct"]) / 100
        oz_inputs.append(CalcInput("ownership_pct", "ownership_record", oi["id"], oi["interest_pct"], "%",
                                   oi["effective_date"]))
    if oz == 0:
        return r.withhold("contained ounces are zero for this category set")
    ev_id = save(store, actor, ev, company_id)
    r.inputs = [CalcInput("enterprise_value", "calculation", ev_id, str(ev.value), ev.unit,
                          ev.parameters.get("price_date"))] + oz_inputs
    if basis == "attributable":
        r.inputs.append(CalcInput("contained_oz", "parameter", None, str(oz), "oz", meta["effective_date"],
                                  "attributable ounces = 100% ounces × ownership"))
    elif len(oz_inputs) > 1:
        r.inputs.append(CalcInput("contained_oz", "parameter", None, str(oz), "oz", meta["effective_date"],
                                  meta["derivation"]))
    r.value = f_ratio(ev.value, oz)
    r.unit = f"{ev.unit}/oz"
    r.warnings += ev.warnings
    r.parameters = {**meta, "basis": basis, "ev_unit": ev.unit, "price_date": ev.parameters.get("price_date")}
    r.caveats.append("Single category set; Inferred never included. Resources are not reserves.")
    return r


def inferred_share(store: Store, actor: Actor, company_id: str, project_id: str) -> CalcResult:
    r = CalcResult("inferred_share", FORMULAS["inferred_share"].label)
    mi, mi_in, meta = _contained(store, actor, company_id, project_id, "measured_indicated", r)
    if r.status == "withheld":
        return r
    inf = [f for f in F.current(store, actor, company_id, "resource_contained_metal", project_id, approved_only=True)
           if f["resource_category"] == "inferred" and f["effective_date"] == meta.get("effective_date")
           and not f["qualifiers"].get("zone")]
    if mi is None or not inf:
        return r.withhold("Measured & Indicated and Inferred ounces on the same effective date not both established")
    i = Decimal(inf[0]["normalized_value"])
    r.inputs = mi_in + [_fact_input("inferred_oz", inf[0])]
    if len(mi_in) > 1:
        r.inputs.append(CalcInput("measured_indicated_oz", "parameter", None, str(mi), "oz", meta["effective_date"],
                                  meta["derivation"]))
    else:
        r.inputs[0].name = "measured_indicated_oz"
    r.value = f_ratio(i, mi + i) * 100
    r.unit = "%"
    r.parameters = meta
    return r


def liquidity_days(store: Store, actor: Actor, company_id: str, position_shares: str,
                   rates: tuple = ("0.05", "0.10", "0.20")) -> CalcResult:
    r = CalcResult("liquidity_days", FORMULAS["liquidity_days"].label)
    adv = _need_fact(r, store, actor, company_id, "average_daily_volume", "average daily volume")
    if r.status == "withheld":
        return r
    pos = Decimal(str(position_shares))
    a = Decimal(adv["normalized_value"])
    table = []
    for rate in rates:
        rr = Decimal(rate)
        table.append({"participation_rate": str(rr), "days": str(quantize(f_ratio(pos, a * rr), 1))})
    r.inputs = [_fact_input("adv", adv), CalcInput("position_shares", "parameter", None, str(pos), "shares"),
                CalcInput("participation_rate", "parameter", None, str(Decimal(rates[0])), "fraction")]
    r.value = f_ratio(pos, a * Decimal(rates[0]))
    r.unit = "days"
    r.parameters = {"table": table, "adv_window": adv["qualifiers"].get("window"), "adv_date": adv["as_of_date"]}
    r.caveats.append(FORMULAS["liquidity_days"].definition)
    return r


# ------------------------------------------------------------------ persistence & reproduction
def save(store: Store, actor: Actor, r: CalcResult, company_id: str | None) -> str:
    f = FORMULAS[r.formula_id]
    inputs = [asdict(x) for x in r.inputs]
    row = store.insert(actor, "calculations", {
        "company_id": company_id, "formula_id": f.id, "formula_version": f.version, "label": r.label,
        "status": r.status, "output_value": str(r.value) if r.value is not None else None, "output_unit": r.unit,
        "display_value": r.display(), "inputs": inputs, "missing": r.missing, "warnings": r.warnings,
        "caveats": r.caveats, "parameters": r.parameters, "created_by": actor.user_id,
        "created_at": config.iso_now()})
    for x in r.inputs:
        if x.ref_id and x.kind in ("fact", "assumption", "calculation"):
            lineage.link(store, actor, x.kind, x.ref_id, "calculation", row["id"])
    r.calc_id = row["id"]
    return row["id"]


def recompute(store: Store, actor: Actor, calc_id: str) -> dict:
    """Re-run the pure function on the STORED inputs. Returns the comparison."""
    c = store.get(actor, "calculations", calc_id)
    if c["status"] != "computed":
        return {"calc_id": calc_id, "reproduced": None, "note": "withheld results have no output to reproduce"}
    vals = _converted_inputs(c["inputs"])
    if c["formula_id"] == "ev_per_contained_oz":
        oz = vals.get("contained_oz") or sum((v for k, v in vals.items() if k.startswith("contained_oz")), Decimal(0))
        vals["contained_oz"] = oz
    if c["formula_id"] == "inferred_share" and "measured_indicated_oz" not in vals:
        vals["measured_indicated_oz"] = sum((v for k, v in vals.items() if k.startswith("contained_oz:")), Decimal(0))
    out = PURE[c["formula_id"]](vals)
    return {"calc_id": calc_id, "stored": c["output_value"], "recomputed": str(out),
            "reproduced": Decimal(c["output_value"]) == out, "formula": c["formula_id"],
            "formula_version": c["formula_version"]}


def run_standard(store: Store, actor: Actor, company_id: str) -> list[dict]:
    """Run the standard calculations for a company and persist them."""
    out = []
    for r in [market_cap(store, actor, company_id), enterprise_value(store, actor, company_id),
              diluted_shares(store, actor, company_id, "all_outstanding"),
              diluted_shares(store, actor, company_id, "in_the_money"), runway(store, actor, company_id)]:
        cid = save(store, actor, r, company_id)
        out.append(store.get(actor, "calculations", cid))
    for p in entities.projects_of(store, actor, company_id):
        for r in [attributable_npv(store, actor, company_id, p["id"]),
                  ev_per_contained_oz(store, actor, company_id, p["id"], "measured_indicated", "100%"),
                  ev_per_contained_oz(store, actor, company_id, p["id"], "measured_indicated", "attributable"),
                  inferred_share(store, actor, company_id, p["id"])]:
            cid = save(store, actor, r, company_id)
            out.append(store.get(actor, "calculations", cid))
    return out


def definitions() -> dict:
    return {"rounding": ROUNDING, "formulas": {k: asdict(v) for k, v in FORMULAS.items()}}
