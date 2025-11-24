(function(){
  function $(sel){ return document.querySelector(sel); }
  const drop = $('#phish-drop');
  const fileInput = $('#phish-file');
  const urlInput = $('#phish-url');
  const submitBtn = $('#phish-submit');
  const result = $('#phish-result');

  async function addPhash({file, url}){
    try{
      const fd = new FormData();
      if (file) fd.append('file', file);
      if (url) fd.append('url', url);
      const res = await fetch('/api/phish/phash', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || ('HTTP '+res.status));
      result.textContent = 'OK: ' + (data.hash || '(added)') + ' ('+(data.count||'?')+')';
      result.style.color = 'var(--ok-color,#39c06b)';
    }catch(e){
      console.error(e);
      result.textContent = 'Error: ' + e.message;
      result.style.color = 'var(--err-color,#e05d5d)';
    }finally{
      setTimeout(()=>{ if(result) result.textContent=''; }, 4000);
    }
  }

  if (drop){
    drop.addEventListener('dragover', (e)=>{ e.preventDefault(); drop.classList.add('hover'); });
    drop.addEventListener('dragleave', ()=> drop.classList.remove('hover'));
    drop.addEventListener('drop', (e)=>{
      e.preventDefault(); drop.classList.remove('hover');
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]){
        addPhash({file: e.dataTransfer.files[0]});
      }
    });
  }

  if (submitBtn){
    submitBtn.addEventListener('click', ()=>{
      const f = (fileInput && fileInput.files && fileInput.files[0]) ? fileInput.files[0] : null;
      const u = (urlInput && urlInput.value || '').trim() || null;
      if (!f && !u){
        result.textContent = 'Pilih file atau isikan URL dulu.';
        result.style.color = 'var(--warn-color,#e0b84e)';
        return;
      }
      addPhash({file: f, url: u});
    });
  }

  console.log('[phish_drop] ready');
})();

// Ensure refresh after upload
if (window.__phashPoller && window.__phashPoller.requestNow) { window.__phashPoller.requestNow(); }
