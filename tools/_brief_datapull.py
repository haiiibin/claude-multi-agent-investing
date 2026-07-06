"""One-shot data pull for weekly-brief. Outputs JSON to stdout."""
import json, sys, warnings
warnings.filterwarnings("ignore")
import yfinance as yf
import pandas as pd
import numpy as np

# Sample ticker set for a standalone data-pull demo. In normal use the weekly-brief
# reads the real ticker set from portfolio/holdings.json instead of this hardcoded list.
HOLDINGS = ["AAPL", "SPY", "XEQT.TO"]
WATCH = ["AMD", "ASML", "INTC", "MU"]
MACRO = ["SPY", "QQQ", "^VIX", "^TNX", "DX-Y.NYB", "CL=F", "GC=F", "CAD=X"]

def rsi(series, n=14):
    d = series.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = (-d.clip(upper=0)).rolling(n).mean()
    rs = up / dn
    return float((100 - 100/(1+rs)).iloc[-1])

def macd(series):
    e12 = series.ewm(span=12, adjust=False).mean()
    e26 = series.ewm(span=26, adjust=False).mean()
    line = e12 - e26
    sig = line.ewm(span=9, adjust=False).mean()
    return float(line.iloc[-1]), float(sig.iloc[-1]), float((line-sig).iloc[-1])

def atr(h, n=14):
    hi, lo, cl = h["High"], h["Low"], h["Close"]
    tr = pd.concat([hi-lo, (hi-cl.shift()).abs(), (lo-cl.shift()).abs()], axis=1).max(axis=1)
    return float(tr.rolling(n).mean().iloc[-1])

def safe(info, *keys):
    for k in keys:
        v = info.get(k)
        if v is not None:
            return v
    return None

def pull(tk):
    out = {"ticker": tk}
    try:
        t = yf.Ticker(tk)
        info = t.info
        price = safe(info, "currentPrice", "regularMarketPrice", "previousClose")
        out["price"] = price
        out["prev_close"] = safe(info, "previousClose")
        out["mktcap"] = safe(info, "marketCap")
        out["pe_trail"] = safe(info, "trailingPE")
        out["pe_fwd"] = safe(info, "forwardPE")
        out["peg"] = safe(info, "trailingPegRatio")
        out["rev_growth"] = safe(info, "revenueGrowth")
        out["gross_margin"] = safe(info, "grossMargins")
        out["fcf"] = safe(info, "freeCashflow")
        out["d2e"] = safe(info, "debtToEquity")
        out["beta"] = safe(info, "beta")
        out["sector"] = safe(info, "sector")
        out["industry"] = safe(info, "industry")
        out["rec"] = safe(info, "recommendationKey")
        out["target_mean"] = safe(info, "targetMeanPrice")
        out["target_high"] = safe(info, "targetHighPrice")
        out["target_low"] = safe(info, "targetLowPrice")
        out["wk52_high"] = safe(info, "fiftyTwoWeekHigh")
        out["wk52_low"] = safe(info, "fiftyTwoWeekLow")
        out["div_yield_raw"] = safe(info, "dividendYield")
        out["div_rate"] = safe(info, "trailingAnnualDividendRate")
        ed = safe(info, "earningsTimestamp")
        try:
            cal = t.calendar
            if isinstance(cal, dict):
                out["earnings_date"] = str(cal.get("Earnings Date"))
        except Exception:
            pass
        # history for technicals
        h = t.history(period="1y", auto_adjust=True)
        if len(h) > 5:
            c = h["Close"]
            out["chg_1d_pct"] = round(float((c.iloc[-1]/c.iloc[-2]-1)*100), 2) if len(c) >= 2 else None
            out["chg_1m_pct"] = round(float((c.iloc[-1]/c.iloc[-22]-1)*100), 2) if len(c) >= 22 else None
            out["chg_3m_pct"] = round(float((c.iloc[-1]/c.iloc[-64]-1)*100), 2) if len(c) >= 64 else None
            out["ma20"] = round(float(c.rolling(20).mean().iloc[-1]), 2) if len(c) >= 20 else None
            out["ma50"] = round(float(c.rolling(50).mean().iloc[-1]), 2) if len(c) >= 50 else None
            out["ma200"] = round(float(c.rolling(200).mean().iloc[-1]), 2) if len(c) >= 200 else None
            if len(c) >= 15:
                out["rsi14"] = round(rsi(c), 1)
            if len(c) >= 27:
                ml, ms, mh = macd(c)
                out["macd"] = {"line": round(ml,2), "signal": round(ms,2), "hist": round(mh,2)}
            if len(c) >= 20:
                m = c.rolling(20).mean().iloc[-1]; sd = c.rolling(20).std().iloc[-1]
                out["bollinger"] = {"upper": round(float(m+2*sd),2), "lower": round(float(m-2*sd),2), "mid": round(float(m),2)}
            if len(h) >= 15:
                out["atr14"] = round(atr(h), 2)
    except Exception as e:
        out["error"] = str(e)
    return out

result = {"holdings": [pull(t) for t in HOLDINGS],
          "watchlist": [pull(t) for t in WATCH],
          "macro": [pull(t) for t in MACRO]}
print(json.dumps(result, indent=1, default=str))
