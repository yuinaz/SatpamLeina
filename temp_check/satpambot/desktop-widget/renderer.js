const ENDPOINT = process.env.WIDGET_BASE || 'http://localhost:10000';
const sel = id => document.getElementById(id);
const set = (dot, sub, ok, text) => { dot.classList.remove('ok','warn','err'); dot.classList.add(ok===true?'ok':(ok===null?'warn':'err')); sub.textContent = text; };
window.desk.onStatus((j)=> {
  if(!j || !j.ok){ set(sel('botDot'), sel('botSub'), false, 'Offline'); set(sel('renderDot'), sel('renderSub'), false, 'Error'); set(sel('upDot'), sel('upSub'), null, 'No key'); set(sel('envDot'), sel('envSub'), null, '-'); set(sel('userDot'), sel('userSub'), null, '-'); return; }
  const hb = j.bot || {}; const hbok = hb.ok === true; let guilds=0, user='-';
  try{ guilds = (hb.data && hb.data.guilds) ? hb.data.guilds.length : 0; }catch(e){}
  try{ user = (hb.data && hb.data.user) ? hb.data.user : '-'; }catch(e){}
  set(sel('botDot'), sel('botSub'), hbok, hbok?('Online · '+guilds+' guilds'): 'Offline');
  const renderOk = (j.render && j.render.ok) ? true : false; set(sel('renderDot'), sel('renderSub'), renderOk, renderOk? 'Healthy' : 'Down');
  const up = j.uptimerobot || {}; const upOk = (up.ok === null) ? null : !!up.ok; set(sel('upDot'), sel('upSub'), upOk, up.ok===null? 'No key' : (upOk? 'OK '+(up.note||''): 'Issue '+(up.note||'')));
  const env = j.env || '-'; set(sel('envDot'), sel('envSub'), true, env.toUpperCase());
  set(sel('userDot'), sel('userSub'), hbok?true:null, user);
});
document.getElementById('openBtn').addEventListener('click', ()=> window.desk.open((process.env.WIDGET_DASHBOARD || (ENDPOINT + '/dashboard')))); 
