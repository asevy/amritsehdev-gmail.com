"""Brief §17 case 7: project NPV does not become company equity value
without a justified bridge."""

from jmi import calc, memo as M


def test_attributable_npv_is_labelled_not_equity_value(approved):
    r = calc.attributable_npv(approved.store, approved.A, approved.OBR, approved.OBP)
    assert r.status == "computed" and r.value == 210_000_000
    assert any("Not company equity value" in c for c in r.caveats)
    assert any("PEA" in c for c in r.caveats)


def test_equity_bridge_withheld_without_specified_components(approved):
    r = calc.equity_bridge(approved.store, approved.A, approved.HPG, approved.HPP)
    assert r.status == "withheld"
    assert any("corporate costs pv" in m for m in r.missing)
    assert any("funding dilution adjustment" in m for m in r.missing)


def test_equity_bridge_computed_only_when_every_component_specified(approved):
    st, a = approved.store, approved.A
    calc.set_assumption(st, a, "corporate_costs_pv", "40000000", "G&A to production decision (test)", unit="USD",
                        company_id=approved.HPG)
    calc.set_assumption(st, a, "funding_dilution_adjustment", "120000000", "equity funding of capex (test)", unit="USD",
                        company_id=approved.HPG)
    calc.set_assumption(st, a, "fx_cad_usd", "0.7246", "test inverse rate", unit="USD per CAD", as_of_date="2026-11-13",
                        source="SYNTHETIC test entry")
    r = calc.equity_bridge(st, a, approved.HPG, approved.HPP)
    assert r.status == "computed"
    assert any("Not a price target" in c for c in r.caveats)
    names = {i.name for i in r.inputs}
    assert {"attributable_npv", "unrestricted_cash", "total_debt", "corporate_costs_pv",
            "funding_dilution_adjustment"} <= names


def test_npv_with_unstated_basis_is_not_bridged(approved):
    """A reviewer may approve an NPV whose basis the source never states; the
    ownership bridge must still refuse to multiply it."""
    from jmi import entities, facts, ingest
    st, a = approved.store, approved.A
    co = entities.create_company(st, a, "Basis Test Co. (SYNTHETIC)", synthetic=True)
    pr = entities.create_project(st, a, co["id"], "Basis Test Project", commodity="gold", stage="pea",
                                 interest_pct="60", interest_kind="joint_venture", effective_date="2020-01-01")
    txt = (b"SYNTHETIC\n\nBasis Test Project: the PEA, with an effective date of May 1, 2026, outlines an after-tax "
           b"NPV (5%) of US$250 million.\n")
    res = ingest.upload(st, a, filename="basis.txt", data=txt, title="Basis Test Project PEA note (SYNTHETIC)",
                        doc_type="news_release", company_id=co["id"], publication_date="2026-05-02", synthetic=True)
    f = next(x for x in st.find(a, "facts", version_id=res["version"]["id"]) if x["metric_id"] == "npv")
    assert f["workflow_state"] == "needs_review" and "basis not stated" in f["missing_reason"]
    facts.review(st, approved.R, f["id"], "approve", "value matches; basis not stated by issuer")
    r = calc.attributable_npv(st, a, co["id"], pr["id"])
    assert r.status == "withheld" and any("100% project basis" in m for m in r.missing)


def test_claim_equating_npv_with_company_value_is_unsupported(approved):
    f = approved.fact(metric_id="npv", raw_value="412")
    res = M.validate_claim(approved.store, approved.A, {
        "kind": "factual", "fact_ids": [f["id"]], "calc_ids": [], "risk_ids": [], "review": {},
        "text": "The PEA estimates an after-tax NPV (5%) of US$412 million, so the company is worth US$412 million."})
    assert res["status"] == "unsupported" and any("equity value" in x for x in res["reasons"])


def test_market_cap_is_not_called_enterprise_value(approved):
    r = calc.market_cap(approved.store, approved.A, approved.HPG)
    cid = calc.save(approved.store, approved.A, r, approved.HPG)
    res = M.validate_claim(approved.store, approved.A, {
        "kind": "factual", "fact_ids": [], "calc_ids": [cid], "risk_ids": [], "review": {},
        "text": "Enterprise value is CAD 88.3 million."})
    assert res["status"] == "unsupported"
