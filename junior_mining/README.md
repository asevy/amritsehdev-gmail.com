# Junior Mining Intelligence (working name)

Evidence-first diligence, risk, peer-comparison and monitoring software for
specialist mining investment teams. Built to the brief
"Junior Mining Intelligence — Claude Code Development Brief" (2026-11-17).

**What it is:** a working pilot that ingests PDF / XLSX / CSV / text
disclosures, proposes typed facts with exact source locations, re-checks
them, routes them through reviewer approval, runs deterministic
calculations, keeps a risk register and diligence checklist, builds
analyst-approved peer comparisons, drafts claim-level cited memos, and
monitors changes. It runs on synthetic fixtures out of the box.

**What it is not:** a scoring or rating system (there is none, by design),
a source of recommendations or price targets, a live-data product (no feed
is connected), or a validated institutional product (expert validation is
pending). See [docs/FEATURE_MATRIX.md](docs/FEATURE_MATRIX.md).

All companies, projects, tickers and figures in `fixtures/` are
**SYNTHETIC** and fictional.

## Quick start

```bash
cd junior_mining
pip install -r requirements.txt          # pdfplumber, pypdfium2, openpyxl, reportlab, Pillow, pytest
python -m pytest                         # 116 tests, ~20 s
python scripts/demo.py                   # scripted end-to-end demonstration over HTTP
```

Run the application against a synthetic workspace:

```bash
JMI_DATA_DIR=./data python -m jmi seed-demo     # prints a generated password once
JMI_DATA_DIR=./data python -m jmi serve         # http://127.0.0.1:8780/login
```

Sign in as `analyst.a`, `reviewer.a`, `admin.a`, `viewer.a` (tenant alpha) or
`analyst.b` (tenant beta) with the printed password. Upload
`data/fixtures/HPG_NR_2026-11-16_resource_update.pdf` on the Halvard Peak
documents page to see change detection, restatement and stale outputs.

## Commands

| Command | Purpose |
|---|---|
| `python -m jmi serve` | HTTP server (stdlib), the eight screens and JSON API |
| `python -m jmi seed-demo` | Synthetic two-tenant workspace |
| `python -m jmi create-tenant ID NAME` / `create-user USER ROLE TENANT` | Real (empty) tenant and users |
| `python -m jmi worker` | Retry failed / queued ingestion runs |
| `python -m jmi integrity` | SQLite integrity check and audit-chain verification |
| `python -m jmi backup DEST` | Consistent online backup |
| `python -m jmi definitions` | Metric and formula registry (JSON) |
| `python -m jmi.bench QUESTIONS.jsonl` | Benchmark runner (separate measures, intervals) |
| `python scripts/export_contracts.py` | Regenerate `docs/contracts/*.json` from code |

## Layout

```
jmi/            application package (see docs/ARCHITECTURE.md for each module)
fixtures/       SYNTHETIC fixture generator (deterministic)
tests/          pytest suite — tests/test_01 … test_16 map to brief §17 cases 1–16
scripts/        demo.py (end-to-end over HTTP), export_contracts.py
benchmark/      expert-review benchmark proposal + synthetic development question set
docs/           reuse inventory, architecture, specification, contracts, runbook, results, handoff
```

## Documents

- [Reuse inventory](docs/REUSE_INVENTORY.md) — what was inspected, run and reused, with paths
- [Architecture decisions](docs/ARCHITECTURE.md)
- [Product specification](docs/PRODUCT_SPEC.md)
- [Data contracts](docs/DATA_CONTRACTS.md) and generated [`docs/contracts/`](docs/contracts)
- [Calculation definitions](docs/CALCULATIONS.md)
- [Data sources, access and licensing](docs/DATA_SOURCES.md)
- [Benchmark proposal](benchmark/PROPOSAL.md)
- [Test results](docs/TEST_RESULTS.md) and [demo transcript](docs/DEMO_TRANSCRIPT.md)
- [Feature completion matrix](docs/FEATURE_MATRIX.md)
- [Runbook](docs/RUNBOOK.md) and [deployment](docs/DEPLOY.md)
- [Handoff](docs/HANDOFF.md)
