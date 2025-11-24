
// 60fps Particles for login background (lightweight, no external deps)
(function(){
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let canvas, ctx, DPR=1, W=0, H=0, rafId=0, dots=[];
  function init(){
    if(prefersReduced) return;
    if(!canvas){
      canvas = document.createElement('canvas');
      canvas.id = 'login-bg-canvas';
      document.body.appendChild(canvas);
      ctx = canvas.getContext('2d');
      window.addEventListener('resize', resize, {passive:true});
    }
    resize();
    spawn();
    loop(0);
  }
  function resize(){
    DPR = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
    W = canvas.width = Math.floor(innerWidth * DPR);
    H = canvas.height = Math.floor(innerHeight * DPR);
    canvas.style.width = innerWidth+'px'; canvas.style.height = innerHeight+'px';
  }
  function spawn(){
    const N = Math.floor(Math.min(120, (W*H)/120000)); // scale with screen
    dots = new Array(N).fill(0).map(()=> ({
      x: Math.random()*W, y: Math.random()*H,
      vx: (Math.random()*2-1)*0.08*DPR,
      vy: (Math.random()*2-1)*0.08*DPR,
      r: (Math.random()*1.2+0.6)*DPR,
      a: Math.random()*0.6+0.25
    }));
  }
  function loop(t){
    rafId = requestAnimationFrame(loop);
    ctx.clearRect(0,0,W,H);
    // gradient
    const g = ctx.createLinearGradient(0,0,W,H);
    g.addColorStop(0,'rgba(37,99,235,0.12)'); g.addColorStop(1,'rgba(12,18,32,0.55)');
    ctx.fillStyle = g; ctx.fillRect(0,0,W,H);
    // particles
    ctx.globalCompositeOperation = 'lighter';
    for(const d of dots){
      d.x+=d.vx; d.y+=d.vy;
      if(d.x<-10||d.x>W+10) d.vx*=-1;
      if(d.y<-10||d.y>H+10) d.vy*=-1;
      ctx.beginPath(); ctx.arc(d.x,d.y,d.r,0,Math.PI*2);
      ctx.fillStyle = 'rgba(129,161,193,'+d.a+')'; ctx.fill();
    }
    ctx.globalCompositeOperation = 'source-over';
  }
  window.__loginParticles = { init, destroy:()=>{ cancelAnimationFrame(rafId); rafId=0; if(canvas) canvas.remove(); canvas=null; } };
})();
