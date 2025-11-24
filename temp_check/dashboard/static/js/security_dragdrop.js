
(function(){
  const dz = document.getElementById('dropzone');
  const fi = document.getElementById('fileInput');
  if(!dz) return;
  dz.addEventListener('click', ()=> fi.click());
  dz.addEventListener('dragover', e=>{e.preventDefault(); dz.classList.add('hover')});
  dz.addEventListener('dragleave', ()=> dz.classList.remove('hover'));
  dz.addEventListener('drop', e=>{
    e.preventDefault(); dz.classList.remove('hover');
    const f = e.dataTransfer.files[0]; if(f) upload(f);
  });
  fi.addEventListener('change', ()=>{ if(fi.files[0]) upload(fi.files[0]) });
  async function upload(file){
    const fd = new FormData(); fd.append('file', file);
    const r = await fetch('/dashboard/security/upload',{method:'POST',body:fd});
    dz.textContent = r.ok ? ('Uploaded: '+file.name) : 'Upload failed';
  }
})();
