import assert from 'node:assert/strict';
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

const d40=C.resolve({D:40,fit:40*(22/22.03-1),L:41,wall:2.5,width:30});
assert.equal(d40.ringCenterX,41);
assert.equal(d40.wall,2.5);
assert.equal(d40.holeSpacing,36);
const d100=C.resolve({D:100,fit:100*(22/22.03-1),L:41,wall:2.5,width:30});
assert.equal(d100.params.LAdjusted,true);
assert.ok(d100.ringCenterX>41&&d100.ringCenterX<70);

const cases=[
  {D:12,fit:12*(22/22.03-1),width:12,L:41,wall:2.5,holeD:5,quality:24,arcChord:.35},
  {D:22.03,fit:-.03,width:22,L:41,wall:2.5,holeD:5,quality:48,arcChord:.18},
  {D:40,fit:40*(22/22.03-1),width:30,L:41,wall:2.5,holeD:5,quality:48,arcChord:.18},
  {D:60,fit:60*(22/22.03-1),width:30,L:41,wall:2.5,holeD:5,quality:48,arcChord:.18},
  {D:100,fit:100*(22/22.03-1),width:30,L:41,wall:2.5,holeD:5,quality:48,arcChord:.18},
  {D:100,fit:100*(22/22.03-1),width:30,L:90,wall:5,holeD:6,quality:48,arcChord:.18},
  {D:22.03,fit:-.03,width:22,L:50,wall:4,holeD:5,quality:48,arcChord:.18}
];
for(const c of cases){
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
console.log(`Snap-Fit v1.1 PASS: base triangles=${base.triangles}, volume=${base.volume.toFixed(3)} mm3, L=${r.ringCenterX}`);
