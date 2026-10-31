// Master-Bot: handelt mit Spielgeld nach "Signal + Kern" und läuft bei jedem Workflow-Lauf auf GitHub.
// Nutzt dieselbe Logik wie Terminal und Backtest (bt.js). Zustand: state/bot.json (Branch bot-state).
import fs from "node:fs";
import path from "node:path";

const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? process.argv[i + 1] : d; };
const DATA = arg("data", "site/data/market.json"), STATE = arg("state", "state/bot.json"), OUT = arg("out", "site/data/bot.json");
const KWBT = new Function(fs.readFileSync(new URL("../bt.js", import.meta.url), "utf8") + ";return KWBT;")();

const GRP = { NESN: "ch", NOVN: "ch", ROG: "ch", UBSG: "ch", ABBN: "ch", ZURN: "ch", LOGN: "ch", AAPL: "us", NVDA: "us", MSFT: "us", TSLA: "us", SMI: "x", SPX: "x", BTC: "x", XAU: "x", EURCHF: "x", SREN: "ch", CFR: "ch", GIVN: "ch", LONN: "ch", SIKA: "ch", HOLN: "ch", ALC: "ch", GEBN: "ch", SCMN: "ch", PGHN: "ch", SLHN: "ch", KNIN: "ch", SOON: "ch", UHR: "ch", AMZN: "us", GOOGL: "us", META: "us", NFLX: "us", AMD: "us", JPM: "us", V: "us", KO: "us", DIS: "us", PLTR: "us", ETH: "x", SOL: "x", XAG: "x" };
const CHF = new Set(["NESN", "NOVN", "ROG", "UBSG", "ABBN", "ZURN", "LOGN", "SMI", "EURCHF", "SREN", "CFR", "GIVN", "LONN", "SIKA", "HOLN", "ALC", "GEBN", "SCMN", "PGHN", "SLHN", "KNIN", "SOON", "UHR"]);
const START = 100000;
const CRYPTO = new Set(["BTC", "ETH", "SOL"]);
const hsOf = s => CRYPTO.has(s) ? .001 : GRP[s] === "x" ? .0003 : .0005;
const qdOf = s => ({ BTC: 4, ETH: 3, SOL: 2, XAU: 2 })[s] || 0;
const floorQ = (x, s) => { const m = 10 ** qdOf(s); return Math.max(0, Math.floor(x * m + 1e-9) / m); };
const r2 = x => Math.round(x * 100) / 100;

const data = JSON.parse(fs.readFileSync(DATA, "utf8"));
let st;
try { st = JSON.parse(fs.readFileSync(STATE, "utf8")); } catch { st = null; }
const now = data.updated || Date.now();
const fx = s => CHF.has(s) ? 1 : (+data.fx > 0 ? +data.fx : 0.8);

const syms = Object.keys(data.instruments).filter(s => GRP[s] && data.instruments[s].length >= 60);
const view = {};
for (const s of syms) {
  const rows = data.instruments[s], P = KWBT.prep(rows), i = rows.length - 1;
  view[s] = { s, P, i, grp: GRP[s], fx: fx(s), price: P.C[i], date: rows[i][0] };
}
const bench = view.SMI || view[syms[0]];
if (!st) st = { started: now, startBench: bench.price, cash: START, pos: {}, tx: [], eq: [], cool: {}, lastData: 0 };

const value = () => { let v = st.cash; for (const k in st.pos) if (view[k]) v += st.pos[k].q * view[k].price * view[k].fx; return v; };
let traded = false;

if (data.updated !== st.lastData) {
  for (const k in st.pos) if (view[k]) st.pos[k].hi = Math.max(st.pos[k].hi || view[k].price, view[k].price);
  const lastD = bench.date;
  const ctx = {
    V: value(), cash: st.cash, lastD, cool: st.cool,
    syms: syms.map(s => {
      const x = view[s];
      return { ...x, sc: KWBT.trendScore(x.P, x.i, KWBT.newsV(s, data.news, now)), held: st.pos[s] ? { ...st.pos[s], auto: true } : null };
    }),
  };
  // Nur Titel handeln, deren Börse gerade offen ist (sonst wäre der Kurs alt, z.B. am Wochenende)
  const runTs = Date.now();
  const orders = KWBT.coreDecide(ctx, KWBT.V2).filter(o => KWBT.isOpen(KWBT.sessionOf(o.s, GRP[o.s]), runTs));
  for (const side of ["sell", "buy"]) for (const o of orders.filter(o => o.side === side)) {
    const x = view[o.s], hs = hsOf(o.s);
    if (side === "sell") {
      const p = st.pos[o.s]; if (!p) continue;
      const px = x.price * (1 - hs), g = p.q * px * x.fx, f = KWBT.feeOf(g), pl = g - f - p.cost;
      st.cash += g - f; delete st.pos[o.s]; if (o.cool) st.cool[o.s] = lastD;
      st.tx.unshift({ t: now, sym: o.s, side, q: p.q, px: +px.toFixed(4), chf: r2(g), fee: r2(f), pl: r2(pl), why: o.why });
    } else {
      const px = x.price * (1 + hs), amt = Math.min(o.amt, st.cash - 50), q = floorQ((amt - KWBT.feeOf(amt)) / (px * x.fx), o.s);
      if (q <= 0) continue;
      const g = q * px * x.fx, f = KWBT.feeOf(g); if (g + f > st.cash) continue;
      st.cash -= g + f;
      st.pos[o.s] = { q, cost: g + f, px: +px.toFixed(4), hi: x.price, core: !!o.core, since: now };
      st.tx.unshift({ t: now, sym: o.s, side, q, px: +px.toFixed(4), chf: r2(g), fee: r2(f), pl: null, why: o.why });
    }
    traded = true;
  }
  st.tx = st.tx.slice(0, 300);
  st.lastData = data.updated;
}

// Verlauf: höchstens ein Punkt pro Stunde, dazu jeder Lauf mit Trades
const V = value(), last = st.eq[st.eq.length - 1];
let appended = false;
if (traded || !last || now - last[0] >= 55 * 60e3) {
  appended = true;
  st.eq.push([now, r2(V), +bench.price.toFixed(2)]);
  if (st.eq.length > 6000) st.eq.splice(0, st.eq.length - 6000);
}
st.cash = r2(st.cash);
st.updated = now;

// Zustand nur bei Trades oder neuem Verlaufspunkt speichern (höchstens etwa stündlich ein Commit)
if (traded || appended) {
  fs.mkdirSync(path.dirname(STATE), { recursive: true });
  fs.writeFileSync(STATE, JSON.stringify(st));
}
const pub = { ...st, value: r2(V), fx: data.fx, strategy: "Signal + Kern", prices: Object.fromEntries(Object.keys(st.pos).map(k => [k, view[k] ? view[k].price : null])) };
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(pub));
console.log(`Master-Bot: Wert CHF ${r2(V)}, Cash ${st.cash}, Positionen ${Object.keys(st.pos).join(", ") || "keine"}${traded ? ", neue Trades: " + st.tx.filter(t => t.t === now).map(t => t.side + " " + t.sym).join(", ") : ""}`);
