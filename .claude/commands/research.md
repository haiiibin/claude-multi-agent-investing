---
description: Deep research on a single ticker across 5 agent personas + tax-aware "already own" analysis across taxable / TFSA / registered accounts. Usage /research AAPL
---

# /research TICKER -- Deep Ticker Research (Tax-Aware)

Multi-agent deep-dive on a single ticker. Ticker from `$ARGUMENTS`. If no argument given, ask which ticker.

**Ticker normalization** (CLAUDE.md quirk): class-share tickers use `-` in yfinance, not `.`. Before any tool call, normalize `BRK.B` → `BRK-B`, `BF.B` → `BF-B`, etc. Echo user's original spelling in output.

## Phase 1 -- Context load

Read `portfolio/holdings.json`. Find all positions in this ticker across accounts:
- Which accounts already hold it?
- Cost basis + shares in each account
- Is it in watchlist? For which target account?

**Memory search protocol (specific steps):**

1. Run `Glob` with pattern `memory/mid_term/*{TICKER}*.md` to find prior research/deep-dive artifacts on this ticker
2. Run `Glob` with pattern `memory/mid_term/*market-pulse*.md` sorted by filename (dates embedded) -- take the most recent
3. For each ticker match, check filename date. Keep only files < **14 days old**; older artifacts are stale
4. `Read` the top 1-2 most recent files (don't flood context with everything)
5. **Journal lookup** -- `Read memory/long_term/journal.md` and grep entries mentioning `{TICKER}` in the last 90 days. These capture "why I passed last time" / "waiting for X" decisions that shouldn't be forgotten. Especially watch for `thesis-change` tags.
6. Summarize key facts (current price anchor, last thesis, agent signals, any follow-up items, prior journal decisions)
7. **Prepend this summary** to the context bundle sent to each persona -- they argue better with hard numbers already in hand
8. If no recent matches exist, tell the user: "No recent research on this ticker -- consider running `/deep-dive {TICKER}` first for a fact-heavy session"
9. If a `/research` was run within the last 3 days, **warn the user**: "Already analyzed 3 days ago -- re-running now may give echo results. Skip unless material new info."

## Phase 2 -- Parallel persona analysis

Dispatch **5 sub-agents in parallel** via Task tool in a single message:

1. `buffett` -- moat / intrinsic value / margin of safety
2. `munger` -- inverted red flags
3. `burry` -- deep value / catalysts
4. `bull` -- strongest bull case
5. `bear` -- strongest bear case

Each agent calls `mcp__yahoo-finance__*` tools independently + receives any deep-dive facts as briefing context.

## Phase 3 -- Synthesis

### Vote-counting rule (Bull/Bear are advocates, not signal)

Bull and Bear are forced-argument personas. Their default output is "here's the strongest case for my side" -- which is useful for steel-manning but is NOT a signal on its own. Rules:

- **Bull returning `bullish` + Bear returning `bearish`**: normal -- they were asked to argue. Neither counts toward consensus. Look at Buffett/Munger/Burry for signal.
- **Bull returning `no-case`**: strong bearish signal (if an advocate can't find material, there isn't any). Count as −1 toward bullish.
- **Bear returning `no-case`**: strong bullish signal. Count as +1 toward bullish.
- Buffett / Munger / Burry each count as ±1 based on their `bullish` / `bearish` / `neutral` output.

### Tie-breaker rule for all-neutral outcome

If **Buffett + Munger + Burry all return `neutral`** (Bull/Bear don't count for this test), do NOT synthesize another "neutral with medium confidence" response. That's useless. Instead:

1. Explicitly label the outcome as **"pass -- insufficient signal"**
2. For each neutral agent, ask: **what specific metric change would flip them**? Examples:
   - Buffett flips bullish if: margin of safety > 20% (implies price drop of $X from current)
   - Burry flips bullish if: FCF yield > 8% (implies price drop of $X OR 30% FCF growth)
   - Munger flips bearish if: any of 6 red flags trip (list which is closest)
3. Output the minimum **price level** or **metric threshold** where the council reorients. This converts a non-answer into a concrete watch condition.
4. If the user is already holding this ticker, a "pass -- insufficient signal" translates to **hold** (no action). If not holding, translates to **skip**, set watchlist entry with the flip threshold.



Consolidated output:

```markdown
# 🔍 Research: {TICKER}

## Snapshot
- Price: $X
- Market cap / PE / dividend yield / payout ratio
- 52w position
- Primary listing / currency (matters for account routing)

## The council

| Agent | Signal | Confidence | Key point |
|-------|--------|------------|-----------|
| Buffett | bullish/bearish/neutral | NN% | one-line |
| Munger | ... | ... | red flags |
| Burry | ... | ... | FCF/catalyst |
| Bull | -- | -- | thesis |
| Bear | -- | -- | biggest risk |

## Where they agree
- ...

## Where they disagree
- ...

## My synthesis
- **Leaning:** bullish / bearish / neutral / pass
- **Conviction:** Low / Medium / High
- **What would change my mind:** ...

## 💼 Your position (from holdings.json)

**If you already own it:**
| Account | Shares | Cost basis | Current value | P&L | Tax status |
|---------|--------|------------|---------------|-----|------------|
| broker-a-taxable | 50 | $150 | $9,125 | +21.7% | 📉 Taxable -- selling triggers capital gains |
| broker-b-tfsa | 20 | $140 | $3,650 | +30.4% | 🎁 TFSA -- selling is tax-free |

**Total exposure:** N shares across X accounts = $NNN (Y% of total portfolio)

**Tailored action:**
- If trimming: **sell from {best account by tax rule}** first
- If adding: **buy in {best account by asset type}** -- see CLAUDE.md routing rules
- If cutting loss: check if any taxable account has unrealized loss for tax-loss harvest

**If you don't own it (or it's in watchlist):**
- **First: read `holdings.json` to enumerate user's ACTUAL accounts** -- don't assume a fixed set.
- **Then route** based on `account_type` + currency + this ticker's yield:
  - US **dividend** stock (yield > 2%) → any `taxable` USD account (FTC recovers withholding); **AVOID `tfsa`** (15% withholding is permanent loss there)
  - Canadian dividend stock → `taxable` CAD (dividend tax credit) or `tfsa` (fully tax-free)
  - High-growth / zero-dividend → `tfsa` first (amplify tax-free gains)
  - USD-denominated asset → USD-base account (save FX)
  - CAD-denominated asset → CAD-base account (save FX)
- **Recommended size:** $X (suggest % of portfolio based on conviction)
- **Entry zone:** $X–$Y based on analysis

## ⚠️ Before acting
- Position size if adding: $X (Y% of portfolio)
- Max drawdown to tolerate: Z%
- Account capacity: TFSA contribution room? Foreign content limits?
```

## Phase 4 -- Save research

Save to `memory/mid_term/{YYYY-MM-DD}-{TICKER}-research.md`.

## Rules

- **Never actually trade.** Advisory only.
- **Cite real numbers from tool calls**, not memory.
- If ticker is held in multiple accounts, **always enumerate each account's position** -- not just total.
- **High-risk flag**: if output suggests a real buy/sell action, surface it clearly and ask user to confirm before any follow-up (e.g. before editing holdings.json to reflect a hypothetical trade).
