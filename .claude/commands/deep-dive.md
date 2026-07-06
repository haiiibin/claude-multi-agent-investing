---
description: Full intelligence gathering on a ticker -- fundamentals + SEC filings + news + macro + competitors. Slower and deeper than /research. Usage /deep-dive AAPL
---

# /deep-dive TICKER -- Intelligence Gathering

Deepest single-ticker analysis in the system. Use when you're seriously considering opening or materially changing a position. Takes ~3-5 minutes.

`/research` is for quick multi-persona debate.
`/deep-dive` is for **information gathering** -- get all the facts on the table before forming an opinion.

Ticker from `$ARGUMENTS`. If missing, ask.

**Ticker normalization** (CLAUDE.md quirk): normalize `BRK.B` → `BRK-B`, `BF.B` → `BF-B` before tool calls. Echo user's spelling in output.

## Phase 1 -- Context (read-only, fast)

1. **Portfolio context**: Read `portfolio/holdings.json`. Aggregate by ticker across ALL accounts (same ticker in 2 accounts = one position for exposure calculation). Note: already held? In which accounts? Total shares? Weighted avg cost? In watchlist?

2. **Memory lookup (specific steps)**:
   - `Glob` pattern `memory/mid_term/*{TICKER}*.md` -- find prior artifacts
   - Filter to files < **90 days old** by filename date
   - If found, `Read` the most recent 1-2 files and summarize key prior findings
   - Use this to avoid re-gathering same facts (e.g., if 10-K already extracted 30 days ago, only pull 10-Q delta)
   - If a `/deep-dive` was run within 14 days, **ask user if they want incremental update or full redo** -- don't silently duplicate
   - **Journal lookup** -- `Read memory/long_term/journal.md` (if exists) and grep entries mentioning `{TICKER}` within last 120 days. Surface: "passed on this ticker 60 days ago at $X because Y" / "flagged thesis-change on this ticker 30 days ago". A deep-dive that ignores user's prior documented stance is wasted effort.

## Phase 2 -- Parallel intelligence dispatch

Dispatch **4 sub-agents in parallel** via Task tool in a single message:

1. `fundamentals-analyst` -- 4 years of statements, quality-of-earnings check
2. `news-analyst` -- last 30 days news, sentiment, actionable events
3. `sec-filings-analyst` -- latest 10-K risk factors, 10-Q changes, recent 8-Ks, insider activity (US-listed only; skip if Canadian)
4. `macro-analyst` -- current regime + specific impact on this ticker / sector

## Phase 3 -- Competitor & industry context (sequential, after phase 2)

Use `WebSearch` + `WebFetch` to gather:
- **Top 3 direct competitors** (by name), their ticker, their valuation multiples
- **Industry tailwinds / headwinds** (1–2 major)
- **Company's moat / differentiation** as described by management vs as observed in numbers

## Phase 4 -- Valuation check

Use fundamentals-analyst output + `mcp__yahoo-finance__get_stock_info` to compare:
- Current PE vs 5-year avg PE
- Current EV/EBITDA vs 5-year avg
- FCF yield vs 5-year avg
- Price / sales vs sector median
- Distance from 52w high/low

Rough DCF sanity check: can the current market cap be justified by reasonable FCF growth + discount rate assumptions?

## Phase 5 -- Synthesis

```markdown
# 🔬 Deep Dive: {TICKER} -- {Company name}

## TL;DR (3 sentences)
What the company does. What's interesting. Verdict in one word.

## Business & Moat
- What they sell, who to, how they make money
- Moat assessment (pricing power / switching cost / network effect / brand / scale)
- Where revenue comes from (segments, geographies, customers)

## Financial Health (from fundamentals-analyst)
{condensed health card -- growth / profitability / balance sheet / cash quality}

**One-line verdict:** {quoted from fundamentals-analyst}

## What SEC Filings Actually Say
{condensed from sec-filings-analyst -- top risks, MD&A themes, recent 8-Ks, insider activity}

## News & Narrative (last 30 days)
{condensed from news-analyst -- sentiment, top events}

## Macro Context
{condensed from macro-analyst -- regime impact on this name}

## Competitive landscape
| Competitor | Ticker | Market cap | PE | Note |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

## Valuation Scorecard
| Metric | Current | 5y Avg | Sector Median | Verdict |
|--------|---------|--------|---------------|---------|
| PE | 28 | 24 | 22 | Premium |
| EV/EBITDA | 20 | 18 | 14 | Premium |
| FCF yield | 3.6% | 4.5% | 5% | Expensive |
| P/S | 6.5 | 5.8 | 3 | Premium |

**DCF sanity:** requires ~8% FCF CAGR for 10 years at 10% discount to justify current price. Is that realistic given base business growth of 6%?

## Bull case (the strongest 3 points)
1. ...
2. ...
3. ...

## Bear case (the strongest 3 points)
1. ...
2. ...
3. ...

## My synthesis (not a buy/sell recommendation)
- **Lean:** bullish / bearish / neutral / pass
- **Conviction:** Low / Medium / High
- **Time horizon this view holds for:** ...
- **What would change my mind:** ...

## For YOUR portfolio specifically
(read holdings.json -- account-aware)
- If you already own: {current position + tax-aware trim/add/hold analysis}
- If you're considering: {best account to buy + suggested sizing + entry zone}
- **Risk before acting:** max drawdown tolerance, position size limit

## Saved as
`memory/mid_term/{YYYY-MM-DD}-{TICKER}-deep-dive.md`
```

## Rules

- **Advisory only -- never actually trade.**
- **Cite real numbers** from tool calls, not memory. Every number should be traceable to a tool output.
- **Respect the user's actual accounts** -- read holdings.json, never assume.
- If data is unavailable (e.g. non-US ticker has no SEC filings), state clearly -- don't fabricate.
- High-risk flag: if recommending a real action (buy/sell > 5% of portfolio), stop and ask user before any follow-up.
