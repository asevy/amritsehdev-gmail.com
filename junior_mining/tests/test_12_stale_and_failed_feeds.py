"""Brief §17 case 12: stale or failed feeds display visibly incomplete coverage."""

from datetime import datetime

from jmi import config, ingest, memo as M, monitoring


def test_failed_ingestion_is_visible_and_retained(ws):
    cs = monitoring.coverage_status(ws.store, ws.A, ws.HPG)
    assert cs["status"] == "ingestion_failed"
    assert any("Corrupt upload" in r for r in cs["reasons"])
    runs = [r for r in ws.store.find(ws.A, "ingestion_runs") if r["status"] == "failed"]
    assert runs and "ParseError" in runs[0]["error"]
    again = ingest.retry_failed(ws.store, ws.A)
    assert again and again[0]["status"] == "failed" and again[0]["attempts"] == 2
    feed = ws.store.find(ws.A, "source_feeds", name="Document uploads")[0]
    assert feed["status"] == "failed"


def test_unreadable_pages_make_coverage_incomplete(ws):
    cov = ingest.coverage(ws.store, ws.A, ws.HPG)
    assert cov["unreadable_pages"] and cov["unreadable_pages"][0]["pages"] == [3]
    assert cov["complete"] is False
    assert "incomplete" in monitoring.coverage_status(ws.store, ws.A, ws.HPG)["all"]


def test_old_disclosures_are_stale(ws):
    cs = monitoring.coverage_status(ws.store, ws.A, ws.BWM)
    assert "stale" in cs["all"] and any("2025-03-10" in r for r in cs["reasons"])


def test_market_data_goes_stale_with_time(ws):
    assert "stale" not in monitoring.coverage_status(ws.store, ws.A, ws.OBR)["all"]
    config.set_clock(datetime(2026, 12, 15, 12, 0))
    cs = monitoring.coverage_status(ws.store, ws.A, ws.OBR)
    assert "stale" in cs["all"] and any("market data dated 2026-11-13" in r for r in cs["reasons"])


def test_outputs_carry_analysis_time_cutoff_and_gaps(approved):
    m = M.create_memo(approved.store, approved.A, approved.HPG, "Memo (SYNTHETIC)")
    r = M.render(approved.store, approved.A, m["version"]["id"])
    assert r["analysis_time"] and r["evidence_cutoff"]
    assert any("Ingestion failed" in u for u in r["unresolved"])
    assert any("Unreadable pages" in u for u in r["unresolved"])
    assert r["coverage"]["complete"] is False


def test_connectors_are_listed_as_not_configured(ws):
    feeds = {f["name"]: f for f in ws.store.find(ws.A, "source_feeds")}
    assert feeds["SEDAR+ filings connector"]["status"] == "not_configured"
    assert feeds["Market-data vendor feed"]["status"] == "not_configured"
