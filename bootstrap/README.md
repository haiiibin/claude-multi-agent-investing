# FA Bootstrap

One-click setup for a new device. Checks prerequisites, auto-installs what's safe, seeds your portfolio file, validates the whole stack.

## Quick run

**Windows (PowerShell)**:
```powershell
cd <path-to>\FA
.\bootstrap\setup.ps1
```

**macOS / Linux**:
```bash
cd <path-to>/FA
chmod +x bootstrap/setup.sh
./bootstrap/setup.sh
```

Idempotent -- safe to re-run anytime.

## What it does (5 steps)

| # | Step | Behavior if missing |
|---|---|---|
| 1 | Python 3.12+ | Prints install link. Does NOT auto-install (OS-level tool, conflicts too risky) |
| 2 | `uv` package manager | **Auto-installs** via official astral.sh script |
| 3 | Claude Code | Prints install link (may already exist as VSCode extension; not forced) |
| 4 | Portfolio + MCP | Copies `holdings.sample.json` to `holdings.json` if absent; checks the yahoo-finance path in `.mcp.json` is set (see Setup) |
| 5 | Validation | Runs `check.py`: file layout, holdings.json, polymarket.py, MCP config |

## What it does NOT do

- Install Python (too OS-specific; just tells you where)
- Install Node / Claude Code CLI (usually installed globally by user, not per-project)
- Clone or build the Yahoo Finance MCP server (external, see Setup below)
- Modify any file outside this repo folder
- Touch your system PATH beyond what `uv`'s own installer does
- Need admin / sudo

## Setup: Yahoo Finance MCP server

The Yahoo Finance MCP server is not vendored in this repo. Install it once:

1. Clone the upstream project (e.g. `https://github.com/Alex2Yang97/yahoo-finance-mcp`) somewhere on your machine.
2. In that folder run `uv sync` to build its venv.
3. Edit `.mcp.json` in this repo: replace `/ABSOLUTE/PATH/TO/yahoo-finance-mcp` with the absolute path to your clone.

Then copy `portfolio/holdings.sample.json` to `portfolio/holdings.json` and fill in your own accounts. `setup.ps1` / `setup.sh` does that copy for you on first run.

## Standalone validation

If you just want to check health without re-running install:

```bash
python3 bootstrap/check.py     # or `py bootstrap\check.py` on Windows
```

Returns exit code 0 on all-pass, non-zero on any hard failure. Missing `holdings.json` or an unconfigured MCP path are warnings, not failures.

## Troubleshooting

**"uv: command not found" after install**: The installer writes to `~/.cargo/bin` or `~/.local/bin`. Restart your terminal to reload PATH, then re-run.

**"MCP configured" warning on validation**: The yahoo-finance path in `.mcp.json` is still the placeholder. Set it per the Setup section above, then re-run.

**"yfinance timed out"**: Network issue or Yahoo rate-limiting. Wait 30 seconds and re-run.

**On Windows, "cannot run script" PowerShell error**: Set execution policy for this session:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\bootstrap\setup.ps1
```
