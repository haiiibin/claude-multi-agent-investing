---
description: Market-wide macro scan -- indices, rates, FX, commodities, sector rotation, upcoming catalysts. Run before /allocate-cash or /rebalance to ground portfolio decisions in current regime.
---

# /market-pulse -- Market & Macro Scan

Broad environment scan. **Not portfolio-specific.** Tells you what the market is doing so you can interpret your holdings in context.

## Steps

1. **Dispatch `macro-analyst` sub-agent** via Task tool. Pass target = "broad market" (no specific ticker).

2. The agent will pull (parallel):
   - Indices: SPY, QQQ, IWM, VIX
   - Rates: ^TNX (10Y), ^IRX (3M), ^FVX (5Y) -- curve shape
   - FX: DXY/UUP, CAD=X (USD/CAD)
   - Commodities: CL=F (oil), GC=F (gold), NG=F (natgas)
   - Sectors: XLK XLF XLE XLV XLY XLP XLI XLU XLRE XLB XLC
   - Risk-on proxy: BTC-USD

3. **Upcoming catalysts.** Use `WebSearch` for:
   - Next FOMC meeting date + market-implied odds
   - Next CPI release date
   - Next NFP (jobs) date
   - Major earnings this week (MAG-7 / banks / bellwethers)

4. **Produce the pulse:**

```markdown
# 🌎 Market Pulse -- {YYYY-MM-DD}

## Regime
**{Risk-on reflation / Risk-on disinflation / Risk-off stagflation / Risk-off deflation / Chop}** -- confidence: {Low/Med/High}

One-sentence rationale.

## Snapshot (1-day / 1-week / 1-month)
| Asset | 1D | 1W | 1M | Level |
|-------|-----|----|----|-------|
| SPY | +0.3% | +1.2% | +2.1% | 580 |
| QQQ | ... | ... | ... | ... |
| VIX | | | | 16.8 |
| US 10Y | | | | 4.25% |
| DXY | | | | 105.2 |
| USD/CAD | | | | 1.37 |
| Oil | | | | $78 |
| Gold | | | | $2340 |

## Sector rotation (1-month)
🟢 Leaders: XLE +5%, XLF +3%, XLI +2%
🔴 Laggards: XLU -1%, XLK -0.5%, XLRE -0.8%

**Rotation thesis:** {1 sentence -- what leadership is saying about the cycle}

## Yield curve
- 3M: 5.20% | 2Y: 4.50% | 10Y: 4.25% | 30Y: 4.40%
- Curve shape: {inverted / flat / normalizing / steepening}
- Implication: ...

## Upcoming catalysts (next 2 weeks)
- **FOMC 2026-05-07** -- market pricing 25bp cut at 45%
- **CPI 2026-05-14** -- consensus 2.8% YoY
- **Big earnings**: NVDA (Wed), JPM (Thu), TSLA (next Mon)

## Implications for a long-only investor
- Positioning: ...
- What to watch: ...
- What to avoid: ...

## Implications for YOUR portfolio
(read `portfolio/holdings.json` and flag holdings most affected by current regime)
- **AAPL** (broker-a-taxable) -- USD-strong regime is revenue headwind (60% foreign); watch next earnings for FX commentary
- **ENB** (broker-b-taxable) -- oil up + rates stable = tailwind; dividend sustainable

## Save
Save this report to `memory/mid_term/{YYYY-MM-DD}-market-pulse.md` for later context.
```

## Rules

- **Cite real numbers** from MCP tool calls. No estimates.
- **Regime calls are probabilistic** -- use hedges when appropriate.
- **Link macro to actual holdings** -- this is the main value vs generic market reports.
- Keep it to one page (< 500 words of prose). Dense tables over paragraphs.
