import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const C=require('./core.js');

function manifold(M){
  const q=p=>p.map(v=>Math.round(v*1e7)/1e7).join(',');
  const edges=new Map();
  for(const tri of M.faces){for(const[a,b]of[[tri[0],tri[1]],[tri[1],tri[2]],[tri[2],tri[0]]]){const A=q(a),B=q(b),k=A<B?`${A}|${B}`:`${B}|${A}`;edges.set(k,(edges.get(k)||0)+1)}}
  return [...edges.values()].filter(n=>n!==2);
}
const r=C.resolve();
assert.equal(r.innerDiameter,22);
assert.equal(r.ringCenterX,41);
assert.equal(r.wall,2.5);
assert.equal(r.holeSpacing,36);
assert.equal(r.plateThickness,7);
assert.equal(r.flangeWidth,59);
assert.equal(r.params.LAdjusted,false);

const d35=C.resolve({D:35,fit:35*(22/22.03-1),L:41,wall:2.5,width:20,holeD:5});
assert.equal(d35.ringCenterX,41);
assert.equal(d35.wall,2.5);
assert.ok(d35.holeSpacing>36);
assert.ok(d35.holeY-d35.ringYMax>=d35.driverClearanceRadius-1e-9);
assert.ok(d35.flangeWidth/2-(d35.holeY+d35.params.holeD/2)>=4-1e-9);

const d40=C.resolve({D:40,fit:40*(22/22.03-1),L:41,wall:2.5,width:20});
assert.equal(d40.ringCenterX,41);
assert.ok(d40.holeSpacing>=d35.holeSpacing);
const d100=C.resolve({D:100,fit:100*(22/22.03-1),L:41,wall:2.5,width:20});
assert.equal(d100.params.LAdjusted,true);
assert.ok(d100.ringCenterX>41&&d100.ringCenterX<70);
assert.ok(d100.holeSpacing>d40.holeSpacing);

const cases=[
  {D:12,fit:12*(22/22.03-1),width:12,L:41,wall:2.5,holeD:5,quality:24,arcChord:.35},
  {D:22.03,fit:-.03,width:20,L:41,wall:2.5,holeD:5,quality:48,arcChord:.18},
  {D:35,fit:35*(22/22.03-1),width:20,L:41,wall:2.5,holeD:5,quality:48,arcChord:.18},
  {D:40,fit:40*(22/22.03-1),width:20,L:41,wall:2.5,holeD:5,quality:48,arcChord:.18},
  {D:60,fit:60*(22/22.03-1),width:20,L:41,wall:2.5,holeD:5,quality:48,arcChord:.18},
  {D:100,fit:100*(22/22.03-1),width:20,L:41,wall:2.5,holeD:5,quality:48,arcChord:.18},
  {D:100,fit:100*(22/22.03-1),width:30,L:90,wall:5,holeD:6,quality:48,arcChord:.18},
  {D:22.03,fit:-.03,width:22,L:50,wall:4,holeD:5,quality:48,arcChord:.18}
];
for(const c of cases){
  const R=C.resolve(c);
  assert.ok(R.holeY-R.ringYMax>=R.driverClearanceRadius-.76,`tool corridor ${JSON.stringify(c)}`);
  const M=C.mesh(c);
  assert.equal(manifold(M).length,0,`non-manifold ${JSON.stringify(c)}`);
  assert.ok(M.triangles>500);
  const stl=C.binaryStl(c);
  assert.equal(stl.buffer.byteLength,84+M.triangles*50);
}
const base=C.mesh();
assert.equal(manifold(base).length,0);
assert.ok(base.volume>18260&&base.volume<18295,base.volume);
assert.match(C.binaryStl().fileName,/D-22p03-L-41-wall-2p5-W-22/);

const app=fs.readFileSync(new URL('./app-v11.js',import.meta.url),'utf8');
const html=fs.readFileSync(new URL('./index.html',import.meta.url),'utf8');
assert.match(app,/function defaultWidth\(D\)\{return Math\.min\(Math\.max\(D,12\),20\)\}/);
assert.match(app,/defaultWidth\(22\.03\)/);
assert.match(html,/id="width"[^>]*value="20"/);

console.log(`Snap-Fit v1.2 width20 PASS: base triangles=${base.triangles}, D35 pitch=${d35.holeSpacing.toFixed(1)} mm, flange=${d35.flangeWidth.toFixed(1)} mm`);
