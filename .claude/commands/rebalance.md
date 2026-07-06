---
description: Drift-based rebalancing. Detects positions deviating from target weights, proposes tax-ordered trim + add. Distinct from /allocate-cash (which deploys NEW cash) -- /rebalance is zero-net-cash reshuffling.
---

# /rebalance -- Drift-Based Rebalancing

/allocate-cash: "have cash, what to buy" | /rebalance: "positions drifted, trim winners + add laggards"

## Input -- target weights

Priority order:

1. **Per-holding** `target_weight` field in `holdings.json`
2. **Top-level** `targets: { sectors: {…}, asset_class: {…} }` in `holdings.json`
3. **Arg override**: `/rebalance equal-weight` | `cap-weight` | `strategic 60/30/10`
4. **None found**: don't invent. Ask user which framework or which weights.

## Phase 1 -- Current state

**Journal pre-scan**: `Read memory/long_term/journal.md` (if exists). Filter last 60 days. Flag any `thesis-change` tags for tickers still in portfolio → these become priority trim candidates in Phase 3, regardless of drift math.

Read `holdings.json`, aggregate by ticker cross-account. Compute:
- MV per ticker (base currency), `weight = MV / total_equity` (cash excluded from denominator)
- Cash weight separately (`cash / total_portfolio`)
- Sector, country, asset-class weights
- Drift per dimension vs target

## Phase 2 -- Drift thresholds

- Absolute drift: `current - target`
- Relative drift: `(current - target) / target`
- **Trigger**: abs >5pp OR rel >25%
- **Urgent**: abs >10pp
- **Ignore**: abs <2pp (micro-drift, not worth trading cost)

## Phase 3 -- Propose trades

### Over-weight → trim (tax-efficiency order)

1. TFSA with gains → tax-free realization, trim first
2. Taxable with **unrealized loss** → rebalance + harvest (double benefit; check 60-day superficial loss per CLAUDE.md)
3. Taxable with short holding → at least not worse
4. Taxable with large gain → trim last

State tax implication per sale (cite pooled ACB per CLAUDE.md, not per-account cost basis).

### Under-weight → add (account selection)

1. Currency match (USD→USD account)
2. Account fit: zero-div growth→TFSA; US high-div→taxable USD (FTC); CAD div→CAD taxable (DTC)
3. Sufficient cash in target account

**If target is TFSA -- mandatory checks** (prevent CRA 1%/month penalty):
- Read `accounts[].contribution_room_remaining`. If `null` → warn user to verify at CRA My Account before buying.
- Check `memory/long_term/trades.md` for same-year TFSA sells. If cash came from same-year withdrawal, room does NOT restore until Jan 1 next year. **Refuse** TFSA buy unless user confirms they understand.

**Respect recent /allocate-cash reserve floor**:
1. `Glob memory/mid_term/*allocate-cash*.md` for plans <30 days old
2. If found, check "Tier 3 -- Reserve" dollar floor
3. If this buy would breach it → present as optional with: "Would reduce cash below $X reserve from YYYY-MM-DD plan -- overriding intentionally?"
4. No recent plan: default floor = 15% of portfolio cash

If account cash insufficient: flag. **Don't silently suggest selling another position to fund** -- that's a separate decision.

## Phase 4 -- Output

```markdown
# ⚖️ Rebalance -- {YYYY-MM-DD}

## Targets (source: {holdings.json | args | user-specified})

## Current
- Equity $X | Cash $Y ({%}) | N unique tickers

## Drift

### 🔴 Urgent (>10pp)
| Dimension | Item | Target | Current | Drift | Action |

### 🟡 Normal (5-10pp)
| … |

### 🟢 Tolerance (<5pp)
{list, no action}

## Trade list (tax-ordered)

### Sells
{Per sale: ticker, account, $, tax cost, realized gain/loss, account rationale}

### Buys
{Per buy: ticker, account, $, currency/FX note, account rationale}

## Net change
- Cash delta: $X
- Tax impact (estimated): $Y
- Projected new weights: {before → after}

## NOT doing
- {tickers to skip (no position in that account, earnings <7 days, etc.)}
- Churn <5pp micro-drift

Save to `memory/mid_term/{YYYY-MM-DD}-rebalance.md`.
```

## Rules

- Advisory -- user executes on broker then `/trade` to sync.
- **Don't chain "sell X to fund Y"** unless user asks. Separate decisions.
- **Earnings cross-check**: any ticker reporting <7 days → warn, suggest `/earnings-week` first.
- **Cost basis quirks** (CLAUDE.md): if flagged stale, don't compute realized P&L -- ask user.
- **Don't invent targets**. Ask if none provided.
- **Micro-drift (<2pp)**: explicitly say "no action" instead of churning.

## High-risk gate → DRAFT + confirm

- Realized gain >5% of portfolio (tax-expensive)
- Cross-currency trades >20% of cash (FX erosion)
- Selling losses in TFSA (user may not realize losses are wasted there)
