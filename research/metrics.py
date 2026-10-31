import numpy as np
import pandas as pd


def ic(P, col, y="xs"):
    """Mittlere Rang-Korrelation pro Stichtag (welche Aktien schlagen die anderen?)."""
    g = P.groupby(level=0)
    v = g.apply(lambda d: d[col].rank().corr(d[y].rank()) if len(d) >= 10 else np.nan).dropna()
    return v.mean(), v.mean() / v.std() * np.sqrt(len(v)), v


def buckets(P, col):
    b = pd.cut(P[col], [-101, -40, -15, 15, 30, 40, 101],
               labels=["≤-40", "-40..-15", "-15..15", "15..30", "30..40", "≥40"])
    t = P.groupby(b, observed=True).agg(n=("fwd", "size"), ret=("fwd", "mean"), hit=("fwd", lambda x: (x > 0).mean()),
                                          xs=("xs", "mean"))
    t["ret"] = (np.exp(t["ret"]) - 1) * 100
    t["xs"] = t["xs"] * 100
    t["hit"] *= 100
    return t.round(2)


def spread(P, col):
    """Top-20 % minus Bottom-20 % je Stichtag, annualisiert (5-Tage-Raster, 20-Tage-Rendite)."""
    def one(d):
        if len(d) < 10:
            return np.nan
        q = d[col].rank(pct=True)
        return d.loc[q >= .8, "xs"].mean() - d.loc[q <= .2, "xs"].mean()
    s = P.groupby(level=0).apply(one).dropna()
    return s.mean() * 252 / 20 * 100


def report(P, col, name):
    m, t, v = ic(P, col)
    print(f"\n== {name} ==  IC {m:.4f} (t={t:.1f})   Top-Bottom-Spread {spread(P, col):.2f} %/Jahr")
    print(f"Korrelation Score↔20T-Rendite (gepoolt): {P[col].corr(P.fwd):.4f}")
    print(buckets(P, col).to_string())
    return v
