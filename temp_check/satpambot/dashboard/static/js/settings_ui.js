(function(){
  function $(sel){ return document.querySelector(sel); }
  const saveBtn = $('#save');
  const previewBtn = $('#preview');
  async function postJSON(url, data){
    const res = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data||{})});
    try { return await res.json(); } catch { return {ok: res.ok}; }
  }
  if (saveBtn){
    saveBtn.addEventListener('click', async ()=>{
      const payload = {}; // TODO: grab fields by id/name if ada
      const j = await postJSON('/api/ui-config', payload);
      alert(j && j.ok ? 'Saved!' : 'Save failed');
    });
  }
  if (previewBtn){
    previewBtn.addEventListener('click', ()=>{
      // Simple refresh to reflect new theme/background if backend applies immediately
      location.reload();
    });
  }
  
// FORM COLLECTOR
function collectFormPayload(scope){
  const data = {};
  const root = scope || document;
  const nodes = root.querySelectorAll('input, select, textarea');
  nodes.forEach(el => {
    const key = (el.name || el.id || '').trim();
    if(!key) return;
    if(el.type === 'checkbox'){
      data[key] = !!el.checked;
    }else if(el.type === 'file'){
      // skip here (ui-config currently expects JSON); handle upload via specific endpoint if needed
    }else{
      data[key] = el.value;
    }
  });
  // Canonicalize known keys if present
  if (data.Theme && !data.theme) data.theme = data.Theme;
  if (data.accent_color && !data.accent) data.accent = data.accent_color;
  if (data.bgMode && !data.bg_mode) data.bg_mode = data.bgMode;
  if (data.bgUrl && !data.bg_url) data.bg_url = data.bgUrl;
  if (data.applyLogin != null && !data.apply_login) data.apply_login = !!data.applyLogin;
  if (data.logoUrl && !data.logo_url) data.logo_url = data.logoUrl;
  return data;
}
console.log('[settings_ui] ready');
})();
