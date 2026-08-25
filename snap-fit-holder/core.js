(function(root,factory){
  'use strict';
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  root.CR20KBSnapFitHolder=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';

  const REF_D=22.0,REF_HOLE_Y=18.0,REF_HOLE_D=5.0,REF_PLATE_X=7.0;
  const PATH=Object.freeze([
    ['M',0.0,-29.5],['L',7.0,-29.5],['L',7.0,-8.5],['A',7.585786437626905,-7.085786437626905,9.0,-6.5],['L',28.0385186031843,-6.5],
    ['A',28.988900529807285,-6.740234619743761,29.7109678156766,-7.40322580645161],['A',37.02554998461908,-12.90169551164647,46.1662263369287,-12.4723736889024],
    ['A',48.052336949495334,-12.486308134874132,49.3561701198421,-13.849255850498],['A',50.96867245175525,-14.573711666662431,51.6931282679198,-12.9612093347493],
    ['A',49.04306700530129,-10.190996836482837,45.209517756016,-10.1626748576242],['A',30.0,0.0,45.209517756016,10.1626748576242],
    ['A',49.043067005301296,10.190996836482842,51.6931282679198,12.9612093347492],['A',50.96867245175525,14.57371166666243,49.3561701198421,13.849255850498],
    ['A',48.052336949495285,12.486308134874111,46.1662263369287,12.4723736889024],['A',37.02554998461909,12.901695511646468,29.7109678156766,7.4032258064516],
    ['A',28.988900529807268,6.7402346197437515,28.0385186031843,6.5],['L',9.0,6.5],['A',7.585786437626905,7.085786437626905,7.0,8.5],['L',7.0,29.5],['L',0.0,29.5]
  ]);
  const DEFAULTS=Object.freeze({D:22.03,fit:-0.03,width:22.0,holeD:5.0,quality:48,arcChord:.18});
  const LIMITS=Object.freeze({D:[12,100],fit:[-2,2],width:[8,60],holeD:[3,10],quality:[24,96],arcChord:[.08,.5]});
  const clamp=(n,a,b)=>Math.max(a,Math.min(b,n)),num=(v,f)=>Number.isFinite(Number(v))?Number(v):f,mod=a=>((a%(2*Math.PI))+2*Math.PI)%(2*Math.PI);

  function normalize(options={}){
    const p={...DEFAULTS,...options};
    p.D=clamp(num(p.D,DEFAULTS.D),...LIMITS.D);p.fit=clamp(num(p.fit,DEFAULTS.fit),...LIMITS.fit);p.clipD=Math.max(8,p.D+p.fit);p.scale=p.clipD/REF_D;
    if(Number.isFinite(Number(p.depthRatio))&&!Number.isFinite(Number(options.width)))p.width=p.clipD*Number(p.depthRatio);
    p.width=clamp(num(p.width,DEFAULTS.width),...LIMITS.width);p.holeD=clamp(num(p.holeD,DEFAULTS.holeD),...LIMITS.holeD);p.holeD=Math.min(p.holeD,Math.max(3,p.width-1));
    p.quality=Math.round(clamp(num(p.quality,DEFAULTS.quality),...LIMITS.quality));p.arcChord=clamp(num(p.arcChord,DEFAULTS.arcChord),...LIMITS.arcChord);p.depth=p.width;p.depthRatio=p.width/p.clipD;return p;
  }
  function circumcenter(a,b,c){const[x1,y1]=a,[x2,y2]=b,[x3,y3]=c,d=2*(x1*(y2-y3)+x2*(y3-y1)+x3*(y1-y2));if(Math.abs(d)<1e-12)throw new Error('degenerate arc');const u1=x1*x1+y1*y1,u2=x2*x2+y2*y2,u3=x3*x3+y3*y3;return[(u1*(y2-y3)+u2*(y3-y1)+u3*(y1-y2))/d,(u1*(x3-x2)+u2*(x1-x3)+u3*(x2-x1))/d]}
  function arcPoints(p0,pm,p1,chord){const c=circumcenter(p0,pm,p1),r=Math.hypot(p0[0]-c[0],p0[1]-c[1]),a0=Math.atan2(p0[1]-c[1],p0[0]-c[0]),am=Math.atan2(pm[1]-c[1],pm[0]-c[0]),a1=Math.atan2(p1[1]-c[1],p1[0]-c[0]),ccw=mod(a1-a0),mid=mod(am-a0),sw=mid<=ccw+1e-8?ccw:ccw-2*Math.PI,n=Math.max(2,Math.ceil(Math.abs(sw*r)/Math.max(.03,chord))),out=[];for(let i=1;i<=n;i++){const a=a0+sw*i/n;out.push([c[0]+Math.cos(a)*r,c[1]+Math.sin(a)*r])}return out}
  function profile(options={}){const p=normalize(options),s=p.scale,ch=p.arcChord/s;let cur=[PATH[0][1],PATH[0][2]],pts=[[cur[0]*s,cur[1]*s]];for(let i=1;i<PATH.length;i++){const q=PATH[i];if(q[0]==='L'){cur=[q[1],q[2]];pts.push([cur[0]*s,cur[1]*s])}else{const mid=[q[1],q[2]],end=[q[3],q[4]];for(const a of arcPoints(cur,mid,end,ch))pts.push([a[0]*s,a[1]*s]);cur=end}}const clean=[];for(const q of pts){const a=clean.at(-1);if(!a||Math.hypot(q[0]-a[0],q[1]-a[1])>1e-8)clean.push(q)}return{params:p,points:clean}}
  function resolve(options={}){const pr=profile(options),p=pr.params,s=p.scale,xs=pr.points.map(q=>q[0]),ys=pr.points.map(q=>q[1]);return{...pr,holeY:REF_HOLE_Y*s,holeSpacing:36*s,plateThickness:REF_PLATE_X*s,ringCenterX:41*s,innerDiameter:p.clipD,outerDiameter:27*s,wall:2.5*s,stemWidth:13*s,flangeWidth:59*s,filletR:2*s,lipRadii:[2.42127091581242*s,1.25*s,4.92127091581242*s],bounds2d:{xmin:Math.min(...xs),xmax:Math.max(...xs),ymin:Math.min(...ys),ymax:Math.max(...ys)},overall:{x:51.7746491938809*s,y:59*s,z:p.width}}}

  function area2(poly){let a=0;for(let i=0;i<poly.length;i++){const p=poly[i],q=poly[(i+1)%poly.length];a+=p[0]*q[1]-q[0]*p[1]}return a/2}
  const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
  function inTri(p,a,b,c,e=1e-10){return cross(a,b,p)>=-e&&cross(b,c,p)>=-e&&cross(c,a,p)>=-e}
  function triangulate(poly){let pts=poly.map(q=>[q[0],q[1]]);if(area2(pts)<0)pts.reverse();const idx=pts.map((_,i)=>i),tris=[];let guard=0;while(idx.length>3&&guard++<100000){let found=false;for(let k=0;k<idx.length;k++){const i0=idx[(k-1+idx.length)%idx.length],i1=idx[k],i2=idx[(k+1)%idx.length],a=pts[i0],b=pts[i1],c=pts[i2];if(cross(a,b,c)<=1e-10)continue;let bad=false;for(const j of idx){if(j!==i0&&j!==i1&&j!==i2&&inTri(pts[j],a,b,c)){bad=true;break}}if(bad)continue;tris.push([i0,i1,i2]);idx.splice(k,1);found=true;break}if(found)continue;let removed=false;for(let k=0;k<idx.length;k++){const i0=idx[(k-1+idx.length)%idx.length],i1=idx[k],i2=idx[(k+1)%idx.length];if(Math.abs(cross(pts[i0],pts[i1],pts[i2]))<1e-8){idx.splice(k,1);removed=true;break}}if(!removed)throw new Error('profile triangulation failed')}if(idx.length===3)tris.push([idx[0],idx[1],idx[2]]);return{points:pts,triangles:tris}}

  function mesh(options={}){
    const R=resolve(options),p=R.params,T=triangulate(R.points),P=T.points,z0=-p.width/2,z1=p.width/2,faces=[];
    const v=(x,y,z)=>[x,y,z],add=(a,b,c)=>faces.push([a,b,c]);
    for(const[a,b,c]of T.triangles){add(v(P[a][0],P[a][1],z0),v(P[c][0],P[c][1],z0),v(P[b][0],P[b][1],z0));add(v(P[a][0],P[a][1],z1),v(P[b][0],P[b][1],z1),v(P[c][0],P[c][1],z1))}
    const eps=1e-6,plateX=R.plateThickness;
    function isHolePlaneEdge(a,b){if(Math.abs(a[0])<eps&&Math.abs(b[0])<eps)return true;if(Math.abs(a[0]-plateX)<eps&&Math.abs(b[0]-plateX)<eps)return true;return false}
    for(let i=0;i<P.length;i++){const j=(i+1)%P.length,a=P[i],b=P[j];if(isHolePlaneEdge(a,b))continue;const a0=v(a[0],a[1],z0),b0=v(b[0],b[1],z0),b1=v(b[0],b[1],z1),a1=v(a[0],a[1],z1);add(a0,b0,b1);add(a0,b1,a1)}

    function triUV(x,A,B,C,sign){let a=v(x,A[0],A[1]),b=v(x,B[0],B[1]),c=v(x,C[0],C[1]);const ar=(B[0]-A[0])*(C[1]-A[1])-(B[1]-A[1])*(C[0]-A[0]);if((ar>0?1:-1)!==sign){const q=b;b=c;c=q}add(a,b,c)}
    function quadUV(x,A,B,C,D,sign){triUV(x,A,B,C,sign);triUV(x,A,C,D,sign)}
    function rectUV(x,u0,u1,v0,v1,sign){quadUV(x,[u0,v0],[u1,v0],[u1,v1],[u0,v1],sign)}
    function plateSurface(x,yMin,yMax,centers,sign){const r=p.holeD/2,h=p.width/2,N=Math.max(16,p.quality),sorted=[...centers].sort((a,b)=>a-b);let cursor=yMin;for(const cy of sorted){const left=cy-r,right=cy+r;if(left>cursor)rectUV(x,cursor,left,-h,h,sign);const upper=[],lower=[];for(let i=0;i<=N/2;i++){const a=Math.PI-Math.PI*i/(N/2);upper.push([cy+Math.cos(a)*r,Math.sin(a)*r]);const b=Math.PI+Math.PI*i/(N/2);lower.push([cy+Math.cos(b)*r,Math.sin(b)*r])}for(let i=0;i<upper.length-1;i++)quadUV(x,upper[i],upper[i+1],[upper[i+1][0],h],[upper[i][0],h],sign);for(let i=0;i<lower.length-1;i++)quadUV(x,[lower[i][0],-h],[lower[i+1][0],-h],lower[i+1],lower[i],sign);cursor=right}if(cursor<yMax)rectUV(x,cursor,yMax,-h,h,sign)}
    const yB=29.5*p.scale,yGap=8.5*p.scale,hc=R.holeY;
    plateSurface(0,-yB,yB,[-hc,hc],-1);plateSurface(plateX,-yB,-yGap,[-hc],1);plateSurface(plateX,yGap,yB,[hc],1);
    const N=Math.max(16,p.quality),hr=p.holeD/2;for(const cy of[-hc,hc])for(let i=0;i<N;i++){const a0=2*Math.PI*i/N,a1=2*Math.PI*(i+1)/N,A=v(0,cy+Math.cos(a0)*hr,Math.sin(a0)*hr),B=v(plateX,cy+Math.cos(a0)*hr,Math.sin(a0)*hr),C=v(plateX,cy+Math.cos(a1)*hr,Math.sin(a1)*hr),D=v(0,cy+Math.cos(a1)*hr,Math.sin(a1)*hr);add(A,B,C);add(A,C,D)}
    const flat=[];for(const f of faces)flat.push(...f);let vol=0;for(const f of faces){const[a,b,c]=f;vol+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6}return{vertices:flat,faces,triangles:faces.length,volume:Math.abs(vol),resolved:R};
  }
  function normal(a,b,c){const ux=b[0]-a[0],uy=b[1]-a[1],uz=b[2]-a[2],vx=c[0]-a[0],vy=c[1]-a[1],vz=c[2]-a[2],x=uy*vz-uz*vy,y=uz*vx-ux*vz,z=ux*vy-uy*vx,l=Math.hypot(x,y,z)||1;return[x/l,y/l,z/l]}
  function fileName(options={}){const p=normalize(options),f=v=>(Math.round(v*100)/100).toString().replace('.','p');return`cr20kb-snap-fit-holder-D-${f(p.D)}-fit-${f(p.fit)}-W-${f(p.width)}.stl`}
  function binaryStl(options={}){const M=mesh(options),count=M.faces.length,buffer=new ArrayBuffer(84+count*50),dv=new DataView(buffer),head='CR20KB Snap-Fit Holder exact-profile v1';for(let i=0;i<head.length&&i<80;i++)dv.setUint8(i,head.charCodeAt(i));dv.setUint32(80,count,true);let off=84;for(const pts of M.faces){const n=normal(...pts);for(const x of[...n,...pts[0],...pts[1],...pts[2]]){dv.setFloat32(off,x,true);off+=4}dv.setUint16(off,0,true);off+=2}return{buffer,mesh:M,fileName:fileName(options)}}
  return{REF_D,REF_HOLE_Y,REF_HOLE_D,PATH,DEFAULTS,LIMITS,normalize,profile,resolve,triangulate,mesh,fileName,binaryStl};
});
