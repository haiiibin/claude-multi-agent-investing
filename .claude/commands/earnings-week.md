---
description: Upcoming earnings + dividend events for portfolio holdings over next N weeks (default 2). Surfaces event clusters (multiple positions on same day = concentrated event risk), consensus estimates, key questions to watch. Run before FOMC/earnings-heavy weeks.
---

# /earnings-week -- Upcoming Earnings & Dividend Events

Portfolio-level calendar view of near-term catalysts. Answers: "what's going to move my positions this week/next week?"

Default window: **14 days**. Accept `$ARGUMENTS` like `/earnings-week 7` or `/earnings-week 30`.

## Phase 1 -- Collect

**Journal pre-scan** (if `memory/long_term/journal.md` exists): grep entries with tags `earnings-pending`, `thesis-test`, `waiting-for-print` within last 30 days. Surface these at the top of the output -- the user's past written stance on "I want to see X in this print" is high-signal context for framing the watch items.

Read `holdings.json`. For every unique ticker across all accounts, pull `t.calendar` from yfinance via MCP (`mcp__yahoo-finance__get_stock_info` may not have this -- may need to call via Bash with Python if MCP tool limits). The calendar dict contains:

- `Earnings Date` -- when they report
- `Earnings High / Low / Average` -- consensus EPS estimate range
- `Revenue High / Low / Average` -- consensus revenue estimate range
- `Dividend Date` -- when dividend is paid
- `Ex-Dividend Date` -- last date to own before the dividend

**Filter to events within `$window_days` (default 14).**

## Phase 2 -- Enrich each earnings event

For each upcoming earnings, collect:

1. **Price context**: current price, 52w position, 1-month change, implied pre-earnings run-up
2. **Consensus vs history**: estimate average, range width (narrow = consensus tight = bigger surprise potential); look up last 2 quarters' beat/miss via `WebSearch` if time permits
3. **Options market implied move** (optional, via `mcp__yahoo-finance__get_option_chain` -- look at ATM straddle for nearest expiry covering the event): `implied_move = (ATM_call + ATM_put) / stock_price`
4. **Key watch items** -- 2-3 specific things to check in the print:
   - e.g., MSFT: "Azure growth constant currency", "Copilot ARR disclosure", "CapEx guide for FY27"
   - Use ticker + "earnings preview" in WebSearch if specific items aren't known

## Phase 3 -- Identify clusters

Flag **event clustering**: if 2+ positions report on the same day, portfolio has **concentrated event risk**. Example: MSFT + META + GOOGL + AMZN all report 2026-04-29.

Calculate: what % of portfolio reports in any single day within the window? If > 25%, flag loudly.

## Phase 4 -- Output

```markdown
# 🗓️ Earnings Week -- next {N} days (as of {YYYY-MM-DD})

## Summary
- Positions reporting: M of N holdings
- Positions going ex-dividend: K
- **Cluster risk**: {date} has X% of portfolio reporting (FLAG if >25%)

## Earnings events (chronological)

### 📅 2026-04-29 (Wed) -- 45% of portfolio reports
| Ticker | Account | Position | Price | 52w pos | Consensus EPS | Implied move | Watch |
|---|---|---|---|---|---|---|---|
| MSFT | broker-a-taxable | 30 sh @$380 | $424 | 34% | $4.07 (±0.14) | ±4.2% | Azure growth CC / Copilot ARR / CapEx FY27 |
| META | broker-a-taxable | 30 sh @$220 | $669 | 85% | $6.74 (±0.83) | ±5.8% | Ad revenue / Reality Labs losses / AI capex |
| GOOGL | -- (not held, but in watchlist) | -- | $X | Y% | $Z | ±W% | -- |

### 📅 2026-04-30 (Thu)
| AAPL | broker-a-taxable | 40 sh @$170 | $266 | 93% | $1.95 (±0.21) | ±3.8% | Services growth / iPhone units / China |

### 📅 2026-05-20 (Tue)
| NVDA | broker-b-tfsa | 15 sh @$130 | $200 | 89% | $1.77 (±0.15) | ±7.5% | Data center guide / Rubin timeline / ASIC commentary |

## Dividend events (ex-dates in window)
| Ticker | Account | Ex-div date | Payment | Per share | Your cash | Tax note |
|---|---|---|---|---|---|---|
| ENB.TO | broker-b-taxable | 2026-05-15 | 2026-06-01 | $0.94 CAD | $94 | Eligible dividend -- DTC applies |
| MSFT | broker-a-taxable | 2026-05-20 | 2026-06-10 | $0.83 USD | $24.90 | 15% US withholding in broker-a-taxable (taxable = creditable as FTC) |

## What this means for you

### Event-cluster risk
⚠️ **April 29 concentrates 45% of portfolio on one day**. If you want to hedge, options:
- Accept the risk (highest expected value if all prior quarters beat consensus)
- Trim 10-20% of each position ahead of print (reduce exposure, pay brokerage + tax on gain)
- Buy ATM puts on SPY as portfolio insurance. Rule-of-thumb 30-day ATM put cost ≈ `VIX / sqrt(12) × 0.4` as % of notional: ~1.5-2% at normal VIX (15-18), 3-5% at elevated VIX (25+). Check current VIX before citing a number.

### Per-position check
- **MSFT**: thesis depends on Azure ≥ 37%. If guide comes below, stop-loss-like reaction warranted -- see your prior `/research MSFT` notes if any.
- **NVDA**: already near 52w high + 1m later. Higher risk the print disappoints. Reminder: your thesis tag says "expect ASIC pressure after 2028" -- listen for Rubin positioning vs TPU v7 Ironwood.

## Skipped holdings
- No upcoming events for: VOO, SHOP.TO, BA, INTC
- Missing calendar data for: (any tickers where yfinance returned empty)
```

## Rules

- **Advisory only. Don't recommend trading around earnings unless user asks.** The job is surfacing information, not timing signals.
- **Implied move is cheap data but require options chain MCP call** -- if chain is empty (low-liquidity name), skip rather than fake
- **Dividend tax implications are account-specific**: always state the account + tax treatment (TFSA gets 15% US withholding; taxable gets dividend tax credit for Canadian eligible divs; etc.)
- **Don't duplicate `/deep-dive` or `/research`** -- this is a calendar, not a research report. One-line per ticker, not paragraphs.
- **Cluster warning threshold**: 25% of portfolio on a single day = high. 40% = very high. State specific %.
- **Save**: append to `memory/short_term/{YYYY-WW}-earnings-week.md` (short-term because it decays fast)
