# FA -- Financial Assistant

Personal AI investment assistant for US + Canadian equities. Advisory only -- never places trades.

## Operating principles

- **Zero API cost**: Claude Code subscription + free data (Yahoo Finance, SEC EDGAR, Polymarket, Web)
- **User-driven, on-demand**: no daily scans, no proactive nudges. User invokes commands when needed.
- **Multi-account tax-aware**: never hardcode accounts -- always read `portfolio/holdings.json` for current state

## Position-size philosophy

FA is an individual active-investor tool, not a mutual fund under ICA-1940 (`75-5-10` rule). Concentration guardrails anchor to active-manager references, not regulatory minimums:

- **Passive-neutral**: SPY top holding ~7%, SPY Tech sector ~32%. **Pull live numbers via `tools/benchmark.py`** -- `get_stock_info('SPY')` does NOT return sector weights for ETFs (only `category: "Large Blend"`). Use `python tools/benchmark.py spy-sectors` / `spy-top-holdings` via the MCP venv python.
- **Active-concentrated reference**: Buffett AAPL 18-22% / top 4 = 56%; Ackman top 5 = vast majority, single positions ≥20%
- **Principle**: concentration itself isn't risky; *unresearched* concentration is. Gates check research depth + downside plan, not raw position %.

Commands implement this as tiered warnings (pass → flag → DRAFT → HIGH-RISK), not hard refusals. See `/allocate-cash` for concrete tiers.

## Account routing rules (Canadian tax)

Accounts are defined dynamically in `holdings.json`. `account_type` field drives tax treatment:

| `account_type` | Canadian tax rule |
|---|---|
| `taxable` | Capital gains 50% inclusion; CDN dividends get DTC; US dividends creditable as FTC |
| `tfsa` | Growth + dividends **tax-free**. BUT US dividends still hit 15% US withholding (not recoverable -- TFSA trap) |
| `rrsp` | Growth deferred. US dividends exempt from 15% withholding (US-CA tax treaty). If no RRSP account exists in holdings.json, don't assume one. |

**Routing heuristics** (apply account-type-agnostic -- enumerate real accounts from holdings.json):

- US high-yield div (>2%) → taxable USD account (FTC recovers withholding). **Avoid TFSA** -- 15% permanent loss.
- CDN dividend stock → taxable CAD (DTC) or TFSA (tax-free, no DTC)
- Zero-div growth → TFSA first (amplify tax-free gains)
- USD asset → USD account (save FX); CAD asset → CAD account
- **Sell priority**: TFSA (tax-free) > taxable with losses (harvest) > taxable with gains

**TFSA gotchas**:
- Yearly contribution room (~$7k CAD/year 2026). Over-contribution = 1%/month CRA penalty.
- Selling does NOT restore room mid-year -- room returns Jan 1 next year. Same-year sell-and-rebuy = over-contribution trap.
- Superficial loss rule (ITA 54): 30 days before + 30 days after sale. Applies to ALL affiliated accounts (TFSA/RRSP/spouse). Loss gets denied + added to ACB of replacement.
- **ACB is pooled across all accounts** for identical property. Same ticker in 2 accounts = 1 ACB pool.

## ⚠️ Known data quirks

### yfinance `dividendYield` -- always cross-check
Two failure modes: (A) returns percentage-number (2.0 instead of 0.02), (B) raw vs computed drift (BCE.TO returned 5.35 vs computed 7.07).

**Always use this pattern** (agents must apply):

```python
def safe_yield(info):
    raw = info.get('dividendYield', 0) or 0
    rate = info.get('trailingAnnualDividendRate', 0) or 0
    price = info.get('currentPrice') or info.get('regularMarketPrice')
    if not price or not rate:
        return raw / 100 if raw > 15 else raw
    computed = rate / price * 100
    if raw > 15:
        return computed
    if abs(raw - computed) / max(computed, 0.1) > 0.20:
        return computed
    return raw
```

**Dividend signals** (independent of data bug):
- Yield > 6% → likely dividend cut risk. Flag. (BCE.TO is current example.)
- Yield < 0.1% on a div-paying company → possibly split-unadjusted data or suspended

### Stock split detection
Cost basis may be pre-split. Sanity check against 5y price range. Flag if `cost_basis > 2× 5y_high` OR `cost_basis < 0.5× 5y_low`. Recent splits: NVDA 10:1 (2024-06), AVGO 10:1 (2024-07), TSLA 3:1 (2022), GOOGL 20:1 (2022).

### Rate index data gaps (^TNX / ^IRX / ^FVX)
Yahoo's CBOE rate indices can stop updating for a week+ while equity/FX/commodity tickers stay current. The call succeeds with no error: the series just ends at a stale date. Observed 2026-07-03: ^TNX and ^IRX latest row was 2026-06-26, while ^VIX / CAD=X / CL=F were current through 07-02/03.

**Rule for agents** (macro-analyst in `/market-pulse` and `/weekly-brief` especially):
- Always check the last `Date` in the returned series. If it lags the most recent US trading day by more than 2 trading days, treat the series as stale.
- When stale, pull the current yield via `WebSearch` (e.g. "10-year treasury yield today") and use that as the live number; cite the MCP value only with its as-of date attached.
- Never present a stale close as the current level in the yield-curve table -- a week-old 10Y next to same-day VIX/FX silently misdates the whole regime read.

### Other yfinance quirks to null-safe

- **`forwardPE`** often null for small-caps, Canadian dual-listed, or recently-IPO'd names. **Fallback**: trailing PE × (1 + expected growth). If no analyst growth estimate either, skip the forward metric rather than reporting missing as "0" or "cheap".
- **`beta`** is a 5-year regression. For recent IPOs (< 3y public) or post-merger entities (e.g. AVGO after VMW), beta is stale or regressed-to-1. Cross-check with 1-year realized vol if it matters.
- **`recommendationKey`** / `recommendationMean` can be None (thinly-covered names). Burry's "analyst consensus" gate must `if recommendation_key is None: skip this gate` -- not default to "strong buy".
- **`marketCap` on ADRs** sometimes reflects only the ADR-listed shares, not the parent's global float. Cross-check with `sharesOutstanding × regularMarketPrice` if mcap-ranked sizing matters.
- **`country`** is HQ country, not revenue-exposure country. AAPL `country=US` but > 50% revenue foreign. Don't use this field alone for geographic exposure -- use segment data from fundamentals.
- **`sector`** / **`industry`** can be null for some Canadian small-caps, ETFs, and trusts (e.g. some `.TO` tickers return `null`). Fallback to `quoteType` + manual ETF sector classification, or bucket as `"Unknown"` in sector breakdown rather than silently dropping the position.
- **Class-share ticker format**: yfinance uses `-` (dash), not `.` (dot), for class-share securities. `BRK.B` returns `price=None`; the correct form is `BRK-B`. Same for `BF-B` (Brown-Forman Class B), `RDS-B` (when it existed), etc. Brokers and users write `.B` naturally, so every command that accepts a ticker from `$ARGUMENTS` should **normalize `.B`/`.A` suffix to `-B`/`-A`** before calling yfinance. `BRK.B`, `BRK/B`, `BRK-B` should all map to `BRK-B`. When echoing back to user, preserve their original spelling.
- **`currentPrice`** can lag after-hours moves. For intraday precision use `regularMarketPrice` + `postMarketPrice` combined.

**General pattern**: every agent that pulls `get_stock_info` should use a `safe_get(info, key, fallback)` wrapper and skip gates cleanly when data is missing -- don't let a null silently become a "pass" or "fail" signal.

## Tag vocabulary (holdings.json `tags[]`)

Tags drive `/stress-test` shock attribution and `/allocate-cash` factor portrait. They're exact-match strings, so typos silently drop shocks. **Stick to these canonical lowercase kebab-case values**:

| Category | Canonical tags |
|---|---|
| AI theme | `ai`, `semi`, `hyperscaler`, `ai-infra` |
| Sector-style | `software`, `ads`, `consumer-tech`, `bank`, `insurance`, `telecom`, `energy`, `pipeline`, `utility`, `reit`, `healthcare`, `biotech`, `pharma`, `materials` |
| Factor | `growth`, `value`, `dividend`, `defensive`, `momentum` |
| Wrapper | `us-exposure-etf`, `cad-exposure-etf`, `global-etf`, `bond-etf` |
| Size | `mega-cap`, `small-cap` (optional -- derivable from marketCap) |

Rules:
- **Lowercase, kebab-case** -- never `AI`, `Ai`, `artificial_intelligence`.
- Multi-tag is encouraged: `["ai", "semi", "hyperscaler-supplier"]` on NVDA is more useful than any one.
- `/stress-test` should emit a WARN if it sees a tag in `holdings.json` not on this list (not block -- user may have a deliberate custom tag, but flag for typo review).

## File layout

```
FA/
├── .mcp.json                       Yahoo Finance MCP (edit the yahoo-finance path)
├── CLAUDE.md                       This file
├── .claude/{agents,commands}/      Sub-agents + slash commands
├── portfolio/
│   ├── holdings.sample.json        Fictional sample portfolio (copy to holdings.json)
│   └── youtubers.yaml              Tracked YouTube finance channels
├── tools/                          polymarket.py, benchmark.py, notion_push.py, transcribe.py, ...
├── memory/{short,mid,long}_term/   Markdown journal / research artifacts (gitignored)
├── bootstrap/                      setup.ps1 / setup.sh / check.py + README
└── notion_config.example.json      Copy to notion_config.json + add your token (optional)
```

**Setup**: copy `portfolio/holdings.sample.json` to `portfolio/holdings.json` and fill in your own accounts. The Yahoo Finance MCP server is not vendored in this repo: clone it separately and set its path in `.mcp.json` (see `bootstrap/README.md`).

## Commands (user-invoked, on-demand)

| Command | Purpose |
|---|---|
| `/weekly-brief` | 全组合多智能体周报（7 agents × 持仓 + portfolio-manager 终审）→ 自动推送 Notion |
| `/market-pulse` | Market regime + rates + sectors + upcoming catalysts |
| `/deep-dive TICKER` | Fact gathering: fundamentals + SEC + news + macro + competitors |
| `/research TICKER` | 5-persona debate + synthesis with tax-aware action |
| `/allocate-cash` | Deploy cash: portfolio gaps + tiered deployment plan |
| `/rebalance` | Drift correction: no new cash, tax-ordered trim+add |
| `/stress-test` | 6 macro scenarios, historical-anchored loss estimates |
| `/earnings-week [N]` | Next N-day earnings + dividend calendar; cluster-risk flag |
| `/tax-harvest` | CRA-compliant loss harvest with 60-day superficial-loss check |
| `/trade <desc>` | Record a completed trade → update holdings.json + trades log |
| `/reconcile` | Corporate-action sync: scans dividends / splits / DRIP since `last_updated`, diff-proposes holdings.json updates |
| `/journal <note>` | Decision log ("why I bought/passed"); `review` mode shows history; `archive` mode rotates old memory artifacts |
| `/youtube-pulse` | Summarizes tracked YouTube finance channels into short-term signals for current holdings |

## Sub-agents (dispatched by commands)

Personas (opinion-heavy): `buffett`, `munger`, `burry`, `bull`, `bear`
Analysts (fact-heavy): `news-analyst`, `fundamentals-analyst`, `macro-analyst`, `sec-filings-analyst`, `technical-analyst`, `risk-analyst`
Synthesis: `portfolio-manager` (called last -- synthesizes all agent outputs into 5-level rating + account routing)

## High-risk gates (stop + confirm with user)

Any of these triggers a draft-and-confirm output instead of silent recommendation:
- Single trade (buy or sell) > 5% of portfolio -- trade-size gate
- Single-ticker holding would exceed 12% after trade -- concentration gate (HIGH-RISK at >20%; see `/allocate-cash` tiered rule)
- Industry concentration > SPY sector weight + 20pp -- sector gate (HIGH-RISK at >+30pp)
- Rebalance moving > 20% of portfolio
- Cash deployment > 70% of reserves
- Portfolio Beta delta > 0.3
- Trade that realizes > 5% of portfolio as taxable gain
- Any TFSA contribution that risks over-contribution

## Non-high-risk (proceed without confirmation)

Run commands, update memory, edit prompts, run `uv sync`.
