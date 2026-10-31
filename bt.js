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
  return{D,O,H,L,C,s20,s50,R,mh,bb,vol,atr:sma(tr,14)};
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
function run(insts,cfg,startCash=100000){
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
    if(di<startDi)continue;
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
function compare(insts,v2=V2){
  const a=run(insts,V1),b=run(insts,v2),dates=b.eq.map(e=>e[0]);
  const bm=insts.SMI?"SMI":Object.keys(insts)[0];
  const smi=hold(insts,[bm],dates),ew=hold(insts,Object.keys(insts).filter(s=>s!=="EURCHF"),dates);
  return{dates,v1:{eq:a.eq,closed:a.closed,st:stats(a.eq,a.closed,a.fees),half:halves(a.eq),open:a.open},v2:{eq:b.eq,closed:b.closed,st:stats(b.eq,b.closed,b.fees),half:halves(b.eq),open:b.open},
    smi:{eq:smi,st:stats(smi),half:halves(smi)},ew:{eq:ew,st:stats(ew),half:halves(ew)},bm};
}
return{prep,score,run,hold,stats,compare,V1,V2,feeOf};
})();
