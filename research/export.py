"""Finales Modell + Kalibrierung exportieren (für bt.js)."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from wf import NEW, target, walk

P = pd.read_pickle("panel.pkl")
cut = P.index.max() - pd.Timedelta(days=35)
tr = P[P.index < cut]
m = Ridge(alpha=50).fit(tr[NEW].to_numpy(), target(tr, "xs").to_numpy())
ptr = m.predict(tr[NEW].to_numpy())
k = float(tr.old.std() / ptr.std())

# Kalibrierung nur aus echten Testjahren (Walk-Forward, nie gesehene Daten)
Q = P[P.year >= 2000].copy()
Q["sc"] = walk(P, NEW, "xs", "ridge")
edges = [-101, -60, -40, -20, 0, 20, 40, 60, 101]
Q["b"] = pd.cut(Q.sc, edges, labels=False, right=False)
cal = []
for b, d in Q.groupby("b"):
    cal.append({"lo": edges[int(b)], "n": int(len(d)), "hit": round(float((d.fwd > 0).mean()), 4),
                "ret": round(float(np.exp(d.fwd.mean()) - 1), 5), "xs": round(float(d["xs"].mean()), 5),
                "beat": round(float((d["xs"] > 0).mean()), 4)})
base = {"n": int(len(Q)), "hit": round(float((Q.fwd > 0).mean()), 4), "ret": round(float(np.exp(Q.fwd.mean()) - 1), 5),
        "beat": round(float((Q["xs"] > 0).mean()), 4)}
out = {"v": 1, "trained": str(cut.date()), "from": str(P.index.min().date()), "stocks": int(P.sym.nunique()),
       "samples": int(len(tr)), "feats": NEW, "w": [round(float(x), 5) for x in m.coef_],
       "b": round(float(ptr.mean() - m.intercept_), 6), "k": round(k, 3), "h": 20, "cal": cal, "base": base,
       "test": "2000-" + str(P.year.max())}
json.dump(out, open("model.json", "w"), separators=(",", ":"))
print(json.dumps(out, indent=1)[:2500])
