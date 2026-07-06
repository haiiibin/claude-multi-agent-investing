# Claude Multi-Agent Investing

A Claude Code framework where 12 agents (5 opinionated personas -- Buffett, Munger, Burry,
bull, bear; 6 fact-gathering analysts; 1 portfolio-manager synthesizer) debate your portfolio
through 13 slash commands. It is advisory only, tax-aware for Canadian accounts (taxable /
TFSA / RRSP), and runs on nothing but a Claude Code subscription plus free data sources
(Yahoo Finance, SEC EDGAR, Polymarket, web search) -- zero extra API cost.

Internally the system calls itself "FA" (Financial Assistant) -- that name shows up in
`CLAUDE.md` and the bootstrap scripts. All paths below are relative to this repo's root.

## Agents

| Agent | Role |
|---|---|
| `buffett` | Buffett persona: bullish / bearish / neutral call via moat, intrinsic value, margin of safety |
| `munger` | Munger persona: inverts the question, runs a red-flag checklist, defaults skeptical when Wall Street consensus is one-sided |
| `burry` | Burry persona: deep-value contrarian hunting hard catalysts (FCF yield, EV/EBIT, insider buying, buybacks) |
| `bull` | Builds the strongest case FOR a ticker (growth, moat, positive indicators) |
| `bear` | Builds the strongest case AGAINST a ticker (risk, weakness, negative indicators) |
| `news-analyst` | Pulls recent news, scores sentiment, flags high-importance events; hardened against prompt injection from article content |
| `fundamentals-analyst` | Reads 4+ years of income / balance / cashflow statements, computes trends, flags quality-of-earnings issues |
| `macro-analyst` | Snapshots rates / FX / commodities / indices / VIX, maps regime impact to a specific ticker or sector |
| `sec-filings-analyst` | Pulls 10-K / 10-Q / 8-K from SEC EDGAR, extracts Risk Factors and material events (US-listed only) |
| `technical-analyst` | Price action: MA20/50/200 trend stack, RSI, MACD, Bollinger Bands, ATR, support/resistance |
| `risk-analyst` | Scores 5 risk dimensions (market/volatility, concentration, FX, tax/account, fundamental), 1-5 each |
| `portfolio-manager` | Final synthesis: reads every other agent's output and issues a 5-level rating with account routing and tax-aware action |

## Commands

| Command | Purpose |
|---|---|
| `/weekly-brief` | Full-portfolio multi-agent report: all analysts + personas per holding, cross-checked against YouTube signals, portfolio-manager final call, optional Notion push |
| `/market-pulse` | Market-wide macro scan: indices, rates, FX, commodities, sector rotation, upcoming catalysts |
| `/deep-dive TICKER` | Deep intelligence gathering: fundamentals + SEC filings + news + macro + competitors |
| `/research TICKER` | 5-persona debate plus a tax-aware "already own" analysis across taxable / TFSA / registered accounts |
| `/allocate-cash` | Portfolio-level cash deployment plan with tiered, tax-aware account routing |
| `/rebalance` | Zero-new-cash drift correction: tax-ordered trim + add |
| `/stress-test` | 6 canonical, historically-anchored macro shocks; per-scenario loss estimate and worst positions |
| `/earnings-week [N]` | Upcoming earnings + dividend calendar for holdings; flags same-day event clusters |
| `/tax-harvest` | Canadian tax-loss harvest planner; enforces the ITA 54 60-day superficial-loss rule |
| `/trade <desc>` | Records a completed trade: updates `holdings.json` cost basis and logs it for an audit trail |
| `/reconcile` | Corporate-action sync: diffs `holdings.json` against dividend / split / spinoff history since `last_updated` |
| `/journal <note>` | Decision journal (write / review / archive modes) so future commands can read prior reasoning |
| `/youtube-pulse` | Summarizes tracked YouTube finance channels into short-term signals for current holdings |

## How /weekly-brief works

Step 0 loads context from `portfolio/holdings.json` (accounts, holdings, cash) and scans
`memory/short_term/` for videos already transcribed. Step 1 fires everything else in parallel:
YouTube RSS feeds for tracked channels, a `macro-analyst` regime snapshot, a `news-analyst`
sentiment pass, a `fundamentals-analyst` metrics pull, and an earnings-calendar search. Step 2 transcribes any new videos sequentially (CPU-bound, one at a time). Step 3
dispatches 7 agents per holding in parallel and in the background: the 5 personas plus
`technical-analyst` and `risk-analyst`; watchlist tickers get a lighter pass. Step 4 extracts
directional signals from the transcripts. Step 5 hands every agent's output for a given
ticker to `portfolio-manager`, which is called last and serially per holding, and which issues
the 5-level rating (Buy/Overweight/Hold/Underweight/Sell), the account routing, and any
high-risk gate flags. Step 6 always saves the brief to `memory/short_term/`, and pushes it to
Notion only if `notion_config.json` exists.

## Quick start

1. Clone this repo and open it in Claude Code.
2. Install the Yahoo Finance MCP server separately (it is not vendored here): clone
   `https://github.com/Alex2Yang97/yahoo-finance-mcp`, run `uv sync` inside it, then edit
   `.mcp.json` in this repo to replace `/ABSOLUTE/PATH/TO/yahoo-finance-mcp` with that path.
   Some tools (`tools/benchmark.py`, the inline scripts in `/reconcile`) need to run in a
   Python environment that has `yfinance` installed, such as that same MCP server's own venv,
   since it usually is not the interpreter running Claude Code itself.
3. Seed your portfolio: `cp portfolio/holdings.sample.json portfolio/holdings.json`, then
   replace the sample accounts/holdings with your own (`bootstrap/setup.ps1` / `setup.sh`
   does this copy for you automatically on first run).
4. Optional -- Notion push: `cp notion_config.example.json notion_config.json` and fill in
   your own Notion integration token and dashboard page id. Without this file, `/weekly-brief`
   just skips the Notion step and keeps the local markdown copy.
5. Optional -- YouTube pulse: `/youtube-pulse` and the transcription step of `/weekly-brief`
   need `yt-dlp`, `openai-whisper`, `youtube-transcript-api`, and `ffmpeg` on PATH. Skip this
   if you don't track YouTube channels.
6. Run `python bootstrap/check.py` to validate the setup, then open Claude Code in this folder
   and run `/market-pulse` as a first smoke test.

## Disclaimer

This is advisory software: it never places trades, and every command that touches money
(trade sizing, rebalancing, cash deployment) stops for user confirmation at defined high-risk
thresholds instead of acting silently. Nothing it outputs is financial advice; it is an
educational framework for organizing your own research and decisions. Yahoo Finance data has
known quirks (stale rate indices, null fields, dividend-yield unit bugs) that are documented
and worked around in `CLAUDE.md` -- read that file before trusting any single number blindly.
