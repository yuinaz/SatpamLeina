
import { autoCanvas, onFrame, clamp } from './anim_util.js';

export function SparklineCanvas(canvas, opts={}){
  const ctx = autoCanvas(canvas);
  let W=canvas.clientWidth, H=canvas.clientHeight;
  let data = new Float32Array(120).fill(0);
  let head = 0;
  let color = opts.color || 'rgba(72, 132, 255, .85)';
  let bg = opts.bg || 'rgba(255,255,255,.04)';
  let grid = opts.grid || 'rgba(255,255,255,.05)';
  let maxKeep = data.length;

  function push(v){
    data[head] = v;
    head = (head + 1) % data.length;
  }

  function set(vs){
    const n = Math.min(vs.length, data.length);
    for(let i=0;i<n;i++) data[(head+i)%data.length] = vs[i];
    head = (head + n) % data.length;
  }

  function draw(){
    const rect = canvas.getBoundingClientRect(); W = rect.width; H = rect.height;
    ctx.clearRect(0,0,W,H);
    // bg
    ctx.fillStyle = bg; ctx.fillRect(0,0,W,H);

    // vertical grid
    ctx.strokeStyle = grid; ctx.lineWidth = 1;
    ctx.beginPath();
    for(let x=0;x<W;x+=Math.max(16, Math.floor(W/12))){
      ctx.moveTo(x+0.5, 0); ctx.lineTo(x+0.5, H);
    }
    ctx.stroke();

    // normalize
    let maxV = 1;
    for(let i=0;i<data.length;i++) maxV = Math.max(maxV, data[i]);
    const step = W / (data.length-1);
    // line
    ctx.beginPath();
    ctx.strokeStyle = color; ctx.lineWidth = 2;
    for(let i=0;i<data.length;i++){
      const idx = (head + i) % data.length;
      const v = data[idx] / maxV;
      const x = i * step;
      const y = H - (H*0.85*v + H*0.1);
      if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
    }
    ctx.stroke();
  }

  const stop = onFrame(()=>draw());

  return { push, set, draw, stop };
}
