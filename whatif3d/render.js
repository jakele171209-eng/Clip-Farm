// node render.js out_dir fps [t1,t2,...]   -> PNG frames
const { chromium } = require('playwright'); const http=require('http'),fs=require('fs'),path=require('path');
const root=__dirname; const types={'.html':'text/html','.js':'text/javascript'};
const srv=http.createServer((q,r)=>{const f=path.join(root,decodeURIComponent(q.url.split('?')[0]));fs.readFile(f,(e,d)=>{if(e){r.writeHead(404);r.end();return}r.writeHead(200,{'Content-Type':types[path.extname(f)]||'application/octet-stream'});r.end(d)})}).listen(8765);
(async()=>{
  const [out,fps,list]=process.argv.slice(2); fs.mkdirSync(out,{recursive:true});
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const p=await b.newPage({viewport:{width:1080,height:1920}});
  p.on('console',m=>console.log('page:',m.text())); p.on('pageerror',e=>console.log('ERR',e.message));
  await p.goto('http://localhost:8765/scene.html'); await p.waitForFunction('window.ready===true');
  const dur=await p.evaluate('window.DURATION');
  const ts=list?list.split(',').map(Number):[...Array(Math.round(dur*fps)).keys()].map(i=>i/fps);
  const c=await p.$('canvas'); let i=0; const t0=Date.now();
  for(const t of ts){await p.evaluate(t=>window.renderFrame(t),t);
    await c.screenshot({path:`${out}/f${String(i++).padStart(5,'0')}.png`});
    if(i%30==0)console.log(i,'/',ts.length,((Date.now()-t0)/i).toFixed(0)+'ms/frame');}
  await b.close(); srv.close();
})();
