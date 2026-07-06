---
description: Portfolio scenario stress test. 6 canonical macro shocks historically anchored (2008/2020/2022). Outputs per-scenario CAD loss + worst positions. Deterministic, not Monte Carlo. Directional -- not point forecasts.
---

# /stress-test -- Portfolio Scenario Stress Test

Answers: "if regime shifts violently, where do I bleed?" Default: all 6 scenarios. Custom via `$ARGUMENTS`.

## Scenarios (canonical shocks, historical anchors)

| # | Scenario | Anchor | Key shocks |
|---|---|---|---|
| 1 | **Recession hard landing** | 2008 GFC (-56%), 2020 Mar (-34%/mo) | SPY -30, QQQ -35, IWM -40, 10Y -150bp, Oil -40, Gold +10, USD +5, credit +300bp |
| 2 | **Stagflation** | 2022 (QQQ -33, oil +40) | SPY -20, QQQ -30, IWM -15, 10Y +200bp, Oil +40, Gold +25, USD +8, high-PE (>30) -40 |
| 3 | **AI capex pause** | 2000 dotcom (QQQ -83), 2022 Q4 | AI infra (semi) -45, hyperscalers -25, non-AI software -15, AI utilities -50, non-tech -5 |
| 4 | **USD spike (tariff shock)** | 2014-15 (+25), 2022 DXY breakout | DXY +10, USD/CAD 1.36→1.50, US multinationals -8, EEM -20, Gold -12, CAD domestic -3 |
| 5 | **Geopolitical shock** | 2022 Russia, 1973 embargo | Oil +50, Natgas +60, Gold +20, VIX +150, SPY -12, Defense +15, airlines -25, energy +25 |
| 6 | **China decoupling** | 2018-19 trade war, 2025 H20 ban | Semi w/ China expo -20, AAPL -15, Chinese ADRs -35, onshoring/defense +10, rare earths +25 |

Scenario sensitivity: high-beta -1.5× worse in #1, duration (long-growth) worst in #2, anything tagged `ai` hit first in #3.

## Phase 1 -- Load portfolio

Read `holdings.json`, aggregate by ticker. For each: current price, sector, beta, mcap, tags. Foreign-rev % via `get_stock_info.country` or WebSearch when geographic split matters (#4, #6).

**Tag sanity check**: compare every tag encountered in `holdings.json` to the canonical vocabulary in CLAUDE.md. If any tags are off-list (e.g. `AI` instead of `ai`, or `artificial-intelligence`), emit a WARN line at the top of the output -- don't block, but the user should know a shock might silently skip them.

## Phase 2 -- Apply shocks

Shock source priority (use **worst applicable**, don't multiply):
- Direct ticker mapping (VOO ~ SPY)
- Sector mapping (scenario "tech -35" → Technology holdings)
- Tag mapping (scenario "AI -45" → `ai` tagged holdings)
- Beta mapping (stock shock ≈ Beta × market shock)

**FX computation (strict order, no double-counting):**
1. Apply equity shock in native currency: `shocked_usd = current_usd × (1 + equity_shock)`
2. Convert shocked USD value to CAD at NEW rate: `shocked_cad = shocked_usd × shares × new_usdcad`
3. Baseline for comparison: `baseline_cad = current_usd × shares × current_usdcad`
4. Net shock in CAD: `shocked_cad - baseline_cad` (reflects both effects multiplicatively)

❌ Never sum "equity loss" + "FX gain" as separate line items. Compose them.

CAD-denominated positions: equity shock only, no FX.

Report in CAD for CDN-resident investor.

## Phase 2.5 -- Idiosyncratic single-ticker layer

Systemic sector/beta shocks **underestimate concentration risk**. A 15% NVDA position in "China decoupling" isn't just "semi sector -20%" -- it's NVDA-specific -40% to -50% because the scenario targets that specific name.

For every position **> 10% of portfolio**:

> **Why 10% here but 12% for the concentration DRAFT gate in CLAUDE.md?** Tail-risk measurement is strictly stricter than position-size review. A position in the 10-12% band doesn't trigger DRAFT (user doesn't need to confirm the position exists), but it still contributes enough to portfolio dollar loss in a −50% blow-up that it should be visible in stress output. The 10% threshold here is deliberately earlier.


1. Apply the systemic scenario shock as usual (Phase 2)
2. **Additionally**, run a parallel "ticker-specific blow-up" layer:
   - Single-stock shock: `-30%` standard, `-50%` for the specific ticker if scenario directly targets it (e.g., NVDA in #3 or #6, Canadian banks in #1, AAPL in #6)
   - This is NOT added to the systemic shock -- it **replaces** it for that position in this sub-scenario (ticker-specific blow-up dominates macro shock)
3. Report as a separate row in the output: "if your top concentrations each blew up 30% while scenario unfolds"

Rationale: empirically, single-stock drawdowns of 30-50% within broader bear markets are common (META −77% in 2022, NFLX −76% in 2022, PYPL −80% 2021-2023 during mild market). Sector beta underestimates these.

## Phase 3 -- Output

```markdown
# 🩻 Stress Test -- {YYYY-MM-DD}

## Current
- Portfolio (CAD): $X | Cash: $Y ({%}) | Top concentration: {ticker} {%}

## Scenario summary
| # | Scenario | CAD loss | Worst 3 | Best 3 |
|---|---|---|---|---|
| 1 | Recession | -$28k (-32%) | {…} | {…} |
| ... | | | | |

## Worst case detail
Top 5 by loss with 1-line "why" per position (cite Beta + sector/tag shock applied). Include recovery-time historical anchor (e.g., 2008→2013 5yrs, 2020→6mo w/ Fed).

## Concentration stress (positions > 10% of portfolio)

Systemic shocks under-estimate idiosyncratic risk. Per Phase 2.5:

| Ticker | Weight | Systemic shock | Ticker blow-up (−30%) | Worst-case CAD loss |
|---|---|---|---|---|
| NVDA | 14% | −22% (scenario #3) | −50% (AI capex directly hits NVDA) | −$X |
| BCE.TO | 11% | −8% | −30% (single-stock div cut) | −$Y |

**Cumulative tail** (if top 3 concentrations each blow up 30-40% in worst scenario): $Z loss. Compare to 1 year of saving rate.

## Hidden resilience
Identify any scenario where current exposure helps (e.g., USD holdings as CDN-recession hedge in #4).

## Blind spots
Scenarios without a hedge in current book. Common: gold for stagflation/geopolitical; short-duration TIPS for inflation; AI-tag trim for capex pause.

## Key takeaways (3-5 bullets)
Biggest risk, asymmetric cash opportunity, concentration sensitivity (e.g., "NVDA 3.5% weight but Beta 2.3 = ~10% of worst-case loss"), FX as stealth hedge, etc.

Save to `memory/mid_term/{YYYY-MM-DD}-stress-test.md`.
```

## Rules

- **Directional, not point forecasts.** State up front.
- **Anchor every shock to historical event.** No vibes.
- **Report in CAD** (CDN resident).
- **No trade recommendations from this command** -- awareness only. Redirect to `/rebalance` or `/allocate-cash` if action needed.
- **Empty holdings**: state "nothing to stress-test" and stop. Don't invent.
- **Don't double-apply**: tech + beta → use worst single, not compound.

## Custom scenarios

```
/stress-test custom SPY:-15% oil:+50% 10Y:+100bp
```

Parse args, apply same methodology.
