
import { autoCanvas, onFrame, clamp } from './anim_util.js';

export function BarsCanvas(canvas, n=16){
  const ctx = autoCanvas(canvas);
  let W=canvas.clientWidth, H=canvas.clientHeight;
  let cur = new Array(n).fill(0);
  let target = new Array(n).fill(0);
  function set(arr){
    const m = Math.min(arr.length, n);
    let max = 1; for(let i=0;i<m;i++) max = Math.max(max, arr[i]);
    for(let i=0;i<m;i++) target[i] = max>0 ? arr[i]/max : 0;
  }
  function draw(dt){
    ctx.clearRect(0,0,W,H);
    const gap = 8, barW = (W - gap*(n+1)) / n;
    for(let i=0;i<n;i++){
      cur[i] += (target[i]-cur[i]) * Math.min(1, dt*10);
      const h = Math.max(2, Math.min(H-6, cur[i]*H*0.9));
      const x = gap + i*(barW+gap);
      const y = H - h - 4;
      const r = 8, rr = Math.min(r,h);
      ctx.fillStyle = 'rgba(56,128,255,.65)';
      ctx.beginPath();
      ctx.moveTo(x, y+rr);
      ctx.arcTo(x, y, x+rr, y, rr);
      ctx.lineTo(x+barW-rr, y);
      ctx.arcTo(x+barW, y, x+barW, y+rr, rr);
      ctx.lineTo(x+barW, y+h);
      ctx.lineTo(x, y+h);
      ctx.closePath();
      ctx.fill();
    }
  }
  const stop = onFrame((dt)=>draw(dt));
  return { set, stop };
}
