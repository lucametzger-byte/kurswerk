"""Walk-Forward: für jedes Testjahr nur mit Daten davor lernen (35 Tage Sperrfrist wegen 20-Tage-Ziel)."""
import sys
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from metrics import report, ic

OLD = ["trend", "mom", "macd", "rsi", "bb"]
NEW = OLD + ["mom12", "trend200", "high52", "lowvol", "reg"]


def target(P, kind):
    s = P.vol.clip(.08, 1.5) * np.sqrt(21 / 252)
    y = P["fwd"] if kind == "abs" else P["xs"]
    return (y / s).clip(-3, 3)


def walk(P, feats, kind="abs", model="ridge", start=2000, alpha=50.0):
    out = []
    for Y in range(start, P.year.max() + 1):
        cut = pd.Timestamp(f"{Y}-01-01") - pd.Timedelta(days=35)
        tr, te = P[P.index < cut], P[P.year == Y]
        if not len(te):
            continue
        X, y = tr[feats].to_numpy(), target(tr, kind).to_numpy()
        if model == "ridge":
            m = Ridge(alpha=alpha).fit(X, y)
        else:
            m = HistGradientBoostingRegressor(max_depth=3, max_iter=150, learning_rate=.05,
                                              min_samples_leaf=400, l2_regularization=1.0).fit(X, y)
        ptr = m.predict(X)
        k = tr.old.std() / ptr.std()
        sc = np.clip(np.round((m.predict(te[feats].to_numpy()) - ptr.mean()) * k), -100, 100)
        out.append(pd.Series(sc, index=te.index))
    return pd.concat(out).to_numpy()


if __name__ == "__main__":
    P = pd.read_pickle("panel.pkl")
    Q = P[P.year >= 2000].copy()
    for name, feats, kind, model in [("alte Faktoren, gelernt", OLD, "abs", "ridge"),
                                     ("neue Faktoren, gelernt (abs)", NEW, "abs", "ridge"),
                                     ("neue Faktoren, gelernt (vs Markt)", NEW, "xs", "ridge"),
                                     ("neue Faktoren, Boosting", NEW, "abs", "gbm")]:
        Q[name] = walk(P, feats, kind, model)
        report(Q, name, name + " | nur Testjahre 2000-2026")
    Q.to_pickle("oos.pkl")
