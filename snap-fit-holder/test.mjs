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
assert.ok(Math.abs(r.overall.x-51.7746491938809)<1e-9);
assert.ok(Math.abs(r.overall.y-59)<1e-9);
assert.ok(Math.abs(r.overall.z-22)<1e-9);
assert.equal(r.holeSpacing,36);
assert.equal(r.wall,2.5);

const cases=[
  {D:12,width:12,holeD:5,quality:24,arcChord:.35},
  {D:22.03,width:22,holeD:5,quality:48,arcChord:.18},
  {D:40,width:30,holeD:5,quality:48,arcChord:.18},
  {D:60,width:30,holeD:5,quality:48,arcChord:.18},
  {D:100,width:30,holeD:5,quality:48,arcChord:.18},
  {D:12,width:8,holeD:10,quality:48,arcChord:.18},
  {D:100,width:60,holeD:10,quality:80,arcChord:.10}
];
for(const c of cases){
  c.fit=c.D*(22/22.03-1);
  const M=C.mesh(c);
  assert.equal(manifold(M).length,0,`non-manifold ${JSON.stringify(c)}`);
  assert.ok(M.triangles>500);
  const stl=C.binaryStl(c);
  assert.equal(stl.buffer.byteLength,84+M.triangles*50);
}
const base=C.mesh();
assert.equal(manifold(base).length,0);
assert.ok(base.volume>18260&&base.volume<18290,base.volume);
console.log(`Snap-Fit PASS: base triangles=${base.triangles}, volume=${base.volume.toFixed(3)} mm3`);
