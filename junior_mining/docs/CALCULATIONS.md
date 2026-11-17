# Calculation definitions

Source of truth: `jmi/calc.py` (`FORMULAS`, `PURE`); also served at
`/definitions` and exported to `contracts/definitions.json`. Every stored
result records formula id + version, all input values with units, dates and
source ids, warnings and caveats. `recompute()` re-runs the pure function on
the stored inputs; the test suite requires an exact match for every computed
result (`tests/test_10_calculation_lineage.py`).

**Arithmetic:** `decimal.Decimal`, 34-digit context. **Rounding:**
ROUND_HALF_EVEN at display only; stored outputs keep full precision.
**Reconciliation tolerance:** two reported figures agree when their
printed-precision intervals overlap (`quantities.interval`).
**Inputs:** reviewer-approved facts only; unapproved candidates withhold the
result ("extracted but not reviewer-approved"). **Missing input:** result
withheld with the missing item named. Silence is never zero; a disclosed
"no debt" is zero with its quote.

| Formula (v1) | Expression | Withheld when | Caveats always shown |
|---|---|---|---|
| `market_cap` | price × basic shares | no approved price or share count | not EV; excludes dilutive securities; date gap between price and share count |
| `enterprise_value` | market cap + total debt − unrestricted cash | debt or cash not established; currency differs and no FX rate with source/date | restricted cash excluded; warrant proceeds not added; dated cash is not current cash |
| `diluted_shares` | basic + included tranches (scenario: all outstanding / in-the-money) | no basic shares; ITM without price | proceeds hypothetical, not cash; tranches with other-currency strikes not tested |
| `runway` | unrestricted cash ÷ monthly spend (assumption, or historical average from a reported period) | no spend basis; currency mismatch | counts from the cash date, elapsed days shown; excludes financing |
| `attributable_npv` | project NPV × ownership % | NPV basis not a stated 100% project basis; ownership not established | not company equity value; PEA caveat |
| `equity_bridge` | attributable NPV + cash − debt − corporate costs PV − funding/dilution adjustment | any component missing | analyst scenario; not a price target or recommendation |
| `ev_per_contained_oz` | EV ÷ contained oz for ONE category set (M&I or P&P), 100% or attributable | category set not established on one date and basis (absent category never assumed zero); basis not 100% | Inferred never included; resources are not reserves |
| `inferred_share` | Inferred ÷ (M&I + Inferred) on one date/basis | either not established | composition ratio, not a quality grade |
| `liquidity_days` | position ÷ (ADV × participation rate) for 5/10/20% | no ADV | market impact not modelled; no universal exit estimate |
| `fx_convert` | amount × rate | — | analyst rate with source and date |

Not implemented (deferred, brief §11): full project cash-flow models,
commodity sensitivities, royalty/stream cash flows, re-pricing of studies.
Reported study economics are shown as reported, with differing assumptions
listed, and are never linearly re-priced.
