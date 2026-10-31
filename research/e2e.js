const fs=require("fs");const {KWBT,H,rowsOf}=require("./load.js");
const src=fs.readFileSync("../scripts/bot.mjs","utf8");
const GRP=eval("("+src.match(/const GRP = (\{[^}]*\})/)[1]+")");
KWBT.MODEL.wf=JSON.parse(fs.readFileSync("wf_weights.json"));
const terminal=Object.keys(H).filter(s=>H[s].terminal&&GRP[s]);
function insts(from,to){const o={};for(const s of terminal){const r=rowsOf(s).filter(x=>x[0]<=to&&x[0]>=from);if(r.length>300)o[s]={rows:r,grp:GRP[s],fx:1}}return o}
const W=[["2000-01-01","2026-10-31"],["2000-01-01","2009-12-31"],["2010-01-01","2019-12-31"],["2020-01-01","2026-10-31"],["2024-10-01","2026-10-31"]];
const pc=x=>(x*100).toFixed(1).padStart(7);
for(const [a,b] of W){
  // 1 Jahr Vorlauf für die Indikatoren
  const pre=String(+a.slice(0,4)-2)+a.slice(4),I=insts(pre,b);
  const res={};
  for(const [name,on] of [["alt",false],["neu",true]]){KWBT.setModel(on);
    for(const k in I)delete I[k].P;
    const c=KWBT.run(I,KWBT.V2,100000,a),r=KWBT.runRot(I,KWBT.V3,a);
    res["Kern "+name]=KWBT.stats(c.eq,c.closed,c.fees);res["Rot "+name]=KWBT.stats(r.eq,r.closed,r.fees)}
  const dates=KWBT.run(I,{...KWBT.V2,entry:999},100000,a).eq.map(e=>e[0]);
  res["SMI halten"]=KWBT.stats(KWBT.hold(I,["SMI"],dates));
  console.log(`\n${a} – ${b}  (${Object.keys(I).length} Titel)`);
  console.log("Strategie        Rendite  MaxVerl  Sharpe Trades Treffer");
  for(const k in res){const s=res[k];console.log(k.padEnd(14),pc(s.ret),pc(s.mdd),s.sharpe.toFixed(2).padStart(7),String(s.trades??"").padStart(6),s.win!=null?pc(s.win):"")}
}
