---
description: Lightweight decision journal -- capture the "why" behind a decision (bought, sold, passed, waited) so future /research and /allocate-cash can read prior reasoning. Fights hindsight bias. Two modes -- write (default) or review (show recent entries).
---

# /journal -- Decision Journal

Persistent record of **investment decisions + the reasoning at the time**. Fights hindsight bias and gives `/research` + `/allocate-cash` historical context in future sessions.

## Usage

**Write mode** (default) -- capture a decision in `$ARGUMENTS`:

```
/journal 今天没买 BRK.B，觉得 $468 是 52w 低但 Buffett 最近卖 AAPL 给信号谨慎。等 Q1 filing 看持仓变化
/journal passed on NVDA after /research said "conditional no" -- waiting for Q1 FY27 print May 20
/journal trimmed MSFT broker-a-taxable 10 shares at $420, locked gain; keeps position under 15% portfolio cap
```

**Review mode** -- `review [window]` to read recent entries:

```
/journal review                      # last 30 days
/journal review 90                   # last 90 days
/journal review NVDA                 # filter by ticker
/journal review thesis-change        # filter by tag
```

**Archive mode** -- `archive` compresses stale `memory/mid_term/*.md` into monthly summaries:

```
/journal archive                     # default: files > 180 days old
/journal archive 90                  # files > 90 days old
```

What it does:
1. `Glob memory/mid_term/*.md`, filter by date encoded in filename (e.g. `2025-10-*`).
2. Group by year-month.
3. For each month: read all files, extract key facts (decisions made, conclusions, tickers, outcomes), write one condensed summary to `memory/archive/{YYYY-MM}-summary.md`.
4. Move originals to `memory/archive/raw/{YYYY-MM}/`. Never delete.
5. Future command lookups read `memory/archive/*-summary.md` first (cheap), fall through to raw on demand.

Run monthly-ish. Without it, `memory/mid_term/` grows unbounded and every command's Glob slows down.

## Phase 1 -- Parse (write mode)

Extract from `$ARGUMENTS`:
- **Decision type**: `bought` / `sold` / `trimmed` / `added` / `passed` / `waited` / `watched` / `thesis-change`
- **Ticker(s)** referenced
- **Key reasoning** (1-3 sentences)
- **Trigger condition** if they waited (e.g., "if NVDA < $170")
- **Expected check-back date** if they're waiting

If critical fields missing, **ask one concise question**, not a form dump.

## Phase 2 -- Context capture

Pull current state at time of decision:
- For each ticker mentioned: current price, 52w position, next earnings date
- Broad market: SPY / VIX / 10Y current level
- Fetch via `mcp__yahoo-finance__get_stock_info` -- snapshot only, don't over-research

Purpose: 6 months later, when reviewing, you see what the state of the world was at decision time.

## Phase 3 -- Append entry

Write to `memory/long_term/journal.md` (append, never overwrite). Entry format:

```markdown
## {YYYY-MM-DD HH:MM} -- {decision_type}: {one-line summary}
- **Tickers**: {list}
- **Action**: {bought / sold / passed / waited}
- **Reasoning**: {user's stated reasoning, cleaned up}
- **Trigger / check-back**: {if applicable}
- **Market context at decision**:
  - TICKER price: $X (52w pos Y%, next earnings {date})
  - SPY: $X | VIX: Y | US 10Y: Z%
- **Tags**: {auto-extracted: thesis-change, tax, harvest, cluster-risk, etc.}
- **Related artifacts**: {link to recent /research or /deep-dive files in memory/mid_term/ if topic matches}
```

Confirm saved with short response -- don't echo the whole entry back.

## Phase 4 -- Review mode

If `$ARGUMENTS` starts with `review`:

1. `Read` `memory/long_term/journal.md`
2. Filter by window (default 30 days) OR ticker OR tag
3. Return entries chronologically newest-first
4. Add **at the top** a "patterns observed" section if 3+ entries match a pattern:
   - "You've passed on AAPL 4 times citing valuation -- may be anchoring"
   - "You've harvested in BCE.TO, PYPL, INTC -- pattern of holding too long into thesis breaks"
   - "3 decisions in last month were driven by 'Fed pause' narrative -- watch for single-story overfit"

Pattern detection is optional -- don't invent if < 3 signal.

## Phase 5 -- Archive mode

If `$ARGUMENTS` starts with `archive [N]`:

1. Parse threshold: `N` days (default 180).
2. `Glob memory/mid_term/*.md` → filter by filename date > N days ago.
3. Group by `YYYY-MM`.
4. For each month-group:
   - `Read` all files.
   - Write condensed `memory/archive/{YYYY-MM}-summary.md` with: decision log bullets, all ticker verdicts, unique theses, outcomes if known. ≤ 500 words per month.
   - Use `Bash mv` (or equivalent) to relocate originals to `memory/archive/raw/{YYYY-MM}/`.
5. Ensure target directories exist first (`Bash mkdir -p`).
6. Report: "Archived {N} files from {K} months. Freed up mid_term Glob surface."

Never DELETE content -- archive is a compression + move, not a destruction.

Cross-command compatibility: the `/research`, `/allocate-cash`, `/rebalance` memory-lookup steps should prefer `memory/archive/*-summary.md` for anything > 90 days old, to keep context small.

## Integration with other commands

Other commands should **check** `memory/long_term/journal.md` when relevant:

- `/research TICKER` -- if there's a journal entry for this ticker in last 90 days, prepend to context
- `/allocate-cash` -- scan last 30 days of journal for "passed" or "waiting" entries; if any triggered by now (e.g., "wait for NVDA < $170" and NVDA is now $168), **surface as candidate**
- `/rebalance` -- if user journaled a thesis change, that position might be priority to trim

I'll add the journal-lookup step to those commands as a future pass, but the journal itself works independently.

## Rules

- **Keep entries short** -- 1-3 sentences on reasoning. No essays. This is a log, not a blog.
- **Don't moralize** -- capture what the user thought, not what they "should have" thought. Future-you judging is the whole point; present-you shouldn't preempt.
- **Append-only** -- never modify prior entries. If a thesis changes, write a NEW entry tagged `thesis-change` referencing the prior one.
- **Advisory** -- this is a user tool, not an agent tool. If user says "/journal" with no content and no `review`, prompt for what they want to record.
- **Privacy** -- journal is local. Never WebSearch or echo journal content outside of the user's own session.
