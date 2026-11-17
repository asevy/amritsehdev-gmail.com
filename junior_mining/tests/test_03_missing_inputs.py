"""Brief §17 case 3: missing input remains unknown; never zero-filled or
inferred as fact."""

from jmi import answers, calc, ingest


def test_debt_not_disclosed_withholds_ev(approved):
    r = calc.enterprise_value(approved.store, approved.A, approved.BWM)
    assert r.status == "withheld" and r.value is None
    assert any("total debt" in m and "not established" in m for m in r.missing)


def test_stated_no_debt_is_zero_with_quote(approved):
    f = approved.fact(metric_id="total_debt", company_id=approved.HPG)
    assert f["normalized_value"] == "0" and "no debt" in f["raw_text"].lower()
    assert any("stated value" in t for t in f["transformations"])


def test_runway_withheld_without_spending_basis(approved):
    r = calc.runway(approved.store, approved.A, approved.TVG)
    assert r.status == "withheld" and r.value is None


def test_unapproved_input_withholds_rather_than_uses(ws):
    r = calc.market_cap(ws.store, ws.A, ws.HPG)
    assert r.status == "withheld"
    assert any("not reviewer-approved" in m for m in r.missing)


def test_stated_nil_category_allows_derivation(approved):
    # Orrin Basin states "No Measured Mineral Resources have been estimated" -> M&I = 0 + Indicated
    r = calc.inferred_share(approved.store, approved.A, approved.OBR, approved.OBP)
    assert r.status == "computed"
    assert any("stated" in t for i in r.inputs if i.ref_id and i.kind == "fact"
               for t in approved.store.get(approved.A, "facts", i.ref_id)["transformations"])


def test_absent_category_is_not_assumed_zero(approved):
    from jmi import entities, facts
    st, a = approved.store, approved.A
    co = entities.create_company(st, a, "Test Absent Category Co. (SYNTHETIC)", synthetic=True)
    pr = entities.create_project(st, a, co["id"], "Absent Category Project", commodity="gold", stage="resource",
                                 interest_pct="100", effective_date="2020-01-01", synthetic=True)
    txt = ("SYNTHETIC FIXTURE\n\nAs at March 1, 2026, the Absent Category Project hosts Indicated Mineral Resources of "
           "0.31 Moz Au.\n").encode()
    res = ingest.upload(st, a, filename="absent.txt", data=txt, title="Absent Category Project note (SYNTHETIC)",
                        doc_type="news_release", company_id=co["id"], publication_date="2026-03-02", synthetic=True)
    f = [x for x in st.find(a, "facts", version_id=res["version"]["id"]) if x["metric_id"] == "resource_contained_metal"][0]
    assert f["resource_category"] == "indicated"
    facts.review(st, approved.R, f["id"], "approve", "matches source")
    r = calc.CalcResult("x", "x")
    val, _, _ = calc._contained(st, a, co["id"], pr["id"], "measured_indicated", r)
    assert val is None and r.status == "withheld"
    assert any("not assumed to be zero" in m for m in r.missing)


def test_question_without_evidence_is_not_found(approved):
    ans = answers.ask(approved.store, approved.A, approved.HPG, "What is the 2027 production guidance?")
    assert ans["status"] == "not_found"
    assert "does not establish that it does not exist" in ans["message"]
    assert ans["coverage"][0].startswith("Documents reviewed")


def test_unreadable_value_stays_unknown(ws):
    f = ws.fact(raw_value="2O1")
    assert f["normalized_value"] is None and f["workflow_state"] == "needs_review"
    assert "OCR" in f["missing_reason"] or "not readable" in f["missing_reason"]
