"""Baut das Mess-Panel: alle Aktien, jeder 5. Handelstag, Faktoren + künftige 20-Tage-Rendite."""
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from feat import load, features, old_score, home_of, NONEQ

# fetch_history importiert yfinance; Ticker-Tabelle daher direkt aus dem Quelltext lesen
src = open(os.path.join(ROOT, "scripts/fetch_data.py")).read()
ns = {}
exec(src[src.index("SYMS = {"):src.index("FX = ")], ns)
src2 = open(os.path.join(ROOT, "scripts/fetch_history.py")).read()
exec(src2[src2.index("EXTRA = {"):src2.index("def num")], ns)
TICK = {**ns["SYMS"], **ns["EXTRA"]}

H = 20  # Haltedauer in Handelstagen


def build():
    data = load()
    idx = {}
    for b in ("SMI", "SPX", "DAX"):
        c = pd.Series(data[b]["c"], index=pd.to_datetime(data[b]["d"]))
        s200 = c.rolling(200).mean()
        idx[b] = pd.DataFrame({"c": c, "reg": np.tanh((c / s200 - 1) / .05),
                               "fwd": np.log(c.shift(-(H + 1)) / c.shift(-1))})
    rows = []
    for s, r in data.items():
        if s in NONEQ:
            continue
        f = features(r)
        f["old"] = old_score(f)
        C = f.C
        f["fwd"] = np.log(C.shift(-(H + 1)) / C.shift(-1))  # Kauf am nächsten Tag, 20 Tage halten
        b = home_of(s, TICK)
        f = f.join(idx[b][["reg", "fwd"]].rename(columns={"fwd": "mfwd"}), how="left")
        f["reg"] = f["reg"].ffill()
        f["xs"] = f["fwd"] - f["mfwd"]
        f["sym"] = s
        f["home"] = b
        f["terminal"] = bool(r.get("terminal"))
        f = f.iloc[::5]
        f = f[f.ok_new & f.fwd.notna() & f.reg.notna()]
        rows.append(f)
    P = pd.concat(rows)
    P = P[P.index >= "1991-01-01"]
    P = P[P["xs"].notna()]  # Tage ohne Heimmarkt-Kurs
    P["year"] = P.index.year
    return P


if __name__ == "__main__":
    P = build()
    P.to_pickle("panel.pkl")
    print(P.shape, P.sym.nunique(), P.index.min(), P.index.max())
    print(P.groupby("year").sym.nunique().to_string())
