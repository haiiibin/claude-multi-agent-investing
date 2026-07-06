#!/usr/bin/env bash
# FA bootstrap -- macOS / Linux
# Run from FA folder:  ./bootstrap/setup.sh
# Idempotent -- safe to re-run.

set -e
FA_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo
echo -e "${CYAN}=== FA Bootstrap (Unix) ===${NC}"
echo "FA root: $FA_ROOT"
echo

all_good=1

# --- 1. Python 3.12+ ---
echo "[1/5] Checking Python 3.12+..."
PY_CMD=""
for candidate in python3.13 python3.12 python3 python; do
    if command -v "$candidate" &>/dev/null; then
        if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)" 2>/dev/null; then
            PY_CMD="$candidate"
            echo -e "  ${GREEN}OK${NC}: $($candidate --version) via '$candidate'"
            break
        fi
    fi
done
if [ -z "$PY_CMD" ]; then
    echo -e "  ${RED}MISSING${NC}: Python 3.12+ not found"
    case "$(uname -s)" in
        Darwin*) echo "  -> brew install python@3.12" ;;
        Linux*)  echo "  -> sudo apt install python3.12 (Debian/Ubuntu) or equivalent" ;;
    esac
    all_good=0
fi

# --- 2. uv (auto-install if missing) ---
echo "[2/5] Checking uv..."
if command -v uv &>/dev/null; then
    echo -e "  ${GREEN}OK${NC}: $(uv --version)"
else
    echo -e "  ${YELLOW}MISSING${NC}: auto-installing uv..."
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        # uv installer puts itself in ~/.local/bin or ~/.cargo/bin
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
        if command -v uv &>/dev/null; then
            echo -e "  ${GREEN}Installed${NC}: restart terminal to ensure PATH picks up"
        else
            echo -e "  ${YELLOW}Installed but PATH not updated. Restart shell, re-run.${NC}"
            all_good=0
        fi
    else
        echo -e "  ${RED}FAILED${NC} auto-install. Manual: https://astral.sh/uv"
        all_good=0
    fi
fi

# --- 3. Claude Code ---
echo "[3/5] Checking Claude Code..."
if command -v claude &>/dev/null; then
    echo -e "  ${GREEN}OK${NC}: $(claude --version 2>&1 | head -1)"
else
    echo -e "  ${YELLOW}NOT FOUND in PATH${NC} (may work via IDE extension)"
    echo "  -> Install: https://claude.com/claude-code"
fi

# --- 4. Portfolio config + MCP server ---
echo "[4/5] Portfolio config + MCP server..."
# Copy the sample portfolio on first run so commands have something to read.
if [ ! -f "$FA_ROOT/portfolio/holdings.json" ]; then
    if [ -f "$FA_ROOT/portfolio/holdings.sample.json" ]; then
        cp "$FA_ROOT/portfolio/holdings.sample.json" "$FA_ROOT/portfolio/holdings.json"
        echo -e "  ${GREEN}OK${NC}: created portfolio/holdings.json from sample (edit it with your own accounts)"
    else
        echo -e "  ${YELLOW}NOTE${NC}: portfolio/holdings.sample.json missing; add your own portfolio/holdings.json"
    fi
else
    echo -e "  ${GREEN}OK${NC}: portfolio/holdings.json already present"
fi
# The Yahoo Finance MCP server is not vendored here. Clone it separately and set its
# path in .mcp.json (see bootstrap/README.md, Setup). This step never hard-fails.
if grep -q "/ABSOLUTE/PATH/TO/" "$FA_ROOT/.mcp.json" 2>/dev/null; then
    echo -e "  ${YELLOW}TODO${NC}: set the yahoo-finance path in .mcp.json (see README Setup)"
else
    echo -e "  ${GREEN}OK${NC}: yahoo-finance path in .mcp.json is configured"
fi

# --- 5. Validation ---
echo "[5/5] Running validation (check.py)..."
if [ -n "$PY_CMD" ] && [ $all_good -eq 1 ]; then
    "$PY_CMD" "$(dirname "$0")/check.py" || all_good=0
else
    echo -e "  ${YELLOW}SKIPPED${NC} (earlier steps failed)"
fi

# --- Summary ---
echo
if [ $all_good -eq 1 ]; then
    echo -e "${GREEN}=== READY ===${NC}"
    echo
    echo "Open Claude Code with FA/ as working directory:"
    echo "  - VSCode: File > Open Folder > $FA_ROOT"
    echo "  - CLI: cd \"$FA_ROOT\" && claude"
    echo
    echo "First test: type /market-pulse in Claude Code"
else
    echo -e "${RED}=== INCOMPLETE ===${NC}"
    echo "Fix items above, then re-run: ./bootstrap/setup.sh"
fi
echo
