#!/usr/bin/env python3
"""Benchmark data tool for the FA investment assistant.

yfinance's `Ticker.info` does NOT expose ETF sector weights. For the
SPY-anchored concentration / factor rules in CLAUDE.md to work, agents
need a reliable way to pull current benchmark composition.

This tool uses `Ticker.funds_data.sector_weightings` (not exposed via
the MCP server) and prints compact JSON.

Usage:
    python tools/benchmark.py spy-sectors
    python tools/benchmark.py spy-top-holdings
    python tools/benchmark.py etf-sectors --ticker QQQ

Run via a Python env with yfinance available (e.g. the Yahoo Finance MCP venv):
    python tools/benchmark.py spy-sectors
"""
from __future__ import annotations

import argparse
import json
import sys

try:
    import yfinance as yf
except ImportError:
    print(json.dumps({
        "error": "yfinance not installed. Run via a Python env with yfinance "
                 "available (e.g. the Yahoo Finance MCP venv): python tools/benchmark.py ..."
    }), file=sys.stderr)
    sys.exit(2)


# Canonical mapping for the sector names FA uses internally vs yfinance's keys.
YF_TO_CANONICAL: dict[str, str] = {
    "technology": "Technology",
    "financial_services": "Financial Services",
    "healthcare": "Healthcare",
    "communication_services": "Communication Services",
    "consumer_cyclical": "Consumer Cyclical",
    "consumer_defensive": "Consumer Defensive",
    "industrials": "Industrials",
    "energy": "Energy",
    "utilities": "Utilities",
    "basic_materials": "Basic Materials",
    "realestate": "Real Estate",
}


def etf_sectors(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    try:
        fd = t.funds_data
        raw = fd.sector_weightings or {}
    except Exception as e:
        return {"error": f"funds_data unavailable for {ticker}: {e}"}

    normalized = {
        YF_TO_CANONICAL.get(k, k): round(float(v), 4)
        for k, v in raw.items()
    }
    return {
        "ticker": ticker,
        "source": "yfinance funds_data.sector_weightings",
        "sector_weights": normalized,
        "total": round(sum(normalized.values()), 4),
    }


def etf_top_holdings(ticker: str, n: int = 10) -> dict:
    t = yf.Ticker(ticker)
    try:
        fd = t.funds_data
        th = fd.top_holdings
    except Exception as e:
        return {"error": f"top_holdings unavailable for {ticker}: {e}"}

    out: list[dict] = []
    try:
        df = th.head(n) if th is not None else None
        if df is None or len(df) == 0:
            return {"error": "top_holdings returned empty"}
        for symbol, row in df.iterrows():
            out.append({
                "symbol": symbol,
                "name": row.get("Name") or row.get("holdingName"),
                "weight": round(float(row.get("Holding Percent", 0)), 4),
            })
    except Exception as e:
        return {"error": f"parsing top_holdings: {e}"}

    return {
        "ticker": ticker,
        "source": "yfinance funds_data.top_holdings",
        "top_n": n,
        "holdings": out,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Pull ETF benchmark composition data")
    p.add_argument("command", choices=["spy-sectors", "spy-top-holdings", "etf-sectors", "etf-top-holdings"])
    p.add_argument("--ticker", default=None, help="ETF ticker (defaults: SPY for spy-* commands)")
    p.add_argument("--top-n", type=int, default=10, help="Number of top holdings")
    args = p.parse_args()

    ticker = args.ticker or ("SPY" if args.command.startswith("spy") else None)
    if not ticker:
        print(json.dumps({"error": "--ticker required for etf-* commands"}), file=sys.stderr)
        return 2

    if args.command in {"spy-sectors", "etf-sectors"}:
        result = etf_sectors(ticker)
    else:
        result = etf_top_holdings(ticker, n=args.top_n)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    sys.exit(main())
