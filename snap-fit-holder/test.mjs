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

assert.equal(C.defaultHoleD(12),5);
assert.equal(C.defaultHoleD(19.99),5);
assert.equal(C.defaultHoleD(20),6.5);
assert.equal(C.defaultHoleD(100),6.5);

const baseline=C.resolve({D:22.03,fit:-.03,width:22,L:41,wall:2.5,holeD:5});
assert.equal(baseline.holeSpacing,36);
assert.equal(baseline.flangeWidth,59);

const current=C.resolve({D:22.03,fit:-.03,width:20,L:41,wall:2.5});
assert.equal(current.params.holeD,6.5);
assert.ok(current.flangeWidth/2-(current.holeY+current.params.holeD/2)>=4-1e-9);

const small=C.resolve({D:16,fit:16*(22/22.03-1),width:16,L:41,wall:2.5});
assert.equal(small.params.holeD,5);

const d35=C.resolve({D:35,fit:35*(22/22.03-1),width:20,L:41,wall:2.5});
assert.equal(d35.params.holeD,6.5);
assert.ok(d35.holeY-d35.ringYMax>=d35.driverClearanceRadius-1e-9);
assert.ok(d35.flangeWidth/2-(d35.holeY+d35.params.holeD/2)>=4-1e-9);

const cases=[
  {D:12,fit:12*(22/22.03-1),width:12,L:41,wall:2.5,quality:24,arcChord:.35},
  {D:16,fit:16*(22/22.03-1),width:16,L:41,wall:2.5,quality:48,arcChord:.18},
  {D:22.03,fit:-.03,width:20,L:41,wall:2.5,quality:48,arcChord:.18},
  {D:35,fit:35*(22/22.03-1),width:20,L:41,wall:2.5,quality:48,arcChord:.18},
  {D:40,fit:40*(22/22.03-1),width:20,L:41,wall:2.5,quality:48,arcChord:.18},
  {D:60,fit:60*(22/22.03-1),width:20,L:41,wall:2.5,quality:48,arcChord:.18},
  {D:100,fit:100*(22/22.03-1),width:20,L:41,wall:2.5,quality:48,arcChord:.18},
  {D:100,fit:100*(22/22.03-1),width:30,L:90,wall:5,holeD:8,quality:48,arcChord:.18}
];
for(const c of cases){
  const R=C.resolve(c);
  assert.ok(R.flangeWidth/2-(R.holeY+R.params.holeD/2)>=4-1e-9,`edge margin ${JSON.stringify(c)}`);
  const M=C.mesh(c);
  assert.equal(manifold(M).length,0,`non-manifold ${JSON.stringify(c)}`);
  assert.ok(M.triangles>500);
  assert.equal(C.binaryStl(c).buffer.byteLength,84+M.triangles*50);
}

console.log(`Snap-Fit v1.3 PASS: D22 hole=${current.params.holeD}; D35 pitch=${d35.holeSpacing.toFixed(1)}; flange=${d35.flangeWidth.toFixed(1)}`);
