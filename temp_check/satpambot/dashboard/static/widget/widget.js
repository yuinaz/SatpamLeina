(function(){
  function el(t,c){var e=document.createElement(t); if(c) e.className=c; return e;}
  function render(root, s){
    root.innerHTML='';
    var card=el('div','spb-card'); root.appendChild(card);
    var row=el('div','spb-row'); card.appendChild(row);
    var dot=el('div','spb-dot '+(s.online?'green':'red')); row.appendChild(dot);
    var label=el('div','spb-label'); label.textContent = s.online? 'Online' : 'Offline'; row.appendChild(label);
    var sub=el('div','spb-sub'); sub.textContent = 'Guilds: '+(s.guilds||0); card.appendChild(sub);
    if(s.updated){ var sub2=el('div','spb-sub'); sub2.textContent='Updated: '+new Date(s.updated*1000).toLocaleString(); card.appendChild(sub2); }
  }
  function init(){
    var root = document.getElementById('spb-widget'); if(!root) return;
    var endpoint = root.getAttribute('data-endpoint') || '/heartbeat';
    var interval = parseInt(root.getAttribute('data-interval') || '60000',10);
    function tick(){
      fetch(endpoint).then(r=>r.json()).then(j=>{
        var st={online:false,guilds:0};
        if(j && j.ok && j.data){ 
          var ts=j.data.ts||0; var age=(Date.now()/1000)-ts; 
          var grace=120;
          st.online = age<=grace; st.guilds=(j.data.guilds||[]).length; st.updated=ts;
        }
        render(root, st);
      }).catch(()=> render(root, {online:false,guilds:0}));
    }
    tick(); setInterval(tick, Math.max(interval, 30000));
  }
  document.addEventListener('DOMContentLoaded', init);
})();