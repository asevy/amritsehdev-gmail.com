"""Brief §17 case 4: inferred resources do not silently become reserves;
intercept length does not become true width."""

import io

import openpyxl

from helpers import passage_candidate, vctx, version_of
from jmi import calc, ingest
from jmi.validate import validate


def _reserve_xlsx_with_inferred() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reserves"
    ws["A1"] = "Tamsin Vale Project Mineral Reserve Estimate (effective September 1, 2025) SYNTHETIC"
    ws.append(["Category", "Tonnes (Mt)", "Grade (g/t Au)", "Contained Au (koz)"])
    ws.append(["Probable", "30.0", "0.70", "675"])
    ws.append(["Inferred", "15.0", "0.55", "265"])
    ws.append(["1. Reported on a 100% basis."])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def test_inferred_row_in_reserve_table_is_rejected(ws):
    res = ingest.upload(ws.store, ws.A, filename="tvg_reserves.xlsx", data=_reserve_xlsx_with_inferred(),
                        title="TVG reserves (SYNTHETIC)", doc_type="technical_report", company_id=ws.TVG,
                        publication_date="2026-10-20", synthetic=True)
    rows = ws.facts(version_id=res["version"]["id"])
    inferred = [f for f in rows if f["resource_category"] == "inferred"]
    assert inferred and all(f["workflow_state"] == "rejected" for f in inferred)
    assert all(f["metric_id"].startswith("reserve_") for f in inferred)
    assert any("not reported as reserves" in c["detail"] for f in inferred for c in f["checks"])
    probable = [f for f in rows if f["resource_category"] == "probable"]
    assert probable and all(f["workflow_state"] == "source_matched" for f in probable)


def test_model_claiming_inferred_as_reserve_is_rejected(ws):
    v = version_of(ws, "HPG_PEA_Technical_Report_Summary_2026.pdf")
    tbl = [t for t in ws.store.find(ws.A, "doc_tables", version_id=v["id"])][0]
    from jmi.extract import Candidate, Location
    row = next(i for i, r in enumerate(tbl["rows"]) if r[0] == "Inferred")
    c = Candidate(metric_id="reserve_contained_metal", quote="331", raw_value="331",
                  location=Location(2, table_index=tbl["table_index"], row_index=row, col_index=3, row_header="Inferred",
                                    col_header="Contained Au (koz)", footnotes=tbl["footnotes"]),
                  context=tbl["title"] + " | Inferred | notes: " + " ".join(tbl["footnotes"]), rule_id="model",
                  fields={"resource_category": "inferred", "effective_date": "2026-04-30", "scope_basis": "100%"},
                  qualifiers={"unit_token": "koz"})
    assert validate(c, vctx(ws, v)).state == "rejected"


def test_ev_per_ounce_never_adds_inferred(approved):
    r = calc.ev_per_contained_oz(approved.store, approved.A, approved.HPG, approved.HPP, "measured_indicated")
    assert r.status == "computed"
    oz_inputs = [i for i in r.inputs if i.name.startswith("contained_oz")]
    assert all("inferred" not in (approved.store.get(approved.A, "facts", i.ref_id)["resource_category"] or "")
               for i in oz_inputs if i.ref_id)


def test_intercept_length_is_not_true_width(ws):
    v = version_of(ws, "HPG_NR_2026-10-08_drilling.txt")
    rows = ws.facts(version_id=v["id"])
    assert not [f for f in rows if f["metric_id"] == "true_width"]
    lengths = [f for f in rows if f["metric_id"] == "drill_intercept_length"]
    assert {f["raw_value"] for f in lengths} == {"23.0", "4.0", "31.5"}
    h41 = next(f for f in lengths if f["qualifiers"]["hole_id"] == "HP-26-041" and f["qualifiers"]["interval"] == "main")
    assert h41["qualifiers"]["true_width_status"].startswith("not known")
    h44 = next(f for f in lengths if f["qualifiers"]["hole_id"] == "HP-26-044")
    assert "estimate" in h44["qualifiers"]["true_width_status"]


def test_model_proposing_true_width_from_intercept_is_rejected(ws):
    v = version_of(ws, "HPG_NR_2026-10-08_drilling.txt")
    c = passage_candidate(ws, v, 1, r"4\.21 g/t Au over 23\.0 m", "true_width", "23.0", claimed_unit="m",
                          qualifiers={"hole_id": "HP-26-041"})
    r = validate(c, vctx(ws, v))
    assert r.state == "rejected"
    assert any(x["check"] == "drilling" and x["status"] == "fail" for x in r.checks)


def test_historical_estimate_kept_separate(ws):
    f = ws.fact(metric_id="historical_estimate_contained_metal", company_id=ws.BWM)
    assert f["estimate_status"] == "historical"
    assert not [x for x in ws.facts(company_id=ws.BWM) if x["metric_id"] == "resource_contained_metal"]
