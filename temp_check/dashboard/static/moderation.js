const WL = {
  async reload(){
    const r = await fetch('/api/whitelist'); if(!r.ok) return;
    const data = await r.json();
    const ul = document.getElementById('wl-list'); ul.innerHTML='';
    (data.list||[]).forEach(id=>{
      const li = document.createElement('li');
      li.textContent = id + ' ';
      const x = document.createElement('button'); x.textContent='Hapus'; x.style.marginLeft='6px';
      x.onclick = async ()=>{
        await fetch('/api/whitelist', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({remove:[id]})});
        WL.reload();
      };
      li.appendChild(x);
      ul.appendChild(li);
    });
  },
  async add(){
    const v = document.getElementById('wl-input').value.trim();
    if(!v) return;
    const ids = v.split(',').map(s=>s.trim()).filter(Boolean);
    await fetch('/api/whitelist', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({add: ids})});
    document.getElementById('wl-input').value='';
    WL.reload();
  }
};

const UP = {
  file: null,
  init(){
    const drop = document.getElementById('drop');
    const file = document.getElementById('file');
    drop.addEventListener('click', ()=> file.click());
    drop.addEventListener('dragover', e=>{e.preventDefault(); drop.style.background='#eef2ff'});
    drop.addEventListener('dragleave', e=>{drop.style.background='#f8fafc'});
    drop.addEventListener('drop', e=>{
      e.preventDefault(); drop.style.background='#f8fafc';
      if(e.dataTransfer.files && e.dataTransfer.files[0]){
        UP.file = e.dataTransfer.files[0];
        document.getElementById('dropNote').textContent = UP.file.name + ' siap diunggah';
      }
    });
    file.addEventListener('change', e=>{
      if(file.files && file.files[0]){
        UP.file = file.files[0];
        document.getElementById('dropNote').textContent = UP.file.name + ' siap diunggah';
      }
    });
  },
  async send(){
    const status = document.getElementById('status');
    const uid = document.getElementById('target_id').value.trim();
    const reason = document.getElementById('reason').value.trim();
    if(!uid){ status.textContent='User ID wajib diisi.'; return;}
    if(!UP.file){ status.textContent='Pilih/seret gambar dulu.'; return;}
    const fd = new FormData();
    fd.append('user_id', uid);
    fd.append('reason', reason);
    fd.append('image', UP.file);
    const r = await fetch('/api/phish-report', {method:'POST', body: fd});
    if(r.ok){
      status.textContent='✅ Bukti terkirim. Bot akan memproses.';
      document.getElementById('target_id').value=''; document.getElementById('reason').value='';
      document.getElementById('dropNote').textContent='Lepaskan gambar di sini atau klik untuk memilih.';
      UP.file = null;
    } else {
      status.textContent='❌ Gagal kirim.';
    }
  }
};

window.addEventListener('DOMContentLoaded', ()=>{ WL.reload(); UP.init(); });
