"""Brief §17 case 10: calculation lineage is reproducible with correct units
and defined rounding."""

from decimal import Decimal

from jmi import calc, lineage


def test_every_computed_result_reproduces_exactly(approved):
    out = []
    for cid in (approved.HPG, approved.TVG, approved.OBR):
        out += calc.run_standard(approved.store, approved.A, cid)
    computed = [c for c in out if c["status"] == "computed"]
    assert len(computed) >= 20
    for c in computed:
        rep = calc.recompute(approved.store, approved.A, c["id"])
        assert rep["reproduced"] is True, (c["formula_id"], rep)


def test_market_cap_value_units_and_rounding(approved):
    r = calc.market_cap(approved.store, approved.A, approved.HPG)
    assert r.value == Decimal("0.62") * Decimal("142350000")
    assert r.unit == "CAD"
    assert r.display() == "CAD 88.3 million"          # display rounding only; stored value full precision
    assert str(r.value) == "88257000.00"
    assert any("days apart" in w for w in r.warnings)  # price 2026-11-13 vs shares 2026-09-30


def test_fx_conversion_records_rate_source_and_date(approved):
    r = calc.enterprise_value(approved.store, approved.A, approved.TVG)
    assert r.status == "computed" and r.unit == "CAD"
    fx = next(i for i in r.inputs if i.name.startswith("fx_"))
    assert fx.value == "1.38" and fx.date == "2026-11-13" and "SYNTHETIC" in fx.note
    assert r.value == Decimal("2.10") * 210_000_000 + Decimal("20000000") * Decimal("1.38") - Decimal("35200000") * Decimal("1.38")


def test_fx_without_source_is_refused(approved):
    import pytest
    from jmi.store import Invalid
    with pytest.raises(Invalid):
        calc.set_assumption(approved.store, approved.A, "fx_usd_cad", "1.4", "no source given")


def test_inputs_are_linked_for_lineage(approved):
    r = calc.ev_per_contained_oz(approved.store, approved.A, approved.HPG, approved.HPP)
    cid = calc.save(approved.store, approved.A, r, approved.HPG)
    ins = lineage.inputs_of(approved.store, approved.A, "calculation", cid)
    kinds = {k for k, _ in ins}
    assert "calculation" in kinds and "fact" in kinds
    for k, i in ins:
        if k == "fact":
            assert approved.store.get(approved.A, "facts", i)["workflow_state"] == "reviewer_approved"


def test_dilution_scenario_keeps_proceeds_hypothetical(approved):
    r = calc.diluted_shares(approved.store, approved.A, approved.HPG, "all_outstanding")
    assert r.value == 142_350_000 + 38_000_000 + 9_100_000
    assert Decimal(r.parameters["hypothetical_exercise_proceeds"]) == Decimal("38000000") * Decimal("0.85") + \
        Decimal("9100000") * Decimal("0.60")
    assert any("NOT cash held" in c for c in r.caveats)
    itm = calc.diluted_shares(approved.store, approved.A, approved.HPG, "in_the_money")
    assert itm.value == 142_350_000 + 9_100_000      # C$0.85 warrants are out of the money at C$0.62


def test_runway_counts_from_cash_date(approved):
    r = calc.runway(approved.store, approved.A, approved.HPG)
    assert r.status == "computed"
    assert r.value == Decimal("18400000") / (Decimal("4600000") / 3)
    assert any("not from today" in w for w in r.warnings)
