(function(){
  const $ = (s) => document.querySelector(s);
  const setTxt = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  async function getJSON(url){ try{ const r = await fetch(url,{cache:'no-store'}); return await r.json(); }catch(e){ return {}; } }
  async function tick(){
    const ping = await getJSON('/api/ping');
    const live = !!ping.ok;
    const badge = document.getElementById('live-badge');
    if (badge){ badge.classList.toggle('on', live); badge.textContent = live?'Live':'Offline'; }
    const m = await getJSON('/api/metrics');
    if (m && m.ok){
      setTxt('stat-guilds',   m.guild_count ?? 0);
      setTxt('stat-members',  m.member_count ?? 0);
      setTxt('stat-online',   m.online_count ?? 0);
      setTxt('stat-channels', m.channel_count ?? 0);
      setTxt('stat-threads',  m.thread_count ?? 0);
      setTxt('stat-latency',  (m.latency_ms ?? 0) + ' ms');
      document.dispatchEvent(new CustomEvent('metrics:update', {detail:m}));
    }
  }
  setInterval(tick, 2000);
  tick();
})();