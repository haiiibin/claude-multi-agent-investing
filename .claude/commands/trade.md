---
description: Sync a completed trade -- parse natural-language description, update holdings.json with correct cost basis averaging, log to memory for audit trail. Usage /trade <description>
---

# /trade -- Sync Completed Trade

Record a trade the user executed on their broker platform. Updates `holdings.json` and logs to `memory/long_term/trades.md` for audit trail.

## Input

Natural language from `$ARGUMENTS`, examples:
- `昨天在 broker-a-taxable 买了 20 股 NVDA @ $195`
- `sold 50 AAPL from broker-a-taxable at $182 today`
- `TFSA 加仓 SHOP.TO 30 股 @CAD$175, 成本摊到均价`
- `trim half of MSFT in broker-a-taxable at $420`

## Steps

1. **Parse the trade.** Extract:
   - Action: buy / sell / add / trim / close
   - Ticker -- **normalize class-share suffix**: `BRK.B` / `BRK/B` → `BRK-B`, `BF.B` → `BF-B` (yfinance quirk per CLAUDE.md). Store the yfinance-valid form in holdings.json.
   - Shares
   - Price
   - Account (match to holdings.json account_id -- or ask if ambiguous)
   - Date (default today if not specified)
   - Currency (infer from account's base_currency)

2. **Ask once if critical info missing.** Don't over-ask. If user wrote "bought NVDA in broker-a-taxable" without shares/price, ask one question: "How many shares and at what price?"

3. **Validate.**
   - If selling, does the account actually hold this ticker + enough shares?
   - If TFSA buy of high-yield US stock → **flag the withholding trap** before proceeding. **Sanity-check yfinance `dividendYield`** per CLAUDE.md quirks: divide by 100 if > 15%, or recompute from `trailingAnnualDividendRate / currentPrice`. Don't flag trap on a false-high yield number.
   - If position size after trade crosses a concentration tier (see CLAUDE.md: ≤7% neutral, 7-12% flag, 12-20% DRAFT, >20% HIGH-RISK) → note the tier in confirmation. Trades don't block -- /trade records what already happened.
   - If buying with insufficient cash in the account → flag and ask whether to deduct from cash or assume deposit arrived

4. **Update `holdings.json`.**

   **IMPORTANT -- Canadian ACB is pooled across ALL accounts** for the same identical property. CRA treats identical property held in multiple accounts as ONE pool for cost basis purposes. This means:

   - **Buy / add**: find existing holding IN THIS ACCOUNT; recompute its per-account cost basis using weighted average:
     `new_cost_in_this_account = (old_shares × old_cost + new_shares × new_price) / (old_shares + new_shares)`
     **Also** note if same ticker exists in other accounts -- mention the new **cross-account pooled ACB** in confirmation (for CRA reporting).
   - **Sell / trim**: reduce `shares` in the selling account. **For realized gain/loss reporting**, compute using the **cross-account pooled ACB**, NOT the per-account cost_basis:
     ```
     pooled_acb_per_share = Σ (shares_in_account_i × cost_basis_i) / Σ shares_in_account_i
     realized_gain_per_share = sale_price - pooled_acb_per_share
     realized_gain_total = realized_gain_per_share × shares_sold
     ```
     Keep `cost_basis` field in the selling account unchanged (CRA bookkeeping is on pooled basis, not per-account). State both numbers in the confirmation so user can reconcile with broker slips. Broker-reported ACB may differ from CRA-required pooled ACB -- user needs the pooled figure for T5008 / Schedule 3.
   - **Close**: set shares to 0 or remove the holding entry (ask user preference once, then remember)
   - **New position**: add new holding entry under correct account
   - **If the ticker exists in `watchlist[]`**: remove that entry automatically (it's been converted to a real holding). Mention the cleanup in the confirmation.
   - **Deduct cash** from the executing account: `cash[currency] -= shares × price + fees` (ask about fees if not specified; skip if unknown -- user can correct later)
   - Update `last_updated` field
   - Preserve JSON formatting

5. **Log to `memory/long_term/trades.md`.** Append entry:
   ```markdown
   ## 2026-04-20 -- {action} {shares} {ticker} @{price} in {account_id}
   - Thesis/reason: (ask user if substantial trade > 3% of portfolio, else skip)
   - Cost basis after: {average}
   - Realized P&L (if sell): {amount, tax-relevant flag}
   - Position size after: {% of portfolio}
   ```

6. **Produce short confirmation.** Don't be verbose -- just confirm what changed:

```markdown
✅ Recorded: Bought 20 NVDA @ $195 in broker-a-taxable

**New position:**
- Shares: 20
- Cost basis: $195.00
- Market value: ~$4,000 (current: $199.88)
- Account: broker-a-taxable (taxable USD)
- Portfolio weight: ~2.1%

**Flags:**
- None ✓ (if clean)
- Or: Position now X% -- above concentration threshold
- Or: TFSA with high-yield US stock -- withholding trap

Logged to: `memory/long_term/trades.md`
```

## Rules

- **Do not execute any actual trade.** User already traded on broker. This command only **records** it.
- **Never modify holdings.json silently.** Always show what changed.
- **Cost basis averaging must be weighted by shares** -- do not use simple arithmetic mean
- **Preserve JSON structure** -- keep account_type, currency, tags, thesis fields intact
- **Ask at most one clarification** -- user wants fast sync, not a questionnaire
- If the trade materially changes portfolio character (> 5% position change, new sector entry, Beta shift > 0.3 -- matches CLAUDE.md high-risk gate), mention it in the confirmation **but don't block** -- user already acted

## High-risk gate

If the trade description implies the user wants me to **simulate** or **recommend** instead of record (e.g., "should I sell NVDA?"), **do not update holdings.json**. Redirect to `/research NVDA` or answer conversationally. This command is for already-executed trades only.
