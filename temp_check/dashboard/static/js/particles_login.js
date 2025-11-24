const c = document.getElementById('particles');
const ctx = c.getContext('2d');
let W, H; const dots = [];
function resize(){
  W = c.width = window.innerWidth;
  H = c.height = window.innerHeight;
}
window.addEventListener('resize', resize); resize();

for(let i=0;i<80;i++){
  dots.push({x:Math.random()*W,y:Math.random()*H,vx:(Math.random()-0.5)*0.6,vy:(Math.random()-0.5)*0.6,r:1+Math.random()*2});
}
function step(){
  ctx.clearRect(0,0,W,H);
  const grad = ctx.createRadialGradient(W/2,H/2,0,W/2,H/2,Math.max(W,H)/1.2);
  grad.addColorStop(0,'rgba(0,0,0,0)');
  grad.addColorStop(1,'rgba(0,0,0,0.35)');
  ctx.fillStyle = grad; ctx.fillRect(0,0,W,H);

  for(const d of dots){
    d.x+=d.vx; d.y+=d.vy;
    if(d.x<0||d.x>W) d.vx*=-1;
    if(d.y<0||d.y>H) d.vy*=-1;
    ctx.beginPath(); ctx.arc(d.x,d.y,d.r,0,Math.PI*2); ctx.fillStyle='rgba(255,255,255,0.8)'; ctx.fill();
  }
  for(let i=0;i<dots.length;i++){
    for(let j=i+1;j<dots.length;j++){
      const a=dots[i], b=dots[j];
      const dx=a.x-b.x, dy=a.y-b.y; const dist=Math.hypot(dx,dy);
      if(dist<110){
        ctx.globalAlpha = 1-Math.min(1,dist/110);
        ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.strokeStyle='rgba(255,255,255,0.4)'; ctx.lineWidth=0.6; ctx.stroke();
        ctx.globalAlpha = 1;
      }
    }
  }
  requestAnimationFrame(step);
}
step();
