\
// Drag&Drop Phish Hash Uploader (patched)
// - Only POST to /dashboard/api/phash/upload
// - Shows success message under dropzone (#drop-log) instead of floating only
(function(){
  const zone = document.querySelector('#dropZone, .dropzone');
  if(!zone){ return; }

  const logBox = document.querySelector('#drop-log, #dz-result');
  function logLine(msg){
    if(!logBox) return;
    const el = document.createElement('div');
    el.textContent = msg;
    el.style.padding = '4px 6px';
    el.style.borderRadius = '8px';
    el.style.marginTop = '4px';
    el.style.background = msg.startsWith('✅') ? 'rgba(16,185,129,.12)' : 'rgba(239,68,68,.12)';
    el.style.color = msg.startsWith('✅') ? '#10b981' : '#ef4444';
    logBox.prepend(el);
  }

  function postFile(file){
    const fd = new FormData();
    fd.append('file', file, file.name || 'image');
    return fetch('/dashboard/api/phash/upload', { method: 'POST', body: fd })
      .then(r => r.json().catch(()=>({})) )
      .then(j => {
        if(j && (j.ok || j.status==='ok')){
          logLine('✅ ' + (file.name || 'file') + (j.phash ? (' → ' + j.phash) : ''));
          // Optional refresh list
          }else{
          logLine('❌ ' + (file.name || 'file') + ' → ' + (j && j.error ? j.error : 'upload failed'));
        }
      }).catch(e => logLine('❌ ' + (file.name || 'file') + ' → ' + e));
  }

  function handleFiles(files){
    [...files].forEach(f => postFile(f));
  }

  zone.addEventListener('dragover', function(e){ e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', function(){ zone.classList.remove('dragover'); });
  zone.addEventListener('drop', function(e){
    e.preventDefault();
    zone.classList.remove('dragover');
    if(e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length){
      handleFiles(e.dataTransfer.files);
    }
  });

  // Optional: also handle paste
  document.addEventListener('paste', function(e){
    if(!e.clipboardData) return;
    const files = [];
    for(const item of e.clipboardData.items){
      if(item.kind === 'file'){
        const f = item.getAsFile();
        if(f) files.push(f);
      }
    }
    if(files.length) handleFiles(files);
  });
})();
// Listen to global phash poller updates
window.addEventListener('phash:update', (e) => {
  const data = e.detail || {};
  const elCount = document.querySelector('[data-phash-count]');
  if (elCount) elCount.textContent = String(data.count || 0);
  const elAutoban = document.querySelector('[data-autoban-badge]');
  if (elAutoban) elAutoban.textContent = data.autoban ? 'ON' : 'OFF';
});
