"""Holt Kurse, Devisen und News von Yahoo Finance (yfinance) und schreibt sie als JSON.

Wird von GitHub Actions alle ~10 Minuten ausgeführt. Ausgabe: site/data/market.json
"""
import argparse
import datetime as dt
import json
import math
import os
import re
import sys
import time

import yfinance as yf

# Kürzel im Terminal -> Yahoo-Ticker
SYMS = {
    "NESN": "NESN.SW", "NOVN": "NOVN.SW", "ROG": "ROG.SW", "UBSG": "UBSG.SW",
    "ABBN": "ABBN.SW", "ZURN": "ZURN.SW", "LOGN": "LOGN.SW",
    "AAPL": "AAPL", "NVDA": "NVDA", "MSFT": "MSFT", "TSLA": "TSLA",
    "SMI": "^SSMI", "SPX": "^GSPC", "BTC": "BTC-USD", "XAU": "GC=F", "EURCHF": "EURCHF=X",
}
FX = "USDCHF=X"
# Für diese Titel werden News geholt (SPX-News gelten als Makro-Meldungen)
NEWS_SYMS = ["NESN", "NOVN", "ROG", "UBSG", "ABBN", "ZURN", "LOGN", "AAPL", "NVDA", "MSFT", "TSLA", "BTC", "XAU", "SPX"]

POS = ("beat", "beats", "surge", "surges", "soar", "soars", "jump", "jumps", "rally", "rallies", "record",
       "upgrade", "upgraded", "raise", "raises", "raised", "gain", "gains", "strong", "stronger", "growth",
       "profit", "profits", "outperform", "bullish", "rise", "rises", "rising", "higher", "boost", "boosts",
       "tops", "exceeds", "approval", "approved", "wins", "win", "rebound", "rebounds", "buyback", "upbeat",
       "optimism", "optimistic", "expands", "climbs", "climb", "breakthrough", "partnership", "dividend",
       "steigt", "steigen", "rekord", "gewinn", "hebt", "übertrifft", "stark", "kaufen", "erholt")
NEG = ("miss", "misses", "missed", "plunge", "plunges", "fall", "falls", "falling", "drop", "drops", "slump",
       "slumps", "downgrade", "downgraded", "cut", "cuts", "weak", "weaker", "loss", "losses", "lawsuit",
       "probe", "investigation", "recall", "warning", "warns", "warn", "bearish", "lower", "decline",
       "declines", "sell-off", "selloff", "layoffs", "layoff", "fined", "fine", "tariff", "tariffs", "crash",
       "concern", "concerns", "fears", "fear", "slides", "slide", "tumbles", "tumble", "sinks", "sink",
       "lags", "scrutiny", "delay", "delays", "halt", "halts", "risk", "risks", "worst",
       "fällt", "fallen", "verlust", "senkt", "warnt", "schwach", "verkaufen", "einbruch")


def sentiment(text):
    words = re.findall(r"[a-zäöüß\-]+", text.lower())
    p = sum(w in POS for w in words)
    n = sum(w in NEG for w in words)
    if p == n:
        return 0.0
    return round(math.tanh((p - n) * 0.7), 2)


def num(x, nd=6):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return round(v, nd)


def history(df, ticker):
    try:
        d = df[ticker]
    except KeyError:
        return []
    d = d.dropna(subset=["Close"])
    rows = []
    for ts, r in d.iterrows():
        c = num(r["Close"])
        if c is None or c <= 0:
            continue
        o = num(r.get("Open")) or c
        h = num(r.get("High")) or max(o, c)
        l = num(r.get("Low")) or min(o, c)
        v = num(r.get("Volume"), 0) or 0
        rows.append([ts.strftime("%Y-%m-%d"), o, max(h, o, c), min(l, o, c), c, v])
    return rows


def parse_news(item, sym):
    c = item.get("content") if isinstance(item.get("content"), dict) else item
    title = (c.get("title") or "").strip()
    if not title:
        return None
    url = ((c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url")
           or item.get("link") or "")
    prov = (c.get("provider") or {}).get("displayName") or item.get("publisher") or "Yahoo Finance"
    ts = None
    pub = c.get("pubDate") or c.get("displayTime")
    if pub:
        try:
            ts = int(dt.datetime.fromisoformat(pub.replace("Z", "+00:00")).timestamp() * 1000)
        except ValueError:
            ts = None
    if ts is None and item.get("providerPublishTime"):
        ts = int(item["providerPublishTime"]) * 1000
    if ts is None:
        return None
    summary = (c.get("summary") or "").strip()
    return {"t": ts, "sym": None if sym == "SPX" else sym, "head": title, "src": prov,
            "url": url if url.startswith("https://") else "", "sent": sentiment(title + " " + summary[:300])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site/data/market.json")
    args = ap.parse_args()

    tickers = list(SYMS.values()) + [FX]
    df = yf.download(tickers, period="1y", interval="1d", group_by="ticker",
                     auto_adjust=False, progress=False, threads=True)

    out = {"updated": int(time.time() * 1000), "fx": None, "instruments": {}, "news": []}
    for sym, t in SYMS.items():
        rows = history(df, t)
        if len(rows) >= 60:
            out["instruments"][sym] = rows
        else:
            print(f"Warnung: zu wenig Daten für {sym} ({t}): {len(rows)} Tage", file=sys.stderr)
    fx_rows = history(df, FX)
    if fx_rows:
        out["fx"] = fx_rows[-1][4]

    seen = set()
    for sym in NEWS_SYMS:
        try:
            items = yf.Ticker(SYMS[sym]).news or []
        except Exception as e:  # News sind optional
            print(f"News für {sym} fehlgeschlagen: {e}", file=sys.stderr)
            continue
        for it in items[:8]:
            n = parse_news(it, sym)
            if n and n["head"] not in seen:
                seen.add(n["head"])
                out["news"].append(n)
    out["news"].sort(key=lambda n: n["t"], reverse=True)
    out["news"] = out["news"][:80]

    if len(out["instruments"]) < 8:
        sys.exit(f"Abbruch: nur {len(out['instruments'])} Titel geladen, alte Daten bleiben online.")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"OK: {len(out['instruments'])} Titel, {len(out['news'])} News, USD/CHF {out['fx']}")


if __name__ == "__main__":
    main()
