/* Kurswerk Backtest: spielt Autopilot-Strategien Tag für Tag auf historischen Tageskerzen nach.
   Signal zum Schlusskurs von Tag t, Ausführung zum Eröffnungskurs des nächsten Handelstags des Titels.
   Spread und Courtage wie im Depot. Keine historischen News -> News-Faktor fehlt, übrige Faktoren werden hochgewichtet. */
const KWBT=(()=>{
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
function sma(a,n){const o=new Array(a.length).fill(null);let s=0;for(let i=0;i<a.length;i++){s+=a[i];if(i>=n)s-=a[i-n];if(i>=n-1)o[i]=s/n}return o}
function ema(a,n){const k=2/(n+1),o=[];let e=a[0];for(let i=0;i<a.length;i++){e=i?a[i]*k+e*(1-k):a[0];o.push(e)}return o}
function rsi(a,n=14){const o=new Array(a.length).fill(null);let g=0,l=0;for(let i=1;i<a.length;i++){const d=a[i]-a[i-1],up=Math.max(d,0),dn=Math.max(-d,0);if(i<=n){g+=up/n;l+=dn/n;if(i===n)o[i]=l?100-100/(1+g/l):100}else{g=(g*(n-1)+up)/n;l=(l*(n-1)+dn)/n;o[i]=l?100-100/(1+g/l):100}}return o}
function sd(a){const m=a.reduce((x,y)=>x+y,0)/a.length;return Math.sqrt(a.reduce((x,y)=>x+(y-m)**2,0)/Math.max(1,a.length-1))}
const HS={ch:.0005,us:.0005,x:.0003};
const feeOf=v=>clamp(v*.001,5,40);

function prep(rows){
  const D=rows.map(r=>r[0]),O=rows.map(r=>r[1]),H=rows.map(r=>r[2]),L=rows.map(r=>r[3]),C=rows.map(r=>r[4]);
  const s20=sma(C,20),s50=sma(C,50),R=rsi(C),e12=ema(C,12),e26=ema(C,26),m=C.map((_,i)=>e12[i]-e26[i]),sg=ema(m,9),mh=m.map((x,i)=>x-sg[i]);
  const bb=C.map((_,i)=>{if(s20[i]==null)return null;let v=0;for(let j=i-19;j<=i;j++)v+=(C[j]-s20[i])**2;const s=Math.sqrt(v/20);return{hi:s20[i]+2*s,lo:s20[i]-2*s}});
  const lr=C.map((c,i)=>i?Math.log(c/C[i-1]):0);
  const vol=C.map((_,i)=>i<21?null:sd(lr.slice(i-19,i+1))*Math.sqrt(252));
  const tr=C.map((c,i)=>i?Math.max(H[i]-L[i],Math.abs(H[i]-C[i-1]),Math.abs(L[i]-C[i-1])):H[i]-L[i]);
  return{D,O,H,L,C,s20,s50,s100:sma(C,100),R,mh,bb,vol,atr:sma(tr,14)};
}
/* gleiche Faktor-Formeln wie das Analyse-Modell im Terminal; newsV=null -> ohne News, Gewichte hochskaliert */
function score(P,i,newsV){
  if(i<55||P.s50[i]==null||P.bb[i]==null)return null;
  const p=P.C[i],vol20=P.vol[i]||.2,dist50=p/P.s50[i]-1,ret20=p/P.C[i-20]-1,b=P.bb[i],pb=(p-b.lo)/((b.hi-b.lo)||1),rv=P.R[i],hN=P.mh[i]/p;
  const f=[[.24,clamp(Math.tanh(dist50/Math.max(.02,vol20/4))*.75+(P.s20[i]>P.s50[i]?.25:-.25),-1,1)],[.18,Math.tanh(ret20/Math.max(.02,vol20/3.5))],
    [.15,Math.tanh(hN/(vol20/Math.sqrt(252))*1.6)],[.11,clamp((50-rv)/25,-1,1)*(rv>70||rv<30?1:.45)],[.07,clamp((.5-pb)*1.6,-1,1)]];
  if(newsV!=null)f.push([.25,newsV]);
  let raw=f.reduce((a,[w,v])=>a+w*v,0);if(newsV==null)raw/=.75;
  const sg=f.filter(x=>Math.abs(x[1])>.15).map(x=>Math.sign(x[1])),agree=sg.length?Math.abs(sg.reduce((a,b)=>a+b,0))/sg.length:0;
  return{score:Math.round(clamp(raw*155,-100,100)),conf:clamp(.35+.5*agree-Math.max(0,vol20-.35)*.6,.1,.95),vol:vol20};
}

/* Strategie-Parameter */
const V1={name:"Autopilot alt",entry:40,minConf:.5,exit:-15,confirm:false,regime:false,stopATR:0,maxW:.08,risk:0,maxPos:8,cool:0,ownOnly:false,skip:[]};
const V2={name:"Autopilot neu",entry:30,minConf:.45,exit:-10,confirm:true,regime:true,stopATR:3,maxW:.15,risk:.0035,maxPos:8,cool:3,ownOnly:true,skip:["EURCHF","SPX"],core:{sym:"SMI",w:.5,buf:.02}};
const BENCH_OF={ch:"SMI",us:"SPX"};

/* insts: {sym:{rows,grp,fx}} */
function run(insts,cfg,startCash=100000,startDate=""){
  const syms=Object.keys(insts),P={};for(const s of syms)P[s]=prep(insts[s].rows);
  const dates=[...new Set(syms.flatMap(s=>P[s].D))].sort();
  const ptr={};for(const s of syms)ptr[s]=-1;
  let cash=startCash,fees=0;const pos={},pend={},lastExit={},eq=[],closed=[];let lastSc={};
  const startDi=Math.max(60,dates.findIndex(d=>d>=(P.SMI||P[syms[0]]).D[60]));
  const priceNow=s=>ptr[s]>=0?P[s].C[ptr[s]]:null;
  const value=()=>{let v=cash;for(const s in pos)v+=pos[s].q*priceNow(s)*insts[s].fx;return v};
  for(let di=0;di<dates.length;di++){
    const d=dates[di];const today=[];
    for(const s of syms){const p=P[s];while(ptr[s]+1<p.D.length&&p.D[ptr[s]+1]<=d)ptr[s]++;if(ptr[s]>=0&&p.D[ptr[s]]===d)today.push(s)}
    if(di<startDi||d<startDate)continue;
    // 1) offene Aufträge zum heutigen Eröffnungskurs ausführen
    for(const s of today){const o=pend[s];if(!o)continue;delete pend[s];
      const i=ptr[s],px0=P[s].O[i],fx=insts[s].fx,hs=s==="BTC"?.001:HS[insts[s].grp];
      if(o.side==="buy"&&!pos[s]){const px=px0*(1+hs),amt=Math.min(o.amt,cash-50);const q=s==="BTC"?Math.floor(amt/(px*fx)*1e4)/1e4:Math.floor((amt-feeOf(amt))/(px*fx));
        if(q>0){const g=q*px*fx,f=feeOf(g);if(g+f<=cash){cash-=g+f;fees+=f;pos[s]={q,cost:g+f,entry:d,hi:P[s].C[i],own:true}}}}
      else if(o.side==="sell"&&pos[s]){const px=px0*(1-hs),g=pos[s].q*px*fx,f=feeOf(g);cash+=g-f;fees+=f;closed.push({sym:s,in:pos[s].entry,out:d,pl:g-f-pos[s].cost,ret:(g-f)/pos[s].cost-1,why:o.why});delete pos[s];lastExit[s]=di}}
    // 2) Bewertung zum Schlusskurs
    const V=value();eq.push([d,V]);
    // 3) Signale zum Schlusskurs
    const regimeOK=g=>{const b=BENCH_OF[g];if(!cfg.regime||!b||!P[b]||ptr[b]<50)return true;const i=ptr[b];return P[b].C[i]>P[b].s50[i]};
    let reserved=0;for(const s in pend)if(pend[s].side==="buy")reserved+=pend[s].amt;
    // Kern-Anlage: Index halten, solange er über seiner 50-Tage-Linie liegt
    const coreS=cfg.core&&P[cfg.core.sym]?cfg.core.sym:null;
    if(coreS&&today.includes(coreS)&&!pend[coreS]){const i=ptr[coreS],c=P[coreS].C[i],m=P[coreS].s50[i];
      if(m){if(pos[coreS]&&c<m*(1-cfg.core.buf))pend[coreS]={side:"sell",why:"Kern"};
        else if(!pos[coreS]&&c>m){const amt=Math.min(cfg.core.w*V,cash-reserved-50);if(amt>1000){pend[coreS]={side:"buy",amt};reserved+=amt}}}}
    for(const s of today){
      if(cfg.skip.includes(s)||s===coreS)continue;
      const i=ptr[s],sc=score(P[s],i,null);if(!sc)continue;
      const prev=lastSc[s];lastSc[s]=sc.score;
      const p=pos[s];
      if(p){p.hi=Math.max(p.hi,P[s].C[i]);
        const stop=cfg.stopATR&&P[s].atr[i]?p.hi-cfg.stopATR*P[s].atr[i]:-Infinity;
        if(P[s].C[i]<stop)pend[s]={side:"sell",why:"Stop"};
        else if(sc.score<=cfg.exit)pend[s]={side:"sell",why:"Signal"};
        continue}
      if(pend[s])continue;
      const n=Object.keys(pos).filter(k=>k!==coreS).length+Object.entries(pend).filter(([k,o])=>o.side==="buy"&&k!==coreS).length;
      if(n>=cfg.maxPos)continue;
      if(sc.score<cfg.entry||sc.conf<cfg.minConf)continue;
      if(cfg.confirm&&!(prev!=null&&prev>=cfg.entry))continue;
      if(!regimeOK(insts[s].grp))continue;
      if(cfg.cool&&lastExit[s]!=null&&di-lastExit[s]<cfg.cool)continue;
      const w=cfg.risk?Math.min(cfg.maxW,cfg.risk/(sc.vol/Math.sqrt(252))):cfg.maxW;
      const amt=Math.min(cash-reserved-50,w*V);
      if(amt>500){pend[s]={side:"buy",amt};reserved+=amt}
    }
  }
  return{eq,closed,fees,open:Object.keys(pos)};
}

/* Momentum-Rotation: jede Woche die stärksten Titel (3- und 6-Monats-Rendite, risikobereinigt) halten,
   nur wenn sie über ihrer 100-Tage-Linie liegen und das Bot-Signal nicht negativ ist. */
const V3={name:"Autopilot neu",kind:"rot",every:5,top:5,cap:.3,minScore:-15,skip:["EURCHF"]};
function momOf(P,i){if(i<126||P.s100[i]==null)return null;const C=P.C,m=.5*(C[i]/C[i-63]-1)+.5*(C[i]/C[i-126]-1),v=P.vol[i]||.2;return{m,adj:m/v,trend:C[i]>P.s100[i],vol:v}}
function pickRot(cands,cfg){
  const ok=cands.filter(c=>c.mo&&c.mo.m>0&&c.mo.trend&&(!c.sc||c.sc.score>=cfg.minScore)).sort((a,b)=>b.mo.adj-a.mo.adj).slice(0,cfg.top);
  const inv=ok.map(c=>1/c.mo.vol),tot=inv.reduce((a,b)=>a+b,0);
  // Gewicht pro Titel: invers zur Volatilität, auf 1/top der Summe skaliert, gedeckelt
  return ok.map((c,k)=>({s:c.s,w:Math.min(cfg.cap,inv[k]/tot*ok.length/cfg.top)}));
}
function runRot(insts,cfg,startDate,startCash=100000){
  const syms=Object.keys(insts),P={};for(const s of syms)P[s]=prep(insts[s].rows);
  const dates=[...new Set(syms.flatMap(s=>P[s].D))].sort(),ptr={};for(const s of syms)ptr[s]=-1;
  let cash=startCash,fees=0,k=0;const pos={},pend={},eq=[],closed=[];
  const value=()=>{let v=cash;for(const s in pos)v+=pos[s].q*P[s].C[ptr[s]]*insts[s].fx;return v};
  for(let di=0;di<dates.length;di++){
    const d=dates[di],today=[];
    for(const s of syms){const p=P[s];while(ptr[s]+1<p.D.length&&p.D[ptr[s]+1]<=d)ptr[s]++;if(ptr[s]>=0&&p.D[ptr[s]]===d)today.push(s)}
    if(d<startDate)continue;
    for(const side of ["sell","buy"])for(const s of today){const o=pend[s];if(!o||o.side!==side)continue;delete pend[s];
      const i=ptr[s],fx=insts[s].fx,hs=s==="BTC"?.001:HS[insts[s].grp];
      if(side==="sell"&&pos[s]){const g=pos[s].q*P[s].O[i]*(1-hs)*fx,f=feeOf(g);cash+=g-f;fees+=f;closed.push({sym:s,in:pos[s].entry,out:d,pl:g-f-pos[s].cost,ret:(g-f)/pos[s].cost-1,why:"Rotation"});delete pos[s]}
      if(side==="buy"&&!pos[s]){const px=P[s].O[i]*(1+hs),amt=Math.min(o.amt,cash-50),q=s==="BTC"?Math.floor(amt/(px*fx)*1e4)/1e4:Math.floor((amt-feeOf(amt))/(px*fx));
        if(q>0){const g=q*px*fx,f=feeOf(g);if(g+f<=cash){cash-=g+f;fees+=f;pos[s]={q,cost:g+f,entry:d}}}}}
    const V=value();eq.push([d,V]);
    if(k++%cfg.every)continue;
    const cands=syms.filter(s=>!cfg.skip.includes(s)&&ptr[s]>=0).map(s=>({s,mo:momOf(P[s],ptr[s]),sc:score(P[s],ptr[s],null)}));
    const want=pickRot(cands,cfg),wantSet=new Set(want.map(x=>x.s));
    for(const s in pos)if(!wantSet.has(s))pend[s]={side:"sell"};
    for(const x of want)if(!pos[x.s]&&!pend[x.s])pend[x.s]={side:"buy",amt:x.w*V};
  }
  return{eq,closed,fees,open:Object.keys(pos)};
}

/* ===== Gemeinsame Live-Logik "Signal + Kern" (Browser-Autopilot und Master-Bot auf GitHub) =====
   ctx = {V, cash, lastD:"YYYY-MM-DD", cool:{sym:"YYYY-MM-DD"},
          syms:[{s,P,i,grp,price,sc:{score,conf,vol},held:{q,hi,auto,core}|null}]}
   -> Aufträge [{s, side:"sell"|"buy", amt?, core?, cool?, why}]  (Verkäufe zuerst ausführen) */
const dayDiff=(a,b)=>Math.round((Date.parse(b+"T00:00:00Z")-Date.parse(a+"T00:00:00Z"))/864e5);
function coreDecide(ctx,cfg=V2){
  const o=[],by={};for(const x of ctx.syms)by[x.s]=x;
  const cs=cfg.core&&by[cfg.core.sym]?cfg.core.sym:null;
  let nAuto=ctx.syms.filter(x=>x.held&&x.held.auto&&!x.held.core).length,budget=ctx.cash-50;
  if(cs){const x=by[cs],m=x.P.s50[x.i];
    if(x.held&&x.held.core&&m&&x.price<m*(1-cfg.core.buf))o.push({s:cs,side:"sell",why:"Kern"});
    else if(!x.held&&m&&x.price>m){const amt=Math.min(budget,cfg.core.w*ctx.V);if(amt>1000){o.push({s:cs,side:"buy",amt,core:true,why:"Kern"});budget-=amt}}}
  const regime=g=>{const b=BENCH_OF[g];if(!b||!by[b])return true;const x=by[b];return x.P.s50[x.i]==null||x.price>x.P.s50[x.i]};
  for(const x of ctx.syms){
    if(cfg.skip.includes(x.s)||x.s===cs)continue;
    const h=x.held,sc=x.sc;
    if(h){if(!h.auto||h.core)continue;const atr=x.P.atr[x.i];
      if(cfg.stopATR&&atr&&x.price<(h.hi||x.price)-cfg.stopATR*atr)o.push({s:x.s,side:"sell",why:"Stop",cool:true});
      else if(sc&&sc.score<=cfg.exit)o.push({s:x.s,side:"sell",why:"Signal",cool:true});
      continue}
    if(nAuto>=cfg.maxPos||!sc)continue;
    const prev=score(x.P,x.i-1,null);
    if(sc.score<cfg.entry||sc.conf<cfg.minConf||!prev||prev.score<cfg.entry||!regime(x.grp))continue;
    const cd=ctx.cool&&ctx.cool[x.s];if(cd&&ctx.lastD&&dayDiff(cd,ctx.lastD)<cfg.cool)continue;
    const w=Math.min(cfg.maxW,cfg.risk/(sc.vol/Math.sqrt(252))),amt=Math.min(budget,w*ctx.V);
    if(amt>500){o.push({s:x.s,side:"buy",amt,why:"Signal"});budget-=amt;nAuto++}
  }
  return o;
}
/* News-Stimmung wie im Terminal: abklingende Summe, Makro-Meldungen halb gewichtet */
const BETA={NESN:.55,NOVN:.5,ROG:.5,UBSG:.75,ABBN:.7,ZURN:.6,LOGN:.6,AAPL:.7,NVDA:.8,MSFT:.75,TSLA:.6,SMI:.95,SPX:.95,BTC:.2,XAU:-.1,EURCHF:.15};
const EQUITY=new Set(["NESN","NOVN","ROG","UBSG","ABBN","ZURN","LOGN","AAPL","NVDA","MSFT","TSLA","SMI","SPX"]);
function newsV(sym,news,now){let s=0;for(const n of news||[]){const dec=Math.exp(-Math.max(0,(now-n.t)/3600e3)*12.5/600);
  if(n.sym===sym)s+=n.sent*dec;else if(!n.sym&&EQUITY.has(sym))s+=n.sent*dec*.5*Math.max(.3,BETA[sym]??.5)}return Math.tanh(s*1.1)}
function hold(insts,syms,dates,startCash=100000){
  // gleichgewichtet kaufen am ersten Tag, danach halten (ohne Gebühren)
  const P={};syms.forEach(s=>P[s]=insts[s].rows);const first={},ptr={};syms.forEach(s=>ptr[s]=-1);
  return dates.map(d=>{let v=0;for(const s of syms){const r=P[s];while(ptr[s]+1<r.length&&r[ptr[s]+1][0]<=d)ptr[s]++;const c=ptr[s]>=0?r[ptr[s]][4]:null;if(first[s]==null&&c!=null)first[s]=c;v+=c!=null?startCash/syms.length*c/first[s]:startCash/syms.length}return[d,v]});
}
function stats(eq,closed,fees){
  const v=eq.map(e=>e[1]),r=v.slice(1).map((x,i)=>x/v[i]-1);let pk=v[0],dd=0;for(const x of v){pk=Math.max(pk,x);dd=Math.min(dd,x/pk-1)}
  const m=r.reduce((a,b)=>a+b,0)/Math.max(1,r.length),s=sd(r);
  const o={ret:v[v.length-1]/v[0]-1,mdd:dd,sharpe:s?m/s*Math.sqrt(252):0,vol:s*Math.sqrt(252)};
  if(closed){o.trades=closed.length;o.win=closed.length?closed.filter(c=>c.pl>0).length/closed.length:0;o.fees=fees;
    const w=closed.filter(c=>c.pl>0),l=closed.filter(c=>c.pl<=0);o.avgWin=w.length?w.reduce((a,c)=>a+c.ret,0)/w.length:0;o.avgLoss=l.length?l.reduce((a,c)=>a+c.ret,0)/l.length:0}
  return o;
}
function halves(eq,closed,fees){const h=Math.floor(eq.length/2);return[stats(eq.slice(0,h+1)),stats(eq.slice(h))]}
function compare(insts,v2=V3){
  const ref=insts.SMI||insts[Object.keys(insts)[0]],startDate=ref.rows[Math.min(130,ref.rows.length-1)][0];
  const a=run(insts,V1,100000,startDate),b=v2.kind==="rot"?runRot(insts,v2,startDate):run(insts,v2,100000,startDate),dates=b.eq.map(e=>e[0]);
  const bm=insts.SMI?"SMI":Object.keys(insts)[0];
  const smi=hold(insts,[bm],dates),ew=hold(insts,Object.keys(insts).filter(s=>s!=="EURCHF"),dates);
  return{dates,v1:{eq:a.eq,closed:a.closed,st:stats(a.eq,a.closed,a.fees),half:halves(a.eq),open:a.open},v2:{eq:b.eq,closed:b.closed,st:stats(b.eq,b.closed,b.fees),half:halves(b.eq),open:b.open},
    smi:{eq:smi,st:stats(smi),half:halves(smi)},ew:{eq:ew,st:stats(ew),half:halves(ew)},bm};
}

/* alle Strategien im selben Zeitfenster vergleichen */
function compareAll(insts){
  const ref=insts.SMI||insts[Object.keys(insts)[0]],startDate=ref.rows[Math.min(130,Math.floor(ref.rows.length/2))][0];
  const pack=r=>({eq:r.eq,closed:r.closed,st:stats(r.eq,r.closed,r.fees),half:halves(r.eq),open:r.open});
  const alt=pack(run(insts,V1,100000,startDate)),core=pack(run(insts,V2,100000,startDate)),rot=pack(runRot(insts,V3,startDate));
  const dates=core.eq.map(e=>e[0]),bm=insts.SMI?"SMI":Object.keys(insts)[0];
  const sm=hold(insts,[bm],dates),ew=hold(insts,Object.keys(insts).filter(s=>s!=="EURCHF"),dates);
  return{dates,alt,core,rot,smi:{eq:sm,st:stats(sm),half:halves(sm)},ew:{eq:ew,st:stats(ew),half:halves(ew)},bm};
}
return{compareAll,coreDecide,newsV,dayDiff,prep,score,run,runRot,momOf,pickRot,hold,stats,compare,V1,V2,V3,feeOf};
})();
