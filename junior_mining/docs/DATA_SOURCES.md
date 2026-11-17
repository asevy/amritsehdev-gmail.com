# Data sources, access and licensing — honest integration status

The upload workflow works without any paid integration. Nothing below is
described as live unless it is.

| Source | Status in this build | Access / licensing notes | Next step |
|---|---|---|---|
| Customer uploads (PDF, XLSX, CSV, TXT) | **Implemented and tested** | Rights are the uploader's; bytes stored per tenant, never shared across tenants | — |
| Market data | **Upload only** (CSV with as-of date, listing, close, currency, ADV, stated source) | A vendor feed needs a licence covering storage, derived data and redistribution | Select vendor; confirm derived-data rights |
| SEDAR+ (Canadian filings) | **Not built** — listed as `not_configured` | Automated-access terms not reviewed; no scraping or CAPTCHA bypass | Review terms; consider licensed aggregator |
| SEC EDGAR | **Not built in this product** (`filing_forensics.py` in the parent repo retrieves EDGAR with a declared User-Agent, untested) | Public; fair-access rate limits; User-Agent with contact required | Adapter behind `ingest.upload` |
| Regulator permit registries | **Not configured** | Jurisdiction-specific; official record is the primary source for authorization status | Per-jurisdiction adapters or manual citation of registry pages |
| Insider transactions (e.g. SEDI) | **Not configured** | Licensed/official source required | — |
| OCR for scanned pages | **Not available** (no tesseract in environment) | Scanned pages are detected and reported unreadable | Install an OCR engine; treat OCR text as lower-confidence source needing review |
| Model provider for candidate proposal | **Not configured** (no SDK, no key). Boundary `extract.ModelProposer` tested with a fake model only | Provider retention/training settings must be documented for the chosen configuration before use; customer documents must not train shared models | Choose provider; configure in secret manager; rerun benchmark |
| Competitor public pages (brief §4 references) | **Recheck blocked** — all 9 hosts outside network allowlist on 2026-11-17 | Read for context only; no copying | Allow hosts `www.hudson-labs.com`, `help.alpha-sense.com`, `pages.marketintelligence.spglobal.com`, `juniorminingintelligence.com`, `premissive.ca`, `mineanalyst.com`, `www.lonmining.com` and re-fetch |

## Source hierarchy used by the product
Primary issuer documents for issuer facts; official records for authorization
status where obtainable; secondary sources as leads with attribution;
promotional material (e.g. investor decks) remains attributed and can be
contradicted by primary filings (the fixture deck's NPV is rejected in favour
of the technical report through a recorded discrepancy resolution).

## Coverage and freshness
Each source has a row in `source_feeds` (status, last success/attempt, error,
licensing note). Coverage status on every company and output reports failed
ingestion, unreadable pages, missing required items, stale disclosures
(> `JMI_FRESHNESS_DAYS`) and stale market data (> `JMI_MARKET_DATA_STALE_DAYS`).
