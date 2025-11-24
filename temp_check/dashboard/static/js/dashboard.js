async function j(url){ const r = await fetch(url,{cache:"no-store"}); return r.json(); }

async function refreshSummary(){
  try{
    const s = await j("/api/stats");
    document.getElementById("m-users").textContent = s.online ?? "--";
    document.getElementById("m-msg").textContent   = s.messages_today ?? "--";
    document.getElementById("m-warn").textContent  = s.warnings ?? "--";
    document.getElementById("m-uptime").textContent= s.uptime ?? "--";
  }catch(e){ /* silent */ }
}

let chart;
async function drawTraffic(){
  const el = document.getElementById("chart-traffic");
  if(!el) return;
  const d = await j("/api/traffic"); // { labels:[], values:[] }
  if(window.Chart && chart){ chart.destroy(); }
  if(!window.Chart){
    const s=document.createElement("script");
    s.src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js";
    s.onload = () => drawTraffic();
    document.body.appendChild(s);
    return;
  }
  chart = new Chart(el, {
    type:"line",
    data:{ labels:d.labels, datasets:[{ data:d.values, tension:.35, fill:false }]},
    options:{ plugins:{ legend:{ display:false }}, scales:{ x:{ grid:{ display:false }}, y:{ beginAtZero:true }}}
  });
}

async function refreshTopGuilds(){
  try{
    const d = await j("/api/top_guilds"); // [{name, count}]
    const ul = document.getElementById("top-guilds");
    ul.innerHTML = "";
    (d||[]).slice(0,6).forEach(g=>{
      const li=document.createElement("li");
      li.className="list-group-item d-flex justify-content-between align-items-center";
      li.textContent = g.name;
      const b=document.createElement("span"); b.className="badge bg-primary rounded-pill"; b.textContent=g.count;
      li.appendChild(b); ul.appendChild(li);
    });
  }catch(e){}
}

refreshSummary(); drawTraffic(); refreshTopGuilds();
setInterval(refreshSummary, 5000);
setInterval(refreshTopGuilds, 15000);
