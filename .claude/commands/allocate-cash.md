---
description: Portfolio-level cash deployment plan. Reads holdings.json, analyzes gaps + market regime, produces tiered plan with tax-aware account routing. Distinct from /rebalance which adjusts existing weights.
---

# /allocate-cash -- Cash Deployment Strategy

Portfolio construction exercise: given cash + current exposures + regime, what to buy and where. **Not** a single-ticker recommendation.

## Input

- Default: read `holdings.json` (cash fields + holdings)
- `$ARGUMENTS` can override: e.g., `deploy 60% of cash, hold 40% reserve` or explicit cash amounts

If input is ambiguous, ask ONE targeted question, then proceed.

## Phase 1 -- Audit

**Journal pre-scan**: `Read memory/long_term/journal.md` (if exists). Filter last 30 days. Extract:
- "waiting for {TICKER} at {price}" entries → if current price has crossed trigger, surface as automatic Tier 1 candidate
- "passed on {TICKER}" entries → note why, don't re-recommend without new evidence
- "thesis-change on {TICKER}" entries → surface as candidate to trim
- Prepend a 3-bullet summary to Phase 4 candidate generation context

**Watchlist sanity check**: for each entry in `holdings.json watchlist[]`:
1. Pull `get_stock_info(ticker).currentPrice`
2. Parse the `note` field for direction keywords: `< $X` / `> $X` / `below X` / `above X`
3. If `note` says "waiting for < $X" but `current > X × 1.5` (target is 50%+ under current), emit `⚠️ {ticker}: target $X is {gap}% below current $Y -- check if target is stale (split? old thesis?)`
4. Same for inverse: note says `> $X` but current is already well above
5. Don't block; just surface. User fixes the note or removes the entry.

This catches dead watchlist entries from stock splits or thesis drift (e.g. GOOGL target `< $180` after the 20:1 split in 2022 when the note was written pre-split).

Read `holdings.json`. Compute:

**Totals**: MV per account (native + base currency), cash per account/currency, cash % of portfolio.

**Concentration -- aggregate by TICKER across accounts** (not by row). Same ticker in 2 accounts = 1 position. Report top 5 aggregate positions.

**Data integrity check**: for each holding, sanity-check `cost_basis` vs 5y price range. Flag if `>2× 5y_high` or `<0.5× 5y_low` → likely stale from split (see CLAUDE.md). Do not compute P&L on flagged positions.

**Exposure map** (parallel `get_stock_info` calls): sector, industry, country, currency, mcap tier, growth/value tilt.

**Risk profile**: weighted Beta, weighted yield (apply `safe_yield`), weighted PE, correlation clusters.

**Factor/style portrait** -- descriptive tags that feed the style verdict, anchored to real benchmarks. These are NOT independent gates; the tiered SPY-anchored rules in the Rules section handle concentration limits.

For each dimension, compute the number and compare to the benchmark:

| Factor | Measure | Benchmark | Tag when |
|---|---|---|---|
| Weighted β | portfolio β vs SPY=1.0 | SPY = 1.0 by definition | `>1.2` tilted offensive; `>1.4` levered |
| Growth tilt | % equity in (Fwd PE >25 AND zero div) | QQQ ~55% growth / IVW ~60% | `>50%` growth-duration bet |
| Momentum | % equity within 85-100% of 52w range | S&P momentum factor typically 20-40% | `>50%` momentum-crowded |
| Income | % equity with yield >3%; weighted avg yield | SPY ~1.1% / SPYD = 100% high-div | `>50%` income-oriented (valid strategy, not alarm). Individual yield `>6%` → cut-risk flag regardless of aggregate |
| Theme tag | % equity in single tag (ai / defensive / energy) | pure-theme ETFs run 100% | `>40%` themed bet (descriptive -- only alarming if unintended) |
| Cap tier | % mega / mid / small | SPY ~85% mega-cap baseline | `small+mid >30%` = deliberate cap tilt |
| Country | % by listing country | Canada = 2.5-3% of global MSCI; Vanguard CA research benchmark = 30% CAD for CA residents; current CA investor avg = 50% CAD | CAD `>60%` = notable home bias; any non-CA/non-US country `>10%` = explicit EM/international tilt |

Output ONE line **style verdict** summarizing the portrait (e.g., `"US mega-cap AI barbell with 45% Canadian dividend sleeve"`). The style verdict is usually more actionable than any single threshold.

**Tax lots**: flag large unrealized gains in taxable (tax drag to sell), unrealized losses (harvest candidates), TFSA with US high-yield (withholding trap).

## Phase 2 -- Regime (dispatch `macro-analyst`)

Pass portfolio character (sector mix, US/CA split). Get: current regime, rates/curve, upcoming catalysts, impact on actual holdings.

## Phase 3 -- Gaps

1. Over-weight (what to defer / trim before adding)
2. Under-weight / missing sectors
3. Expensive vs cheap among current holdings (quick `fundamentals-analyst` on top 3-5)
4. What regime favors that user lacks

## Phase 4 -- Candidates

Organize by role:

| Role | Criterion |
|---|---|
| Fill sector gap | Missing exposure regime needs |
| Add to winner | Conviction hold + reasonable valuation (must pass Phase 5 gates) |
| Defensive | Downside protection for current regime |
| Wildcard | Asymmetric upside contrarian |

For each candidate: quick `get_stock_info` for PE vs 5y avg, 52w position, dividend yield (via `safe_yield`), mcap. Mark if needs `/deep-dive` before buying.

## Phase 5 -- Deployment plan

```markdown
# 💰 Cash Deployment -- {YYYY-MM-DD}

## Snapshot
- Equity: $X | Cash: $Y ({%}) | Top 5 agg positions: {…}
- Style verdict: {one line}
- Biggest current risks: {…}

## Regime
{brief from macro-analyst}

## Gaps
{bullet list}

## Tier 1 -- Deploy now
| Ticker | Account | $ | Why |
|---|---|---|---|

## Tier 2 -- Staged triggers
| Ticker | Account | $ | Trigger |
|---|---|---|---|

Trigger format: concrete price level + ref date, e.g., `MSFT < $410 (current $424 as of 2026-04-21)`. Event triggers use concrete dates: `after 2026-04-29 FOMC`.

## Tier 3 -- Reserve
$Z held back. Reasons: {upcoming catalyst / Beta cap / dry powder}

## Not doing
- Chase {TICKER}: priced in
- Add to {SECTOR}: already concentrated
- TFSA high-yield US: withholding trap

## FX coordination
If rec requires currency user lacks in target account: state options -- (a) skip, (b) Norbert's Gambit via DLR/DLR.U (~0.01% cost, T+2), (c) broker spot conversion (~1.5%). Prefer CAD-listed US-exposure ETFs (e.g. VFV.TO, VUN.TO) to avoid FX entirely when possible.

## Follow-up
Run `/deep-dive` on any Tier 1 candidate lacking recent research.

Save to `memory/mid_term/{YYYY-MM-DD}-allocate-cash.md`.
```

## Rules

- Cite real tool-call numbers. No fabricated metrics.
- **Concentration -- tiered, anchored to SPY (active-investor philosophy, see CLAUDE.md)**. No hard caps; research-backed concentration is acceptable.

  *Industry* (vs current SPY sector weight, e.g. Tech ~32%, Healthcare ~11%, Financials ~13%):
  | Excess over SPY | Action |
  |---|---|
  | `< +10pp` | quiet pass |
  | `+10-20pp` | flag "above SPY benchmark" in output |
  | `+20-30pp` | DRAFT + user confirm |
  | `> +30pp` | HIGH-RISK gate |

  *Single ticker* (vs SPY top holding ~7%):
  | Position size | Action |
  |---|---|
  | `≤ 7%` | quiet pass (passive-index level) |
  | `7-12%` | flag "active concentration zone" |
  | `12-20%` | DRAFT + require /research run within last 30 days + written downside plan |
  | `> 20%` | HIGH-RISK gate, needs explicit thesis + stop-loss line |

  **Pulling live SPY benchmarks**: `get_stock_info('SPY')` does NOT expose sector weights -- it returns `category: "Large Blend"` only. Use the repo tool:
  ```bash
  # run via a Python env with yfinance available (e.g. the Yahoo Finance MCP venv)
  python tools/benchmark.py spy-sectors
  python tools/benchmark.py spy-top-holdings
  ```
  Outputs JSON with current sector_weights dict and top holdings list. Fall back to last-known snapshot if offline: Tech ~33%, Financials ~12%, Healthcare ~9%, Comm ~10%, Industrials ~8%, Consumer Cyc ~10%, Consumer Def ~5%, Energy ~4%, Utilities ~2.5%, Materials ~2%, Real Estate ~2% (as of 2026-04).

- **"Add to winners" gates -- BOTH must pass**: (1) 52w position ≤ 85%, (2) analyst consensus buy ≤ 80%. Any fail = skip. Mirrors Munger/Burry counter-consensus. Position size itself is governed by the tiered rule above.
- **Reserve default**: ≥15-20% cash held back unless user overrides. Cash is optionality on opportunity.
- **Staging bias**: prefer tranched entries with triggers over all-in, unless position is small.
- **Tax routing** (see CLAUDE.md for full rules): always state `account_id` for each rec.

## High-risk gate → DRAFT + confirm

Any of: single rec >5% portfolio (trade-size gate) | resulting single-ticker holding >12% (concentration gate -- HIGH-RISK at >20%) | industry >SPY+20pp (HIGH-RISK at >+30pp) | total deployment >70% cash | **trade volume >20% of equity** | Beta delta >0.3 | net reduction in defensive holdings → output as DRAFT, list high-risk aspects, ask user before finalizing.
