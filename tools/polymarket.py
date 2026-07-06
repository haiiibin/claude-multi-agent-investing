#!/usr/bin/env python3
"""Polymarket query tool for the FA investment assistant.

Queries Polymarket's Gamma API (free, no auth). Returns compact JSON
optimized for LLM consumption -- filters high-volume markets, returns
probabilities not raw API objects.

Usage:
    python tools/polymarket.py --topic fed --limit 5
    python tools/polymarket.py --query "nvidia" --min-volume 10000
    python tools/polymarket.py --topic recession --limit 3

Stdlib only. No pip deps required.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlencode

GAMMA_API = "https://gamma-api.polymarket.com"

TOPICS: dict[str, list[str]] = {
    "fed": ["fed ", "fomc", "interest rate", "rate cut", "rate hike", "basis point", "jerome powell"],
    "cpi": ["cpi", "inflation"],
    "jobs": ["unemployment", "nfp", "nonfarm", "jobs report", "payroll"],
    "recession": ["recession", "hard landing", "soft landing"],
    "gdp": ["gdp"],
    "macro": ["fed ", "fomc", "cpi", "inflation", "gdp", "unemployment", "recession", "interest rate"],
    "election": ["election", "president"],
    "tariff": ["tariff", "trade war"],
    "china": ["china", "taiwan", "xi jinping"],
    "russia": ["russia", "ukraine", "putin"],
    "middle-east": ["iran", "israel", "gaza", "houthi"],
    "crypto": ["bitcoin", "ethereum", "btc ", " eth ", "crypto"],
    "ai": ["openai", "anthropic", "agi", "chatgpt", "gpt-", "claude"],
    "earnings": ["earnings", "beat", "q1 ", "q2 ", "q3 ", "q4 ", "report"],
}


def fetch_markets(pool_size: int = 200) -> list[dict]:
    """Pull highest-volume active markets. One API call."""
    url = f"{GAMMA_API}/markets?" + urlencode({
        "active": "true",
        "closed": "false",
        "limit": pool_size,
        "order": "volume24hr",
        "ascending": "false",
    })
    req = urllib.request.Request(url, headers={"User-Agent": "FA-PolymarketTool/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        print(json.dumps({"error": f"Polymarket API unreachable: {e}"}), file=sys.stderr)
        sys.exit(2)


def parse_list_str(s) -> list:
    """Polymarket returns outcomes/outcomePrices as JSON-stringified arrays."""
    if not s:
        return []
    if isinstance(s, list):
        return s
    try:
        return json.loads(s)
    except (TypeError, json.JSONDecodeError):
        return []


def _classify_liquidity(volume_24h: float, liquidity: float, open_interest: float) -> str:
    """Signal quality for LLM consumers -- probability on an illiquid market is noise."""
    if volume_24h >= 50_000 or liquidity >= 100_000 or open_interest >= 500_000:
        return "deep"
    if volume_24h >= 10_000 or liquidity >= 25_000 or open_interest >= 100_000:
        return "moderate"
    if volume_24h >= 1_000 or liquidity >= 5_000:
        return "thin"
    return "noise"


def format_market(m: dict) -> dict:
    """Trim raw API object to the fields agents actually need."""
    outcomes = parse_list_str(m.get("outcomes"))
    prices = parse_list_str(m.get("outcomePrices"))

    probs = None
    if outcomes and prices and len(outcomes) == len(prices):
        try:
            probs = {o: round(float(p), 4) for o, p in zip(outcomes, prices)}
        except (TypeError, ValueError):
            probs = None

    def _num(v, default: float = 0.0) -> float:
        try:
            return round(float(v or 0), 2)
        except (TypeError, ValueError):
            return default

    volume_24h = _num(m.get("volume24hr"))
    liquidity = _num(m.get("liquidity"))
    open_interest = _num(m.get("openInterest"))

    return {
        "question": m.get("question"),
        "probabilities": probs,
        "volume_24h_usd": volume_24h,
        "volume_1wk_usd": _num(m.get("volume1wk")),
        "liquidity_usd": liquidity,
        "open_interest_usd": open_interest,
        "signal_quality": _classify_liquidity(volume_24h, liquidity, open_interest),
        "one_day_change": m.get("oneDayPriceChange"),
        "end_date": m.get("endDate"),
        "url": f"https://polymarket.com/event/{m.get('slug', '')}",
    }


def filter_by_topic(markets: list[dict], topic: str) -> list[dict]:
    kws = TOPICS.get(topic.lower(), [topic.lower()])
    return [m for m in markets if any(kw in (m.get("question") or "").lower() for kw in kws)]


def filter_by_query(markets: list[dict], query: str) -> list[dict]:
    q = query.lower()
    return [m for m in markets if q in (m.get("question") or "").lower()]


def main() -> None:
    p = argparse.ArgumentParser(description="Query Polymarket prediction markets (free, no key)")
    p.add_argument("--topic", help=f"Predefined topic. Options: {', '.join(sorted(TOPICS.keys()))}")
    p.add_argument("--query", help="Substring search in market question")
    p.add_argument("--limit", type=int, default=5, help="Max results (default 5)")
    p.add_argument("--min-volume", type=float, default=0, help="Filter: 24h volume floor in USD")
    p.add_argument("--pool-size", type=int, default=300, help="API pool size before filtering")
    args = p.parse_args()

    markets = fetch_markets(pool_size=args.pool_size)

    if args.topic:
        markets = filter_by_topic(markets, args.topic)
    if args.query:
        markets = filter_by_query(markets, args.query)
    if args.min_volume > 0:
        markets = [m for m in markets if float(m.get("volume24hr") or 0) >= args.min_volume]

    markets = markets[:args.limit]

    output = {
        "source": "polymarket",
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(markets),
        "markets": [format_market(m) for m in markets],
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
