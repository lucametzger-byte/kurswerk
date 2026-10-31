"""Faktoren exakt wie in bt.js / index.html nachgebaut, plus neue Kandidaten."""
import gzip, json, os
import numpy as np
import pandas as pd

NONEQ = {"SMI", "SPX", "DAX", "SX5E", "NDX", "DJI", "SMIM", "XAU", "XAG", "EURCHF", "BTC", "ETH", "SOL"}
EU_SUFFIX = (".DE", ".PA", ".AS", ".L")


def load(path=os.environ.get("HIST", "history.json.gz")):
    j = json.load(gzip.open(path, "rt"))
    return j["data"]


def home_of(sym, ticker_map):
    t = ticker_map.get(sym, "")
    if t.endswith(".SW"):
        return "SMI"
    if t.endswith(EU_SUFFIX):
        return "DAX"
    return "SPX"


def sma(a, n):
    return pd.Series(a).rolling(n).mean().to_numpy()


def ema(a, n):
    k = 2 / (n + 1)
    o = np.empty_like(a)
    e = a[0]
    for i in range(len(a)):
        e = a[i] * k + e * (1 - k) if i else a[0]
        o[i] = e
    return o


def rsi(a, n=14):
    o = np.full(len(a), np.nan)
    g = l = 0.0
    for i in range(1, len(a)):
        d = a[i] - a[i - 1]
        up, dn = max(d, 0), max(-d, 0)
        if i <= n:
            g += up / n; l += dn / n
            if i == n:
                o[i] = 100 - 100 / (1 + g / l) if l else 100
        else:
            g = (g * (n - 1) + up) / n; l = (l * (n - 1) + dn) / n
            o[i] = 100 - 100 / (1 + g / l) if l else 100
    return o


def features(r):
    """r: dict mit d,o,h,l,c. Gibt DataFrame mit allen Faktoren je Tag zurück."""
    C = np.asarray(r["c"], float)
    n = len(C)
    s20, s50, s200 = sma(C, 20), sma(C, 50), sma(C, 200)
    R = rsi(C)
    m = ema(C, 12) - ema(C, 26)
    mh = m - ema(m, 9)
    sd20 = pd.Series(C).rolling(20).std(ddof=0).to_numpy()
    bhi, blo = s20 + 2 * sd20, s20 - 2 * sd20
    lr = np.r_[0, np.diff(np.log(C))]
    vol = pd.Series(lr).rolling(20).std(ddof=1).to_numpy() * np.sqrt(252)
    vol[:21] = np.nan
    vol60 = pd.Series(lr).rolling(60).std(ddof=1).to_numpy() * np.sqrt(252)
    hi252 = pd.Series(C).rolling(252).max().to_numpy()
    v = np.where(np.isnan(vol), .2, vol)
    dist50 = C / s50 - 1
    ret20 = C / np.r_[np.full(20, np.nan), C[:-20]] - 1
    pb = (C - blo) / np.where((bhi - blo) == 0, 1, bhi - blo)
    f = pd.DataFrame(index=pd.to_datetime(r["d"]))
    f["C"] = C
    f["vol"] = v
    # --- heutige Faktoren (identisch zu bt.js) ---
    f["trend"] = np.clip(np.tanh(dist50 / np.maximum(.02, v / 4)) * .75 + np.where(s20 > s50, .25, -.25), -1, 1)
    f["mom"] = np.tanh(ret20 / np.maximum(.02, v / 3.5))
    f["macd"] = np.tanh((mh / C) / (v / np.sqrt(252)) * 1.6)
    f["rsi"] = np.clip((50 - R) / 25, -1, 1) * np.where((R > 70) | (R < 30), 1, .45)
    f["bb"] = np.clip((.5 - pb) * 1.6, -1, 1)
    # --- neue Kandidaten ---
    c21 = np.r_[np.full(21, np.nan), C[:-21]]
    c252 = np.r_[np.full(252, np.nan), C[:-252]]
    vy = np.where(np.isnan(vol60), v, vol60)
    f["mom12"] = np.tanh((c21 / c252 - 1) / np.maximum(.05, vy))
    f["trend200"] = np.tanh((C / s200 - 1) / np.maximum(.05, vy / 2))
    f["high52"] = np.tanh((C / hi252 - .9) / .1)
    f["lowvol"] = np.clip((.30 - vy) / .2, -1, 1)
    ok = np.arange(n) >= 55
    ok &= ~np.isnan(s50) & ~np.isnan(bhi)
    f["ok_old"] = ok
    f["ok_new"] = ok & ~np.isnan(c252) & ~np.isnan(s200)
    return f


def old_score(f):
    raw = (.24 * f.trend + .18 * f.mom + .15 * f.macd + .11 * f.rsi + .07 * f.bb) / .75
    return np.clip(np.round(raw * 155), -100, 100)
