# Sehdev Quality Portfolio — v1

> A living document. The trading toolkit enforces discipline in code;
> this document is where the *thesis* lives — why each holding is here,
> which account it lives in, and what would make me sell it.
>
> Owner: Amrit Sehdev
> Version: 1.0
> Last updated: [fill in]

---

## 1. Sleeves & accounts

| Account | Purpose | Approximate size |
|---|---|---|
| TFSA (Tax-Free Savings Account) | Multi-week / multi-month winners; forever-holds. Gains are tax-free. | [fill in] |
| Personal non-registered | Active swing sleeve (short-hold, higher-frequency). Losses stay usable. | $50,000 |
| RRSP | Long-term retirement. Contribute; don't trade. | [fill in] |
| Corporate | Passive sleeve, mindful of Small Business Deduction / $50k passive-income grind. | [fill in] |

**Rules by account** (enforced in `account_router.py`):
- Intraday / few-day trades → Personal non-registered *only* (business-income reclassification risk in TFSA).
- Multi-week / multi-month setups → TFSA.
- Forever-holds (index ETFs) → TFSA / RRSP / Corp as fits contribution room; not the swing sleeve.
- If TFSA short-hold count ≥ 25 in trailing year → move active trades to personal (`account_router` warns automatically).

---

## 2. Forever-holds (never traded on momentum)

These are excluded from the scanner via `Scanner(exclude={...})`.

| Ticker | Role | Account |
|---|---|---|
| XEQT | All-equity global index (Cdn-listed) | TFSA / RRSP |
| ZEQT | Same theme, BMO issue | TFSA |
| XIC | Cdn broad market | TFSA / RRSP |
| ZSP | S&P 500 | TFSA |
| XEF | Developed ex-North America | RRSP |
| XWD | World | RRSP |
| XGI | Global infra | TFSA |

DCA these on schedule. Do not use the scanner on them; the scanner will refuse.

---

## 3. Active holdings — by account

*(Fill in after opening or paper-trading each. Each row is a real position, not a watchlist idea.)*

### TFSA (multi-week / multi-month)
| Ticker | Entered | Entry | Stop | Target / Thesis | Notes |
|---|---|---|---|---|---|
| _example: LMT_ | _2026-07-15_ | _$541.75_ | _$493.48_ | _$638 — LOADED coil breakout, aerospace tailwind_ | _size 34 sh, 0.75% sleeve risk_ |

### Personal non-registered (few-day swings, intraday)
| Ticker | Entered | Entry | Stop | Target / Thesis | Notes |
|---|---|---|---|---|---|

### Corporate (passive)
| Ticker | Entered | Entry | Stop | Target / Thesis | Notes |
|---|---|---|---|---|---|

---

## 4. Watchlist — flagged setups, not yet entered

Logged via `python log_signal.py <TICKER> <SIGNAL> --flag-price ... --entry ... --stop ... --target ...`. Read from `swing_journal.json`.

| Ticker | Signal | Flag date | Flag price | Entry trigger | Stop | Target | Notes |
|---|---|---|---|---|---|---|---|
| LMT | LOADED | 2026-06-03 | $513.43 | $541.75 | $493.48 | $638.29 | Wide moat, Morningstar 8% discount to FVE; wait for July earnings catalyst |

---

## 5. Universe (screener input)

See `universe.txt` for the daily scan list. Currently 40 US large-caps across
AI/semis, software, AI power, industrials, financials, healthcare, mega-caps.
Adjust as sector themes rotate.

---

## 6. Trading rules (the discipline, in prose)

**Non-negotiable:**
1. **Every buy gets a stop the same minute the order fills.** No exceptions. This is the Constellation Software lesson — a 48% drawdown that would have been 10-15% with a stop.
2. **Stop-limit orders, not stop-market.** Good-till 90 days, renew when they expire.
3. **Predetermined entry + stop + target before the order goes in.** Sized off ATR via `risk_manager.size_order`.
4. **0.75% sleeve risk per trade, max.** Sleeve = $50k → max $375 risk per position.
5. **Max 5 concurrent open positions**, ≤ 100% sleeve exposure.
6. **Circuit breakers:** if 3 consecutive losses, halt for the day. If daily loss ≥ 2% of sleeve, halt for the day.
7. **RiskManager stays in `mode="suggest"`, not `"auto"`.** I place every order by hand until expectancy is proven.

**Discretionary:**
- Do not trade a name flagged `poor-R:R-dont-chase` no matter how good the story is.
- LOADED coils need a scheduled catalyst inside 21 days to graduate from "watch" to "actionable."
- If a name has any forensic red flag (going-concern, material weakness, restatement), it's out — no matter the chart.

---

## 7. Expectancy gate — the go/no-go on real money

The $50k active sleeve does **not** fund until:
- [ ] `python launch.py` runs clean on my machine
- [ ] `python backtest.py` on the 40-ticker universe over 2 years shows positive expectancy per signal type (LOADED, MOVING_NOW)
- [ ] `swing_journal.json` has ≥ 30 closed paper trades
- [ ] `python -c "from trade_journal import Journal; print(Journal().report())"` shows `EDGE` on ALL and on at least one signal type
- [ ] Corp passive-income treatment of the sleeve confirmed with accountant

If any of the above is not true, the sleeve stays paper.

---

## 8. Change log

| Date | Change |
|---|---|
| [today] | v1 scaffold created |
