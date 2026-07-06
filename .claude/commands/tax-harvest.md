---
description: Canadian tax-loss harvest planner. Scans taxable accounts for losses, enforces ITA 54 (60-day superficial loss window in all affiliated accounts), proposes non-identical replacements, computes tax benefit. TFSA skipped -- losses there don't offset anything.
---

# /tax-harvest -- Canadian Tax-Loss Harvest

Advisory only. Advisory only. Most useful Nov-Dec; works year-round.

## Canadian rules enforced

1. **Superficial loss (ITA 54)**: buy same/identical property within 30 days before OR after sale in ANY affiliated account (TFSA, RRSP, spouse, controlled corp) → loss **denied and added to ACB of replacement**. 60-day window total.
2. **Identical property**: judgment call, not a hardcoded list. Walk the Phase 3 decision tree. Clear-identical examples: cross-listed pairs (BAM ↔ BAM.TO), same-issuer same-index ETFs (VFV.TO ↔ VOO). Grey-zone (likely identical per practitioner consensus even without case law): SPY ↔ IVV ↔ VOO.
3. **T+1 settlement** (since May 2024). Last trade day for 2026 tax year = Dec 30.
4. **ACB pooled across ALL accounts** for identical property.
5. Capital losses offset capital gains only. Carry back 3yr / forward indefinitely.

## Phase 1 -- Audit

Filter `holdings.json` to `account_type: taxable` (skip TFSA + RRSP).

Per holding: unrealized gain/loss (native + CAD), holding period. Apply `safe_yield` check (CLAUDE.md). Flag stale cost basis per split-detection rule.

## Phase 2 -- Candidate identification

For each **loss** position:

1. **Threshold**: ignore losses <$500 CAD (friction not worth it) unless user overrides
2. **60-day window BOTH directions**:
   - **Past 30 days**: check `memory/long_term/trades.md` for buys of this ticker in any account → if found, SKIP (loss already superficial)
   - **Next 30 days**: check `memory/long_term/journal.md` for "waiting for {ticker}" plans, GTC limits, DRIP schedules → require explicit user confirmation "I will NOT buy within 30 days"
   - **DRIP trap**: if ex-div date is within next 30 days AND DRIP enabled, auto-reinvest IS the affiliated buy. Loudly flag.
   - Any hit → loss is denied + added to replacement ACB (user benefits eventually, just not this year)
3. **Cross-account ACB**: if held in other accounts at a gain, pooled ACB partially offsets. State explicitly.
4. **Gain-harvesting companion** (optional): if taxable has large gains, pairing a gain sale with a loss sale is **tax-neutral rebalancing**. Useful for moving winners (sell in taxable → contribute to TFSA next year).

## Phase 3 -- Replacement tickers

Maintain exposure during 30-day cool-off. Replacement must NOT be "identical property".

**CRA has not published a clean test.** Case law and tax-practitioner consensus say "identical" turns on whether the securities confer the *same rights and obligations*. Two funds tracking the same index with the same underlying holdings are almost always judged identical by auditors; two funds tracking different (even similar) indices are almost always OK. When in doubt, be conservative -- the cost of being wrong is loss denial.

Instead of hardcoded rules, walk this decision tree with the user:

```
Candidate replacement: {TICKER2}

Q1: Same issuer / fund family as {TICKER1}?
    └─ YES → Q2
    └─ NO  → Q3

Q2: Tracks the same benchmark index?
    └─ YES → 🚫 Treat as identical. Pick different candidate.
    └─ NO  → Q3

Q3: Cross-listed shares of the same underlying entity? (e.g. BAM.TO vs BAM, SHOP.TO vs SHOP)
    └─ YES → 🚫 Identical by definition. Pick different candidate.
    └─ NO  → Q4

Q4: Same sector/industry exposure, different specific basket?
    └─ YES → ⚠️ Grey zone. Probably safe but ask user to accept residual audit risk.
            (Example: BMO.TO (single stock) → ZEB.TO (ETF holding BMO + 5 other banks). Not identical.
            Example: SPY → VOO. Both S&P 500, different issuer. Widely treated as identical by CRA
            practitioners despite no case law.)
    └─ NO  → ✅ Not identical. Safe replacement.
```

**Default clear cases** (no need to run the tree):
- ✅ Single stock → broader sector ETF (NVDA → SMH, AMD → SMH)
- ✅ Single stock → different single stock (NVDA → AVGO)
- ✅ Bond ETF → different bond ETF with different index or materially different duration/credit
- 🚫 Cross-listed pairs (CNR ↔ CNI, BAM ↔ BAM.TO, SHOP ↔ SHOP.TO)
- 🚫 Same-issuer same-index ETFs (VFV.TO ↔ VOO -- both Vanguard S&P 500)

**Grey-zone examples requiring user judgment**:
- SPY → IVV → VOO (all S&P 500, different issuers): most tax practitioners treat as identical; safest to pick a different index like RSP (equal-weight S&P 500) or SPLV (low-vol)
- QQQ → QQQM (both track Nasdaq-100, same issuer): identical
- VTI → ITOT (total market, different issuers): grey
- Hard tech ETF → broader growth ETF: not identical if the baskets differ materially

Use `WebSearch` for candidate ideas when thinking through replacements. Show the decision tree output to user for their confirmation before finalizing.

## Phase 4 -- Output

```markdown
# 🪓 Tax-Loss Harvest -- {YYYY-MM-DD}

## Summary
- Taxable accounts scanned: {list}
- Loss positions: N | Total CAD loss: $X
- Above $500 threshold: M

## Candidates

### {TICKER} in {account_id}
- {shares} sh, cost $X, current $Y, **loss $Z CAD ({pct}%)**
- 60-day window: ✅ CLEAR / ⚠️ {reason -- RECENT BUY / PENDING ORDER / DRIP}
- Cross-account ACB: {only here / also in {other} at gain $W}
- **Action**: Sell {N} shares at market (or limit $X)
- **Replacement**: {REPLACEMENT} ({reason, not-identical})
- **Earliest re-entry**: {sale_date + 31 days}

## Gain-harvesting companions (optional, tax-neutral)
| Position | Unrealized gain | Tax alone | Tax paired with loss |
|---|---|---|---|
| {ticker} | +$X | ~$Y @ 25% | $0 (offset) |

## Tax savings estimate
Marginal rate X%, 50% inclusion:
- Realized loss: $Z | Taxable loss: $Z/2 | Tax saved this year: $S (against gains) OR carried forward

## NOT doing
- Buy back {TICKER} before {date} in ANY account (superficial loss)
- Harvest if thesis still intact -- tax is tail, investing is dog

## Timing
- Tax year 2026: sell by Dec 30 (T+1 to 12/31)
- Defer to 2027: sell on/after Jan 2

Save to `memory/long_term/{YYYY}-tax-harvest-plan.md` (CRA audit trail).
```

## Rules

- **No harvest on thesis-intact positions.** Don't harvest a temporary drawdown in a good business.
- **60-day window in ALL affiliated accounts** (TFSA, RRSP, spouse if mentioned). Always check both directions.
- **>10% portfolio turnover** → flag as material restructuring, not just tax move.
- **USD stocks**: CRA requires CAD gains at **historical FX at purchase**, not current spot. State this caveat -- planning number will differ from actual reported loss.
- **No candidates**: just say so. Don't manufacture reasons.
