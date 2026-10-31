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
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import yfinance as yf

# Kürzel im Terminal -> Yahoo-Ticker
SYMS = {
    "NESN": "NESN.SW", "NOVN": "NOVN.SW", "ROG": "ROG.SW", "UBSG": "UBSG.SW",
    "ABBN": "ABBN.SW", "ZURN": "ZURN.SW", "LOGN": "LOGN.SW",
    "AAPL": "AAPL", "NVDA": "NVDA", "MSFT": "MSFT", "TSLA": "TSLA",
    "SMI": "^SSMI", "SPX": "^GSPC", "BTC": "BTC-USD", "XAU": "GC=F", "EURCHF": "EURCHF=X",
    "SREN": "SREN.SW", "CFR": "CFR.SW", "GIVN": "GIVN.SW", "LONN": "LONN.SW", "SIKA": "SIKA.SW",
    "HOLN": "HOLN.SW", "ALC": "ALC.SW", "GEBN": "GEBN.SW", "SCMN": "SCMN.SW", "PGHN": "PGHN.SW",
    "SLHN": "SLHN.SW", "KNIN": "KNIN.SW", "SOON": "SOON.SW", "UHR": "UHR.SW", "AMZN": "AMZN",
    "GOOGL": "GOOGL", "META": "META", "NFLX": "NFLX", "AMD": "AMD", "JPM": "JPM",
    "V": "V", "KO": "KO", "DIS": "DIS", "PLTR": "PLTR", "ETH": "ETH-USD",
    "SOL": "SOL-USD", "XAG": "SI=F",
}
FX = "USDCHF=X"
# Ersatz-Ticker, falls Yahoo den ersten nicht liefert
ALT = {"ROG": ["RO.SW", "ROG.VX"]}
# Suchbegriffe für Google News (Deutsch, Schweiz). None-Schlüssel = Makro-Meldungen
GNEWS = {
    "NESN": "Nestlé Aktie", "NOVN": "Novartis Aktie", "ROG": "Roche Aktie", "UBSG": "UBS Aktie",
    "ABBN": "ABB Aktie", "ZURN": "Zurich Insurance Aktie", "LOGN": "Logitech Aktie",
    "AAPL": "Apple Aktie", "NVDA": "Nvidia Aktie", "MSFT": "Microsoft Aktie", "TSLA": "Tesla Aktie",
    "BTC": "Bitcoin Kurs", "XAU": "Goldpreis", "EURCHF": "Franken Euro Kurs", "MACRO": "Börse SMI Wall Street",
    "SREN": "Swiss Re Aktie", "CFR": "Richemont Aktie", "GIVN": "Givaudan Aktie", "LONN": "Lonza Aktie",
    "SIKA": "Sika Aktie", "HOLN": "Holcim Aktie", "ALC": "Alcon Aktie", "GEBN": "Geberit Aktie",
    "SCMN": "Swisscom Aktie", "PGHN": "Partners Group Aktie", "SLHN": "Swiss Life Aktie", "KNIN": "Kühne+Nagel Aktie",
    "SOON": "Sonova Aktie", "UHR": "Swatch Aktie", "AMZN": "Amazon Aktie", "GOOGL": "Alphabet Aktie",
    "META": "Meta Aktie", "NFLX": "Netflix Aktie", "AMD": "AMD Aktie", "JPM": "JPMorgan Aktie",
    "V": "Visa Aktie", "KO": "Coca-Cola Aktie", "DIS": "Disney Aktie", "PLTR": "Palantir Aktie",
    "ETH": "Ethereum Kurs", "SOL": "Solana Kurs", "XAG": "Silberpreis",
}
# Für diese Titel werden News geholt (SPX-News gelten als Makro-Meldungen)
NEWS_SYMS = ["NESN", "NOVN", "ROG", "UBSG", "ABBN", "ZURN", "LOGN", "AAPL", "NVDA", "MSFT", "TSLA", "BTC", "XAU", "SPX", "SREN", "CFR", "GIVN", "LONN", "SIKA", "HOLN", "ALC", "GEBN", "SCMN", "PGHN", "SLHN", "KNIN", "SOON", "UHR", "AMZN", "GOOGL", "META", "NFLX", "AMD", "JPM", "V", "KO", "DIS", "PLTR", "ETH", "SOL", "XAG"]

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
       "fällt", "fallen", "verlust", "senkt", "warnt", "schwach", "verkaufen", "einbruch",
       "sinkt", "sinken", "verliert", "verlieren", "verluste", "rückgang", "abstufung", "klage", "untersuchung",
       "stellenabbau", "zölle", "zoll", "krise", "gewinnwarnung", "minus", "schwäche", "druck", "belastet",
       "abwärts", "tief", "tiefer", "absturz", "einbussen", "enttäuscht", "enttäuscht")
POS = POS + ("legt", "zulegen", "gewinne", "rekordhoch", "erhöht", "kursziel", "plus", "aufwärts", "höher",
             "kaufempfehlung", "wachstum", "zuversichtlich", "übertrifft", "überzeugt", "rally", "hoch")


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
        c = num(r["Close"], 4)
        if c is None or c <= 0:
            continue
        o = num(r.get("Open"), 4) or c
        h = num(r.get("High"), 4) or max(o, c)
        l = num(r.get("Low"), 4) or min(o, c)
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


def google_news(query, sym, limit=6):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query + " when:7d", "hl": "de-CH", "gl": "CH", "ceid": "CH:de"})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (kurswerk-terminal)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        src_el = it.find("source")
        src = (src_el.text or "").strip() if src_el is not None else "Google News"
        if src and title.endswith(" - " + src):
            title = title[: -len(" - " + src)]
        try:
            ts = int(parsedate_to_datetime(it.findtext("pubDate")).timestamp() * 1000)
        except Exception:
            continue
        link = (it.findtext("link") or "").strip()
        items.append({"t": ts, "sym": None if sym == "MACRO" else sym, "head": title, "src": src or "Google News",
                      "url": link if link.startswith("https://") else "", "sent": sentiment(title)})
    items.sort(key=lambda n: n["t"], reverse=True)
    return items[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site/data/market.json")
    args = ap.parse_args()

    tickers = list(SYMS.values()) + [FX]
    df = yf.download(tickers, period="2y", interval="1d", group_by="ticker",
                     auto_adjust=False, progress=False, threads=True)

    out = {"updated": int(time.time() * 1000), "fx": None, "instruments": {}, "news": []}
    debug = {"missing": [], "news_errors": []}
    for sym, t in SYMS.items():
        rows = history(df, t)
        if len(rows) < 60:
            for alt in [t] + ALT.get(sym, []):
                try:
                    single = yf.Ticker(alt).history(period="2y", interval="1d", auto_adjust=False)
                    rows = history({alt: single}, alt)
                except Exception as e:
                    debug["news_errors"].append(f"{sym} Einzelabfrage {alt}: {e}"[:200])
                if len(rows) >= 60:
                    break
        if len(rows) >= 60:
            out["instruments"][sym] = rows
        else:
            debug["missing"].append(f"{sym} ({len(rows)} Tage)")
            print(f"Warnung: zu wenig Daten für {sym} ({t}): {len(rows)} Tage", file=sys.stderr)
    fx_rows = history(df, FX)
    if fx_rows:
        out["fx"] = fx_rows[-1][4]

    seen = set()

    def add(n):
        key = n["head"].lower()[:90]
        if n["head"] and key not in seen:
            seen.add(key)
            out["news"].append(n)

    for sym, q in GNEWS.items():
        try:
            for n in google_news(q, sym):
                add(n)
        except Exception as e:
            debug["news_errors"].append(f"Google {sym}: {type(e).__name__}: {e}"[:200])
    if len(out["news"]) < 10:  # Ersatz: Yahoo-News über yfinance
        for sym in NEWS_SYMS:
            try:
                items = yf.Ticker(SYMS[sym]).news or []
            except Exception as e:
                debug["news_errors"].append(f"Yahoo {sym}: {e}"[:200])
                continue
            for it in items[:8]:
                n = parse_news(it, sym)
                if n:
                    add(n)
    out["news"].sort(key=lambda n: n["t"], reverse=True)
    out["news"] = out["news"][:160]
    out["debug"] = debug

    if len(out["instruments"]) < 8:
        sys.exit(f"Abbruch: nur {len(out['instruments'])} Titel geladen, alte Daten bleiben online.")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"OK: {len(out['instruments'])} Titel, {len(out['news'])} News, USD/CHF {out['fx']}, Debug: {debug}")


if __name__ == "__main__":
    main()
