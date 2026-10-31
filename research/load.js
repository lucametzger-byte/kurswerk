const fs=require("fs"),zlib=require("zlib");
const KWBT=new Function(fs.readFileSync("../bt.js","utf8")+";return KWBT;")();
const H=JSON.parse(zlib.gunzipSync(fs.readFileSync(process.env.HIST||"history.json.gz"))).data;
const rowsOf=s=>{const r=H[s];return r.d.map((d,i)=>[d,r.o[i],r.h[i],r.l[i],r.c[i],r.v[i]])};
module.exports={KWBT,H,rowsOf};
