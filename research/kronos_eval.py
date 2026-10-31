"""Kronos-Prognosen (kronos_*.csv) gegen das Analyse-Modell auf denselben Titeln und Stichtagen messen."""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from feat import load, features, old_score, home_of  # noqa: E402
from panel import TICK, H  # noqa: E402
from wf import NEW, target  # noqa: E402

K = pd.concat(pd.read_csv(f) for f in sorted(glob.glob(os.environ.get("KRONOS", "kronos_*.csv"))))
K["date"] = pd.to_datetime(K.date)
K["kret"] = np.log(K.kclose / K.close)
K["kmret"] = np.log(K.kmean / K.close)
print("Kronos-Prognosen:", len(K), "Stichtage:", K.date.nunique(), "Titel:", K.sym.nunique())

data = load()
idx = {}
for b in ("SMI", "SPX", "DAX"):
    c = pd.Series(data[b]["c"], index=pd.to_datetime(data[b]["d"]))
    idx[b] = pd.DataFrame({"reg": np.tanh((c / c.rolling(200).mean() - 1) / .05),
                           "mfwd": np.log(c.shift(-(H + 1)) / c.shift(-1))})

rows = []
for s, g in K.groupby("sym"):
    f = features(data[s])
    f["old"] = old_score(f)
    f["fwd"] = np.log(f.C.shift(-(H + 1)) / f.C.shift(-1))
    f = f.join(idx[home_of(s, TICK)], how="left")
    f["reg"] = f["reg"].ffill()
    f["xs"] = f["fwd"] - f["mfwd"]
    for _, r in g.iterrows():
        h = f[f.index <= r.date]
        if not len(h):
            continue
        x = h.iloc[-1].copy()
        x["sym"], x["date"], x["kret"], x["kmret"] = s, r.date, r.kret, r.kmret
        rows.append(x)
D = pd.DataFrame(rows).dropna(subset=["fwd", "xs"] + NEW)
print("auswertbar:", len(D))

# Analyse-Modell mit Gewichten nur aus der Zeit vor dem jeweiligen Jahr (wie Kronos: kein Blick nach vorn)
P = pd.read_pickle("panel.pkl")
for Y in sorted(D.date.dt.year.unique()):
    tr = P[P.index < pd.Timestamp(f"{Y}-01-01") - pd.Timedelta(days=35)]
    m = Ridge(alpha=50).fit(tr[NEW].to_numpy(), target(tr, "xs").to_numpy())
    sel = D.date.dt.year == Y
    D.loc[sel, "model"] = m.predict(D.loc[sel, NEW].to_numpy())


def zs(col):
    return D.groupby("date")[col].transform(lambda v: (v - v.mean()) / (v.std() or 1))


D["combo"] = zs("model") + zs("kret")


def ic(col, y="xs"):
    v = D.groupby("date").apply(lambda d: d[col].rank().corr(d[y].rank())).dropna()
    return v.mean(), v.mean() / v.std() * np.sqrt(len(v)), (v > 0).mean()


def topbot(col):
    def one(d):
        q = d[col].rank(pct=True)
        return d.loc[q >= .8, "xs"].mean() - d.loc[q <= .2, "xs"].mean()
    return D.groupby("date").apply(one).mean() * 100


print(f"\nZeitraum {D.date.min().date()} bis {D.date.max().date()}, {D.date.nunique()} Stichtage, je ~{len(D)//D.date.nunique()} Aktien")
print("Signal            IC      t     Stichtage>0   Top-Flop je 20 Tage")
res = {}
for c, name in [("old", "Trendsignal (alt)"), ("model", "Analyse-Modell"), ("kret", "Kronos Endkurs"),
                ("kmret", "Kronos Pfadmittel"), ("combo", "Modell + Kronos")]:
    m, t, p = ic(c)
    res[c] = {"ic": m, "t": t, "pos": p, "tb": topbot(c)}
    print(f"{name:18s} {m:+.4f}  {t:+5.2f}   {p*100:5.1f} %       {topbot(c):+.2f} %")
print("\nKorrelation Kronos ↔ Modell:", round(D[["kret", "model"]].corr().iloc[0, 1], 3),
      "| Kronos ↔ 1-Monats-Momentum:", round(D[["kret", "mom"]].corr().iloc[0, 1], 3))
json.dump(res, open("kronos_result.json", "w"), indent=1)
