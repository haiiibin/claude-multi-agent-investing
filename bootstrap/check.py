#!/usr/bin/env python3
"""FA post-install health check.

Runs AFTER setup.ps1 / setup.sh. Validates the system can actually pull data.
Exits 0 if all good, non-zero if anything is broken.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


FA_ROOT = Path(__file__).resolve().parent.parent
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"


def ok(msg: str) -> None:
    print(f"  {GREEN}OK{NC}: {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}WARN{NC}: {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}FAIL{NC}: {msg}")


def check_layout() -> bool:
    required = [
        "CLAUDE.md",
        ".mcp.json",
        ".claude/commands/market-pulse.md",
        ".claude/agents/buffett.md",
        "tools/polymarket.py",
        "portfolio/holdings.sample.json",
    ]
    missing = [p for p in required if not (FA_ROOT / p).exists()]
    if missing:
        fail(f"Missing files: {missing}")
        return False
    ok(f"All {len(required)} required files present")
    return True


def check_holdings_valid_json() -> bool:
    p = FA_ROOT / "portfolio" / "holdings.json"
    if not p.exists():
        warn("portfolio/holdings.json not found. Copy the sample to get started: "
             "cp portfolio/holdings.sample.json portfolio/holdings.json")
        return True
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "accounts" in data and isinstance(data["accounts"], list)
        ok(f"holdings.json parses. {len(data['accounts'])} account(s) defined.")
        return True
    except Exception as e:
        fail(f"holdings.json invalid: {e}")
        return False


def check_polymarket_script() -> bool:
    """Run polymarket.py with a tiny query. Doesn't need .venv."""
    script = FA_ROOT / "tools" / "polymarket.py"
    try:
        r = subprocess.run(
            [sys.executable, str(script), "--topic", "fed", "--limit", "1"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode != 0:
            fail(f"polymarket.py failed: {r.stderr[:200]}")
            return False
        data = json.loads(r.stdout)
        if data.get("source") != "polymarket":
            fail("polymarket.py output looks wrong")
            return False
        ok(f"polymarket.py works. Got {data.get('count', 0)} market(s).")
        return True
    except subprocess.TimeoutExpired:
        fail("polymarket.py timed out (network issue?)")
        return False
    except Exception as e:
        fail(f"polymarket.py error: {e}")
        return False


def check_mcp_configured() -> bool:
    """Check that the Yahoo Finance MCP server path in .mcp.json has been set.

    The MCP server is not vendored in this repo. Users clone it separately and
    point .mcp.json at it (see bootstrap/README.md, Setup). This is a warn-level
    check so a fresh clone still passes overall.
    """
    p = FA_ROOT / ".mcp.json"
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f".mcp.json invalid JSON: {e}")
        return False

    args = cfg.get("mcpServers", {}).get("yahoo-finance", {}).get("args", [])
    if any("/ABSOLUTE/PATH/TO/" in str(a) for a in args):
        warn("Yahoo Finance MCP path in .mcp.json is still the placeholder. "
             "Clone the yahoo-finance-mcp server and set its path "
             "(see bootstrap/README.md, Setup section).")
        return True
    ok("Yahoo Finance MCP path in .mcp.json is configured.")
    return True


def check_yfinance_network() -> bool:
    """Optional live yfinance call, only if yfinance is importable in this interpreter.

    yfinance normally lives inside the MCP server's own venv, not this interpreter,
    so a missing import is a skip (warn), not a failure.
    """
    if importlib.util.find_spec("yfinance") is None:
        warn("yfinance not installed in this interpreter (it lives in the MCP server venv). "
             "Skipping live price test.")
        return True

    try:
        r = subprocess.run(
            [sys.executable, "-c",
             "import yfinance as yf; p = yf.Ticker('AAPL').info.get('currentPrice'); "
             "assert p and p > 0, 'bad price'; print(f'AAPL=${p}')"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode != 0:
            fail(f"yfinance call failed (network?): {r.stderr[:300]}")
            return False
        ok(f"yfinance network: {r.stdout.strip()}")
        return True
    except subprocess.TimeoutExpired:
        fail("yfinance timed out (network or rate-limit)")
        return False
    except Exception as e:
        fail(f"yfinance error: {e}")
        return False


def main() -> int:
    print()
    print(f"  Validating FA at {FA_ROOT}")
    print()

    checks = [
        ("File layout", check_layout),
        ("holdings.json", check_holdings_valid_json),
        ("polymarket.py", check_polymarket_script),
        ("MCP configured", check_mcp_configured),
        ("yfinance network", check_yfinance_network),
    ]

    results = []
    for name, fn in checks:
        print(f"  [{name}]")
        results.append(fn())
        print()

    passed = sum(results)
    total = len(results)
    print(f"  Result: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
