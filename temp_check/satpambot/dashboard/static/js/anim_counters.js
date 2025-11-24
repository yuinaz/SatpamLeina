
import { onFrame, lerp, clamp, easeExp } from './anim_util.js';

const nodes = new Map(); // id -> {el, value, target}

export function bindCounter(id, initial=0){
  const el = document.getElementById(id);
  if(!el) return;
  nodes.set(id, { el, value: initial, target: initial });
}

export function setCounter(id, value){
  const n = nodes.get(id); if(!n) return;
  n.target = Number(value)||0;
}

function format(v){
  if (v >= 1e9) return (v/1e9).toFixed(1).replace(/\.0$/,'') + 'B';
  if (v >= 1e6) return (v/1e6).toFixed(1).replace(/\.0$/,'') + 'M';
  if (v >= 1e3) return (v/1e3).toFixed(1).replace(/\.0$/,'') + 'K';
  return Math.round(v).toString();
}

onFrame((dt)=>{
  for(const [id,n] of nodes){
    const diff = n.target - n.value;
    if (Math.abs(diff) < 0.01) { n.value = n.target; }
    else {
      // accelerate early, decelerate near the end
      const t = clamp(dt*7, 0, 1);
      n.value = lerp(n.value, n.target, easeExp(t));
    }
    n.el.textContent = format(n.value);
  }
});
