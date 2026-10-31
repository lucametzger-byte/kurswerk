"""Kronos als zweite Meinung testen: Prognose der nächsten 20 Handelstage für alle Aktien.

Nur Stichtage nach dem Ende von Kronos' Trainingsdaten (Pipeline endet 2025-06-05), damit das Modell
die Antworten nicht auswendig kennt. Läuft in GitHub Actions (.github/workflows/kronos.yml), aufgeteilt in Shards.
Ausgabe: CSV mit date, sym, close, kclose (Kronos-Schlusskurs nach 20 Tagen), kmean (Mittel des Pfads).
"""
import argparse
import gzip
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd
import torch

NONEQ = {"SMI", "SPX", "DAX", "SX5E", "NDX", "DJI", "SMIM", "XAU", "XAG", "EURCHF", "BTC", "ETH", "SOL"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hist", default="history.json.gz")
    ap.add_argument("--kronos", default="kronos-src")
    ap.add_argument("--model", default="NeoQuasar/Kronos-small")
    ap.add_argument("--tokenizer", default="NeoQuasar/Kronos-Tokenizer-base")
    ap.add_argument("--lookback", type=int, default=256)
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--start", default="2025-07-01")
    ap.add_argument("--end", default="2026-09-25")
    ap.add_argument("--step", type=int, default=10)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--out", default="kronos.csv")
    a = ap.parse_args()

    sys.path.insert(0, a.kronos)
    from model import Kronos, KronosTokenizer, KronosPredictor

    torch.manual_seed(42)
    np.random.seed(42)
    torch.set_num_threads(os.cpu_count() or 4)
    tok = KronosTokenizer.from_pretrained(a.tokenizer)
    mdl = Kronos.from_pretrained(a.model)
    pred = KronosPredictor(mdl, tok, device="cpu", max_context=512)

    data = json.load(gzip.open(a.hist, "rt"))["data"]
    frames = {}
    for s, r in data.items():
        if s in NONEQ:
            continue
        df = pd.DataFrame({"open": r["o"], "high": r["h"], "low": r["l"], "close": r["c"], "volume": r["v"]},
                          index=pd.to_datetime(r["d"]))
        frames[s] = df[~df.index.duplicated()]

    cal = pd.to_datetime(data["SPX"]["d"])
    cal = cal[(cal >= a.start) & (cal <= a.end)][:: a.step]
    mine = [d for k, d in enumerate(cal) if k % a.shards == a.shard]
    print(f"Shard {a.shard}/{a.shards}: {len(mine)} Stichtage", flush=True)

    rows = []
    for d in mine:
        t0 = time.time()
        dfs, xts, yts, syms, last = [], [], [], [], []
        for s, df in frames.items():
            h = df[df.index <= d]
            if len(h) < a.lookback or (d - h.index[-1]).days > 5:
                continue
            h = h.iloc[-a.lookback:]
            dfs.append(h.reset_index(drop=True))
            xts.append(pd.Series(h.index))
            yts.append(pd.Series(pd.bdate_range(h.index[-1] + pd.Timedelta(days=1), periods=20)))
            syms.append(s)
            last.append(float(h.close.iloc[-1]))
        with torch.no_grad():
            out = pred.predict_batch(dfs, xts, yts, pred_len=20, T=1.0, top_p=0.9,
                                     sample_count=a.samples, verbose=False)
        for s, c, p in zip(syms, last, out):
            rows.append({"date": d.strftime("%Y-%m-%d"), "sym": s, "close": c,
                         "kclose": float(p["close"].iloc[-1]), "kmean": float(p["close"].mean())})
        print(f"{d.date()}: {len(syms)} Titel in {time.time() - t0:.0f} s", flush=True)
        pd.DataFrame(rows).to_csv(a.out, index=False)  # Zwischenstand, falls der Job abbricht
    pd.DataFrame(rows).to_csv(a.out, index=False)
    print("fertig", len(rows))


if __name__ == "__main__":
    main()
