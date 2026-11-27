import type { RoutePoint } from '../types';

/** Geometria di display, MAI alterare i punti GPX originali.
 * Semplifica le polilinee inattive (~15 m) prima di consegnarle al worker.
 * Il percorso selezionato viene ancora disegnato dal layer GPX completo.
 */
const displayCache=new WeakMap<RoutePoint[],number[][]>();

function distanceSq(p:RoutePoint,a:RoutePoint,b:RoutePoint):number{
  const lat=Math.cos(p[1]*Math.PI/180);
  const kx=111320*lat,ky=111195;
  const ax=(a[0]-p[0])*kx,ay=(a[1]-p[1])*ky;
  const bx=(b[0]-p[0])*kx,by=(b[1]-p[1])*ky;
  const dx=bx-ax,dy=by-ay;
  const factor=Math.max(0,Math.min(1,-(ax*dx+ay*dy)/Math.max(1,dx*dx+dy*dy)));
  const x=ax+factor*dx,y=ay+factor*dy;
  return x*x+y*y;
}
export function routeDisplayGeometry(points:RoutePoint[]):number[][]{
  const cached=displayCache.get(points);if(cached)return cached;
  if(points.length<=2){
    const raw=points.map(p=>[p[0],p[1]]);
    displayCache.set(points,raw);return raw;
  }
  const selected=new Uint8Array(points.length);
  selected[0]=selected[points.length-1]=1;
  const stack: [number,number][] = [[0,points.length-1]];
  const tolerance2=15*15;
  while(stack.length){
    const [left,right]=stack.pop()!;
    let largest=-1,idx=-1;
    for(let i=left+1;i<right;i++){
      const d=distanceSq(points[i],points[left],points[right]);
      if(d>largest){largest=d;idx=i;}
    }
    if(largest>tolerance2&&idx>left){
      selected[idx]=1;
      stack.push([left,idx],[idx,right]);
    }
  }
  const chosen:number[][]=[];
  for(let i=0;i<points.length;i++)if(selected[i])chosen.push([points[i][0],points[i][1]]);
  // Il GPX integrale è disponibile nel layer attivo; anteprima max 600 punti.
  const result=chosen.length>600?chosen.filter((_,i)=>i===0||i===chosen.length-1||i%Math.ceil(chosen.length/598)===0):chosen;
  displayCache.set(points,result);
  return result;
}
