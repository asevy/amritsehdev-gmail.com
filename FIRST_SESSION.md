# First session in Claude Code — checklist

You have 8 modules + this checklist. Goal of session 1: get everything running
on synthetic data, then wire ONE live feed. Do NOT fund real money yet.

## 0. One-time setup
- [ ] Put all files in a folder, then: `git init && git add -A && git commit -m "initial toolkit"`
- [ ] `python -m venv .venv && source .venv/bin/activate`
- [ ] `pip install -r requirements.txt`

## 1. Confirm every module runs (each has a built-in synthetic self-test)
- [ ] `python swing_scanner.py`      # MOVING_NOW vs LOADED scoring
- [ ] `python filing_forensics.py`   # forensic red-flag engine
- [ ] `python catalyst_calendar.py`  # catalyst timing curve
- [ ] `python intraday.py`           # RVOL / ORB / VWAP
- [ ] `python swing_pipeline.py`     # full pipeline: gates + scores + ranking
- [ ] `python account_router.py`     # account routing by holding horizon
- [ ] `python trade_journal.py`      # expectancy by signal type
- [ ] `python risk_manager.py`       # position sizing + circuit breakers
All should print sensible output with no errors.

## 2. Wire ONE live feed (start with yfinance, free)
- [ ] In `filing_forensics.py` set SEC_UA = "Your Name your-email@example.com"  (SEC requires it)
- [ ] Run a real daily scan:
      from swing_scanner import Scanner
      Scanner(exclude={"XEQT","ZEQT","XIC"}).scan(["NVDA","GEV","ETN","MRVL"])
- [ ] Run a real forensic report:
      from filing_forensics import forensic_report_for_ticker
      print(forensic_report_for_ticker("MRVL").summary)

## 3. Good prompts to give Claude Code
- "Review risk_manager.py and account_router.py line by line for correctness —
   these protect my capital, so check the math and the circuit-breaker logic."
- "Wire the live daily-scan adapter into swing_pipeline per the README, then run
   the full pipeline against this universe: [...]."
- "Build a backtester that replays the LOADED and MOVING_NOW signals over the
   last 2 years of daily data and reports expectancy in R-multiples by signal type."

## 4. Before any real money (the sequence is the safeguard)
- [ ] Keep RiskManager mode = "suggest" (not "auto")
- [ ] Paper-trade; let trade_journal.py accumulate a real sample
- [ ] Confirm expectancy is POSITIVE across enough trades
- [ ] Only then fund the $50k sleeve — active trades in personal non-registered,
      multi-week runners routed to TFSA per account_router
- [ ] Confirm the corporate passive-income / Small Business Deduction point with
      your accountant before finalizing which account holds the sleeve

## Honest reminder
This controls risk and focuses attention. It does NOT predict pops. LOADED coils
fizzle often; every trade needs its stop. The decision and the size stay yours.
