---
description: Corporate-action reconciliation. Compare holdings.json vs yfinance action history (dividends, splits, spinoffs). Surface drift since last_updated so user can align with broker statement. Distinct from /trade which records user-initiated transactions.
---

# /reconcile -- Corporate Action Sync

`/trade` records what **you** did. `/reconcile` catches what **the market** did to your holdings while you weren't looking -- dividends, DRIP, splits, spinoffs. Without this, `holdings.json` silently drifts from broker reality and every downstream analysis becomes wrong.

Advisory only. User confirms against broker statement before the file is touched.

## When to run

- Monthly (dividends arrive monthly on Canadian banks, quarterly on US mega-cap)
- Before any `/allocate-cash` or `/rebalance` if last run was > 30 days ago
- After any announced split / spinoff / merger for a ticker you hold

## Phase 1 -- Scope

Read `holdings.json`. For each account, note `last_updated` timestamp. Define the reconciliation window as `[last_updated, today]` per account.

Enumerate every unique ticker across all accounts.

## Phase 2 -- Fetch corporate actions

**The MCP server does NOT expose `Ticker.actions` directly** (verified: 9 MCP tools, all `get_*_info` / `get_historical_*` variants). Use a Bash call into the MCP's own venv python:

```bash
# run via a Python env with yfinance available (e.g. the Yahoo Finance MCP venv)
python -c "
import yfinance as yf, json, sys, pandas as pd
ticker, since = sys.argv[1], sys.argv[2]  # since = YYYY-MM-DD
t = yf.Ticker(ticker)
df = t.actions  # DataFrame indexed by Date with Dividends, Stock Splits
df = df[df.index >= since]
out = [{'date': str(idx.date()), 'dividend': float(r.get('Dividends',0)), 'split': float(r.get('Stock Splits',0))}
       for idx, r in df.iterrows() if r.get('Dividends') or r.get('Stock Splits')]
print(json.dumps(out))
" {TICKER} {last_updated}
```

Per ticker event:
- Non-zero `Stock Splits` → note ratio (e.g. 10.0 = 10:1 forward split).
- Non-zero `Dividends` → per-share amount. Pull the ex-date price separately via `mcp__yahoo-finance__get_historical_stock_prices` for DRIP share-count math, and historical FX from `CAD=X` if a USD dividend lands in a CAD base-currency account (CRA rule).

Also `WebSearch` for spinoff/merger announcements per ticker -- yfinance doesn't always surface these. Especially if user holds names in M&A news.

## Phase 3 -- Compute expected delta per position

For each `(ticker, account)` holding:

**Dividends**:
- Dividend per share × shares held = expected cash in
- Account for withholding per account_type:
  - `taxable` USD account, US stock → net = gross × 0.85 (15% withholding, FTC-creditable)
  - `tfsa` USD account, US stock → net = gross × 0.85 (15% withholding, NOT recoverable -- TFSA trap)
  - `taxable` CAD account, CAD stock → net = gross (no withholding)
  - `rrsp` USD account, US stock → net = gross (US-CA treaty exemption)
- Flag DRIP positions: if `drip_enabled: true` on the holding → expected share add = floor(gross_div / ex-date_price)

**Splits**:
- New shares = old shares × ratio (e.g. 10:1 → ×10)
- Per-share cost basis must divide by same ratio
- Total cost basis unchanged

**Spinoffs** (manual detection -- ask user):
- CRA rule: original ACB is allocated between parent + spinoff by FMV ratio on distribution date
- User must provide the FMV ratio from their broker -- don't guess

## Phase 4 -- Output

```markdown
# 🔄 Reconcile -- {YYYY-MM-DD}

## Window
- Last updated per account: {table}
- Scope: {N} tickers × {M} accounts

## Expected corporate-action deltas

### 💵 Dividends (in window)
| Ticker | Account | Ex-date | $/share | Shares | Expected cash | DRIP? | Status |
|---|---|---|---|---|---|---|---|
| ENB.TO | broker-b-taxable | 2026-02-15 | $0.94 CAD | 100 | +$94 | no | ❓ Confirm in statement |
| AAPL | broker-a-taxable | 2026-02-10 | $0.24 USD | 40 | +$9.60 (gross), +$8.16 (net after 15% WHT) | no | ❓ |
| VFV.TO | broker-b-tfsa | 2026-03-21 | $0.38 CAD | 50 | +$19 → DRIP buys ~0.14 sh @$132 | **YES** | ❓ |

### 🔀 Splits (in window)
| Ticker | Date | Ratio | Old shares | New shares | Old cost | New cost |
|---|---|---|---|---|---|---|
| (none this window) | | | | | | |

### 🌱 Spinoffs / M&A (flagged from news search)
| Parent | Event | Date | Action required |
|---|---|---|---|
| (none) | | | |

## Suggested holdings.json updates

**If user confirms all above matches broker statement**, apply:

1. `broker-a-taxable.cash.USD += $8.16` (AAPL dividend net)
2. `broker-b-tfsa.holdings[VFV.TO].shares += 0.14` and `recompute cost_basis via weighted average` (DRIP)
3. (for splits: update shares + per-share cost_basis; leave total cost basis unchanged)
4. Set all touched accounts `last_updated = {today}`

Show exact JSON diff before writing. **Never silent-write**.

## Reconciliation unknowns

If the ticker is missing from yfinance response, or ex-date is ambiguous: list under "Needs manual entry" -- do NOT make up numbers. User enters via `/trade` if broker shows action.

## Status legend

- ✅ Matches broker statement user pasted in
- ❓ Needs user to confirm against broker
- ⚠️ Discrepancy flagged (cash in holdings.json says $X but expected $Y)
- 🚫 Missing data (user input needed)

Save log to `memory/long_term/reconcile-{YYYY-MM-DD}.md` for CRA audit trail.
```

## Rules

- **Never write `holdings.json` without explicit user confirmation** -- reconcile is a diff-proposer, not a silent sync.
- **DRIP is the hidden trap** -- if a user has `drip_enabled` but doesn't notice the share growth, their cost basis drifts. Flag DRIP positions loudly.
- **FX at the time of distribution matters** for CAD reporting of USD dividends (CRA rule). Use historical USD/CAD on ex-date, not spot. `yfinance` gives you the price -- you'll need historical FX too.
- **Spinoffs require user input** -- don't guess FMV allocation. Ask.
- **Stock splits never change cost basis total** -- only per-share. A failure to adjust means future P&L is wrong.
- **Superficial-loss interaction**: if a DRIP purchase happens within 30 days of a sale at loss in another affiliated account → that's a superficial loss trigger. Flag it.

## Output discipline

Short confirmation after user approves:
```
✅ Applied 3 dividends (+$121.76 across accounts), 1 DRIP share add (VFV.TO +0.14). No splits. 0 discrepancies.
Logged: memory/long_term/reconcile-2026-04-24.md
```
