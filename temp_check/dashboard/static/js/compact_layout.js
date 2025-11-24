
(function(){
  document.documentElement.classList.add("compact");
  function makeChip(k, v){ var c=document.createElement("div"); c.className="stat-chip";
    var lk=document.createElement("div"); lk.className="k"; lk.textContent=k;
    var lv=document.createElement("div"); lv.className="v"; lv.textContent=v;
    c.appendChild(lk); c.appendChild(lv); return c; }
  function injectChips(){
    var labels=["Guilds","Members","Online","Channels","Threads","Latency"];
    var root=document.querySelector('[data-rt-counters]')||document.querySelector(".rt-counters")||document.body;
    if(!root||document.getElementById("compact-stat-strip")) return;
    var chips=[]; labels.forEach(function(lbl){
      var el=[].find.call(root.querySelectorAll("*"), function(n){ try{return n.textContent.trim().toLowerCase().startsWith(lbl.toLowerCase());}catch(e){return false;} });
      if(!el) return; var m=(el.textContent.match(/(\d+(\.\d+)?)/)||[])[1];
      if(!m&&el.nextElementSibling){ m=(el.nextElementSibling.textContent.match(/(\d+(\.\d+)?)/)||[])[1]; }
      chips.push(makeChip(lbl, m||"0"));
    });
    if(!chips.length) return; var holder=document.createElement("div"); holder.className="stat-strip"; holder.id="compact-stat-strip";
    chips.forEach(function(c){ holder.appendChild(c); }); var main=document.querySelector("#main, .container-fluid, main, .content, .dashboard, .page-content")||document.body;
    main.insertBefore(holder, main.firstChild);
  }
  document.querySelectorAll('.col-lg-6, .col-xl-6').forEach(function(el){ el.classList.remove('col-lg-6'); el.classList.remove('col-xl-6'); el.classList.add('col-lg-5'); el.classList.add('col-xl-5'); });
  document.querySelectorAll('.row').forEach(function(r){ r.style.flexWrap='wrap'; });
  if(document.readyState==="loading"){ document.addEventListener("DOMContentLoaded", function(){ setTimeout(injectChips, 100); }); } else { setTimeout(injectChips, 100); }
})();
