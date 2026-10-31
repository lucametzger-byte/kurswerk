"""Holt die komplette Kurshistorie (so weit Yahoo zurückreicht) für das Training des Analyse-Modells.

Läuft wöchentlich über .github/workflows/history.yml und landet im Branch history-data.
Neben den Terminal-Titeln wird ein grösseres Trainings-Universum geladen, damit das Modell
auf möglichst vielen Aktien und Marktphasen (Dotcom, 2008, Corona) geprüft werden kann.
Kurse sind dividenden- und splitbereinigt (auto_adjust=True), damit Renditen stimmen.
"""
import argparse
import gzip
import json
import math
import sys
import time

import yfinance as yf

from fetch_data import SYMS, ALT

# zusätzliche Titel nur fürs Training (nicht im Terminal sichtbar)
EXTRA = {
    # Schweiz
    "BALN": "BALN.SW", "BAER": "BAER.SW", "BARN": "BARN.SW", "CLN": "CLN.SW", "EMSN": "EMSN.SW",
    "FHZN": "FHZN.SW", "HELN": "HELN.SW", "LISN": "LISN.SW", "SGSN": "SGSN.SW", "SCHP": "SCHP.SW",
    "STMN": "STMN.SW", "TEMN": "TEMN.SW", "VACN": "VACN.SW", "ADEN": "ADEN.SW", "SPSN": "SPSN.SW",
    "PSPN": "PSPN.SW", "SUN": "SUN.SW", "BUCN": "BUCN.SW", "GF": "GF.SW", "SQN": "SQN.SW",
    "SMIM": "^SMIM",
    # USA
    "XOM": "XOM", "CVX": "CVX", "PG": "PG", "JNJ": "JNJ", "PFE": "PFE", "MRK": "MRK", "WMT": "WMT",
    "HD": "HD", "MCD": "MCD", "IBM": "IBM", "INTC": "INTC", "CSCO": "CSCO", "ORCL": "ORCL",
    "QCOM": "QCOM", "TXN": "TXN", "ADBE": "ADBE", "CAT": "CAT", "DE": "DE", "BA": "BA", "MMM": "MMM",
    "GE": "GE", "HON": "HON", "LMT": "LMT", "UNH": "UNH", "ABT": "ABT", "AMGN": "AMGN", "GILD": "GILD",
    "BMY": "BMY", "LLY": "LLY", "PEP": "PEP", "MO": "MO", "CL": "CL", "KMB": "KMB", "NKE": "NKE",
    "SBUX": "SBUX", "COST": "COST", "TGT": "TGT", "LOW": "LOW", "BAC": "BAC", "WFC": "WFC", "C": "C",
    "GS": "GS", "MS": "MS", "AXP": "AXP", "USB": "USB", "T": "T", "VZ": "VZ", "CMCSA": "CMCSA",
    "UPS": "UPS", "FDX": "FDX", "UNP": "UNP", "NEE": "NEE", "DUK": "DUK", "SO": "SO", "EMR": "EMR",
    "ITW": "ITW", "GD": "GD", "NOC": "NOC", "RTX": "RTX", "DHR": "DHR", "TMO": "TMO", "MDT": "MDT",
    "SYK": "SYK", "ADP": "ADP", "MU": "MU", "AMAT": "AMAT", "LRCX": "LRCX", "KLAC": "KLAC", "ADI": "ADI",
    "NDX": "^NDX", "DJI": "^DJI",
    # Europa
    "SAP": "SAP.DE", "SIE": "SIE.DE", "ALV": "ALV.DE", "BAS": "BAS.DE", "BAYN": "BAYN.DE", "MBG": "MBG.DE",
    "BMW": "BMW.DE", "DTE": "DTE.DE", "MC": "MC.PA", "OR": "OR.PA", "SAN": "SAN.PA", "TTE": "TTE.PA",
    "AIR": "AIR.PA", "ASML": "ASML.AS", "ULVR": "ULVR.L", "SHEL": "SHEL.L", "AZN": "AZN.L",
    "HSBA": "HSBA.L", "BP": "BP.L", "GSK": "GSK.L", "DAX": "^GDAXI", "SX5E": "^STOXX50E",
}


def num(x, nd):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return round(v, nd)


def columns(d):
    d = d.dropna(subset=["Close"])
    out = {"d": [], "o": [], "h": [], "l": [], "c": [], "v": []}
    for ts, r in d.iterrows():
        c = num(r["Close"], 6)
        if c is None or c <= 0:
            continue
        o = num(r.get("Open"), 6) or c
        h = num(r.get("High"), 6) or max(o, c)
        l = num(r.get("Low"), 6) or min(o, c)
        out["d"].append(ts.strftime("%Y-%m-%d"))
        out["o"].append(o)
        out["h"].append(max(h, o, c))
        out["l"].append(min(l, o, c))
        out["c"].append(c)
        out["v"].append(num(r.get("Volume"), 0) or 0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="history.json.gz")
    args = ap.parse_args()

    universe = {**SYMS, **EXTRA}
    terminal = set(SYMS)
    items = list(universe.items())
    data, missing = {}, []
    for k in range(0, len(items), 30):
        chunk = items[k:k + 30]
        tickers = [t for _, t in chunk]
        df = yf.download(tickers, period="max", interval="1d", group_by="ticker",
                         auto_adjust=True, progress=False, threads=True)
        for sym, t in chunk:
            try:
                rows = columns(df[t])
            except KeyError:
                rows = {"c": []}
            if len(rows["c"]) < 300:
                for alt in [t] + ALT.get(sym, []):
                    try:
                        rows = columns(yf.Ticker(alt).history(period="max", interval="1d", auto_adjust=True))
                    except Exception as e:
                        print(f"{sym} {alt}: {e}", file=sys.stderr)
                    if len(rows["c"]) >= 300:
                        break
            if len(rows["c"]) >= 300:
                rows["terminal"] = sym in terminal
                data[sym] = rows
            else:
                missing.append(sym)
        time.sleep(2)

    meta = {"updated": int(time.time() * 1000), "count": len(data), "missing": missing,
            "first": {s: v["d"][0] for s, v in data.items()}}
    with gzip.open(args.out, "wt", encoding="utf-8") as f:
        json.dump({"meta": meta, "data": data}, f, separators=(",", ":"))
    print(f"{len(data)} Titel gespeichert, fehlend: {missing}")


if __name__ == "__main__":
    main()
