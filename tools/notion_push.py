"""
Notion sync for FA portfolio dashboard.

Config:
  Copy notion_config.example.json to notion_config.json and fill in your own
  Notion integration token and dashboard_page_id. notion_config.json is gitignored;
  no token or database id is hardcoded in this file.

Usage:
  python tools/notion_push.py setup    -- create FA Dashboard + databases (run once)
  python tools/notion_push.py sync     -- sync holdings from holdings.json
  python tools/notion_push.py journal "Title" "Content"  -- add journal entry
"""

import json
import sys
import requests
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "notion_config.json"
HOLDINGS_PATH = BASE_DIR / "portfolio" / "holdings.json"
NOTION_VERSION = "2022-06-28"
API = "https://api.notion.com/v1"


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def post(token, path, body):
    r = requests.post(f"{API}{path}", headers=headers(token), json=body)
    r.raise_for_status()
    return r.json()


def patch(token, path, body):
    r = requests.patch(f"{API}{path}", headers=headers(token), json=body)
    r.raise_for_status()
    return r.json()


def get(token, path):
    r = requests.get(f"{API}{path}", headers=headers(token))
    r.raise_for_status()
    return r.json()


# ── Setup ──────────────────────────────────────────────────────────────────────

def setup():
    cfg = load_config()
    token = cfg["token"]

    parent_id = cfg.get("dashboard_page_id")
    if not parent_id:
        print("dashboard_page_id not set in notion_config.json")
        sys.exit(1)
    print(f"  Using dashboard page: {parent_id}")

    print("Creating Portfolio Holdings database...")
    portfolio_db = post(token, "/databases", {
        "parent": {"type": "page_id", "page_id": parent_id},
        "icon": {"type": "emoji", "emoji": "💼"},
        "title": [{"type": "text", "text": {"content": "Portfolio Holdings"}}],
        "properties": {
            "Ticker":        {"title": {}},
            "Name":          {"rich_text": {}},
            "Account":       {"select": {"options": [
                                {"name": "Broker A", "color": "blue"},
                                {"name": "Broker B TFSA", "color": "green"},
                                {"name": "Broker B Taxable", "color": "orange"},
                             ]}},
            "Shares":        {"number": {"format": "number"}},
            "Cost/Share":    {"number": {"format": "number"}},
            "Cost Total":    {"number": {"format": "number"}},
            "Mkt Value":     {"number": {"format": "number"}},
            "Currency":      {"select": {"options": [
                                {"name": "USD", "color": "default"},
                                {"name": "CAD", "color": "red"},
                             ]}},
            "Tags":          {"multi_select": {}},
            "Updated":       {"date": {}},
        },
    })
    portfolio_db_id = portfolio_db["id"]
    print(f"  Portfolio DB: {portfolio_db_id}")

    print("Creating Investment Journal database...")
    journal_db = post(token, "/databases", {
        "parent": {"type": "page_id", "page_id": parent_id},
        "icon": {"type": "emoji", "emoji": "📓"},
        "title": [{"type": "text", "text": {"content": "Investment Journal"}}],
        "properties": {
            "Title":    {"title": {}},
            "Date":     {"date": {}},
            "Type":     {"select": {"options": [
                            {"name": "YouTube Pulse", "color": "purple"},
                            {"name": "Trade", "color": "green"},
                            {"name": "TFSA Action", "color": "blue"},
                            {"name": "Rebalance", "color": "orange"},
                            {"name": "Macro Note", "color": "yellow"},
                            {"name": "Watchlist Update", "color": "gray"},
                        ]}},
            "Tickers":  {"multi_select": {}},
            "Signal":   {"select": {"options": [
                            {"name": "Bullish", "color": "green"},
                            {"name": "Bearish", "color": "red"},
                            {"name": "Neutral", "color": "gray"},
                            {"name": "Action Taken", "color": "blue"},
                        ]}},
        },
    })
    journal_db_id = journal_db["id"]
    print(f"  Journal DB: {journal_db_id}")

    cfg["portfolio_db_id"] = portfolio_db_id
    cfg["journal_db_id"] = journal_db_id
    save_config(cfg)
    print("\nSetup complete. IDs saved to notion_config.json.")
    print(f"Open Notion and navigate to 'FA Dashboard' to view.")


# ── Sync Holdings ──────────────────────────────────────────────────────────────

ACCOUNT_LABEL = {
    "broker-a-taxable":  "Broker A",
    "broker-b-tfsa":     "Broker B TFSA",
    "broker-b-taxable":  "Broker B Taxable",
}

def clear_db(token, db_id):
    """Delete all existing rows in a database."""
    r = requests.post(f"{API}/databases/{db_id}/query", headers=headers(token), json={})
    r.raise_for_status()
    pages = r.json().get("results", [])
    for p in pages:
        requests.delete(f"{API}/blocks/{p['id']}", headers=headers(token))


def sync_holdings():
    cfg = load_config()
    token = cfg["token"]
    db_id = cfg.get("portfolio_db_id")
    if not db_id:
        print("Run setup first: python tools/notion_push.py setup")
        sys.exit(1)

    holdings_data = json.loads(HOLDINGS_PATH.read_text(encoding="utf-8"))
    now_iso = datetime.now(timezone.utc).date().isoformat()

    print("Clearing existing holdings rows...")
    clear_db(token, db_id)

    print("Syncing holdings...")
    for account in holdings_data["accounts"]:
        acct_label = ACCOUNT_LABEL.get(account["id"], account["id"])
        for h in account.get("holdings", []):
            ticker = h["ticker"]
            tags = [{"name": t} for t in h.get("tags", [])]
            props = {
                "Ticker":     {"title": [{"text": {"content": ticker}}]},
                "Name":       {"rich_text": [{"text": {"content": h.get("name", "")}}]},
                "Account":    {"select": {"name": acct_label}},
                "Currency":   {"select": {"name": h.get("currency", "USD")}},
                "Tags":       {"multi_select": tags},
                "Updated":    {"date": {"start": now_iso}},
            }
            if h.get("shares") is not None:
                props["Shares"] = {"number": h["shares"]}
            if h.get("cost_basis_per_share") is not None:
                props["Cost/Share"] = {"number": round(h["cost_basis_per_share"], 4)}
            if h.get("cost_basis_total") is not None:
                props["Cost Total"] = {"number": round(h["cost_basis_total"], 2)}
            if h.get("market_value_approx") is not None:
                props["Mkt Value"] = {"number": round(h["market_value_approx"], 2)}

            post(token, "/pages", {
                "parent": {"database_id": db_id},
                "properties": props,
            })
            print(f"  + {ticker} ({acct_label})")

    # Also add cash rows
    for account in holdings_data["accounts"]:
        acct_label = ACCOUNT_LABEL.get(account["id"], account["id"])
        for currency, amount in account.get("cash", {}).items():
            if amount and amount > 0:
                post(token, "/pages", {
                    "parent": {"database_id": db_id},
                    "properties": {
                        "Ticker":   {"title": [{"text": {"content": f"CASH ({currency})"}}]},
                        "Name":     {"rich_text": [{"text": {"content": f"{acct_label} cash"}}]},
                        "Account":  {"select": {"name": acct_label}},
                        "Mkt Value":{"number": amount},
                        "Currency": {"select": {"name": currency}},
                        "Tags":     {"multi_select": [{"name": "cash"}]},
                        "Updated":  {"date": {"start": now_iso}},
                    },
                })
                print(f"  + CASH {currency} {amount} ({acct_label})")

    print("Sync complete.")


# ── Add Journal Entry ──────────────────────────────────────────────────────────

def add_journal(title: str, content: str, entry_type: str = "Macro Note",
                tickers: list = None, signal: str = "Neutral"):
    cfg = load_config()
    token = cfg["token"]
    db_id = cfg.get("journal_db_id")
    if not db_id:
        print("Run setup first: python tools/notion_push.py setup")
        sys.exit(1)

    today = datetime.now(timezone.utc).date().isoformat()
    ticker_tags = [{"name": t} for t in (tickers or [])]

    # Notion paragraph blocks are limited to 2000 chars per rich_text object
    def _chunk(text, max_len=1900):
        chunks = []
        while len(text) > max_len:
            split_at = text.rfind('\n', 0, max_len)
            if split_at == -1:
                split_at = max_len
            chunks.append(text[:split_at])
            text = text[split_at:].lstrip('\n')
        if text:
            chunks.append(text)
        return chunks

    children = [
        {"object": "block", "type": "paragraph",
         "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}}
        for chunk in _chunk(content)
    ]

    page = post(token, "/pages", {
        "parent": {"database_id": db_id},
        "properties": {
            "Title":   {"title": [{"text": {"content": title}}]},
            "Date":    {"date": {"start": today}},
            "Type":    {"select": {"name": entry_type}},
            "Tickers": {"multi_select": ticker_tags},
            "Signal":  {"select": {"name": signal}},
        },
        "children": children,
    })
    print(f"Journal entry created: {title}")
    return page["id"]


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "setup":
        setup()
    elif cmd == "sync":
        sync_holdings()
    elif cmd == "journal":
        title = sys.argv[2] if len(sys.argv) > 2 else "Note"
        content = sys.argv[3] if len(sys.argv) > 3 else ""
        entry_type = sys.argv[4] if len(sys.argv) > 4 else "Macro Note"
        tickers_raw = sys.argv[5] if len(sys.argv) > 5 else ""
        tickers = [t.strip() for t in tickers_raw.split(",") if t.strip()]
        signal = sys.argv[6] if len(sys.argv) > 6 else "Neutral"
        add_journal(title, content, entry_type, tickers, signal)
    else:
        print(__doc__)
