(function () {
  if (window.__phashPoller) return;
  try {
    var path = (window.location && window.location.pathname) || '';
    var onDashboard = path.indexOf('/dashboard') === 0 && path !== '/dashboard/login' && path.indexOf('/login') === -1;
    if (!onDashboard) return;
  } catch (e) {}

  var CHANNEL_NAME = 'phash-channel';
  var LS_KEY = 'phash_poller_leader';
  var HEARTBEAT_MS = 4000;
  var LEASE_MS = 10000;
  var POLL_MS_DEFAULT = 5000;

  var bc = null;
  try { bc = new BroadcastChannel(CHANNEL_NAME); } catch (e) {}

  function now() { return Date.now(); }
  function getLease() { try { var raw = localStorage.getItem(LS_KEY); return raw?JSON.parse(raw):null; } catch(e){ return null; } }
  function setLease(ownerId) { try { var p={id:ownerId,until:now()+LEASE_MS}; localStorage.setItem(LS_KEY, JSON.stringify(p)); return p; } catch(e){ return null; } }
  function isLeaseValid(l){ return l && l.until && l.until>now(); }
  function tryBecomeLeader(){ var c=getLease(); if(!isLeaseValid(c)){ setLease(MY_ID); c=getLease(); } return c && c.id===MY_ID && isLeaseValid(c); }
  function renewIfLeader(){ var c=getLease(); if(c && c.id===MY_ID) setLease(MY_ID); }

  var MY_ID = Math.random().toString(36).slice(2) + String(Date.now());
  var interval=null, abortCtl=null, last=null, isLeader=false;

  async function fetchOnce(signal){ const res=await fetch('/api/phish/phash',{signal,cache:'no-store'}); if(!res.ok) return null; return await res.json(); }
  function broadcast(d){ try{ if(bc) bc.postMessage({type:'phash:update', payload:d}); }catch(e){} }
  function handleBroadcast(ev){ try{ var m=(ev&&ev.data)||{}; if(m&&m.type==='phash:update'){ last=m.payload||null; window.dispatchEvent(new CustomEvent('phash:update',{detail:last})); } }catch(e){} }

  async function leaderTick(){ try{ if(!isLeader) return; if(abortCtl) abortCtl.abort(); abortCtl=new AbortController(); const data=await fetchOnce(abortCtl.signal); if(!data) return; last=data; window.dispatchEvent(new CustomEvent('phash:update',{detail:data})); broadcast(data);}catch(e){} }
  function startLeader(){ stopLeader(); try{ leaderTick(); }catch(e){} var ms=(window.__uiConfig&&window.__uiConfig.poll_interval_ms)||POLL_MS_DEFAULT; interval=setInterval(leaderTick, ms); }
  function stopLeader(){ if(interval) clearInterval(interval); interval=null; if(abortCtl) abortCtl.abort(); }

  document.addEventListener('visibilitychange', function(){ if(document.visibilityState==='hidden'){ stopLeader(); } else if(isLeader){ startLeader(); } });

  var hb=setInterval(function(){ var c=getLease(); var v=isLeaseValid(c); if(isLeader){ if(!v || (c&&c.id!==MY_ID)){ isLeader=false; stopLeader(); } else { renewIfLeader(); } } else { if(!v){ if(tryBecomeLeader()){ isLeader=true; startLeader(); } } } }, HEARTBEAT_MS);
  try{ if(bc) bc.onmessage=handleBroadcast; }catch(e){}

  if(tryBecomeLeader()){ isLeader=true; startLeader(); }
  function requestNow(){ if(isLeader){ leaderTick(); } }
  window.__phashPoller = { requestNow: requestNow, isLeader: function(){return isLeader;}, getLast: function(){return last;} };

  window.addEventListener('beforeunload', function(){ try{ clearInterval(hb);}catch(e){} stopLeader(); });
})();