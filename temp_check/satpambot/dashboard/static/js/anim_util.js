
// rAF loop registry + DPI helpers
export const DPR = Math.max(1, Math.floor(window.devicePixelRatio || 1));

export function autoCanvas(canvas){
  const ctx = canvas.getContext('2d');
  const resize = ()=>{
    const rect = canvas.getBoundingClientRect();
    const W = Math.max(10, Math.floor(rect.width));
    const H = Math.max(10, Math.floor(rect.height));
    canvas.width = W * DPR; canvas.height = H * DPR;
    canvas.style.width = W+'px'; canvas.style.height = H+'px';
    ctx.setTransform(DPR,0,0,DPR,0,0);
  };
  resize(); new ResizeObserver(resize).observe(canvas);
  return ctx;
}

let rafHandlers = new Set();
let last = performance.now();
function tick(t){
  const dt = Math.min(0.05, Math.max(0,(t-last)/1000));
  last = t;
  for(const cb of rafHandlers) { try{ cb(dt, t); }catch(e){} }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

export function onFrame(cb){
  rafHandlers.add(cb);
  return ()=>rafHandlers.delete(cb);
}

export const clamp = (x,a,b)=>Math.max(a,Math.min(b,x));
export const lerp = (a,b,t)=>a+(b-a)*t;
export const easeExp = (x)=>1-Math.exp(-6*x); // snappy easing
