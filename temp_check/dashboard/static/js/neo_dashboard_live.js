(function() {
  function $(sel) { return document.querySelector(sel); }
  function $all(sel) { return Array.from(document.querySelectorAll(sel)); }
  function text(el, v){ if(el) el.textContent = v; }

  function setupDropzone(sel, url, after){
    $all(sel).forEach(function(dz){
      var prevent = function(e){ e.preventDefault(); e.stopPropagation(); };
      ['drag','dragstart','dragend','dragover','dragenter','dragleave','drop'].forEach(function(ev){
        dz.addEventListener(ev, prevent, false);
      });
      ['dragover','dragenter'].forEach(function(){ dz.classList.add('is-over'); });
      ['dragleave','dragend','drop'].forEach(function(){ dz.classList.remove('is-over'); });
      dz.addEventListener('drop', function(e){
        var files = (e.dataTransfer && e.dataTransfer.files) ? Array.from(e.dataTransfer.files) : [];
        if(!files.length) return;
        var fd = new FormData();
        files.forEach(function(f){ fd.append('file', f); });
        fetch(url, { method:'POST', body: fd })
          .then(function(r){ return r.json().catch(function(){ return {ok:r.ok}; }); })
          .then(function(j){ if (after) after(j); })
          .catch(function(err){ console.error('upload failed', err); });
      }, false);
    });
  }

  function pick(obj, k, d){ return (obj && (k in obj)) ? obj[k] : d; }

  function renderMetrics(m){
    if(!m) return;
    text($('#mm-up-real'), pick(m,'uptime', pick(m,'updated', 0)) + 's');
    var cpu = pick(m, 'cpu_pct', null);
    var ram = pick(m, 'ram_pct', null);
    if(cpu !== null) text($('#mm-cpu-real'), cpu + '%');
    if(ram !== null) text($('#mm-ram-real'), ram + '%');
    text($('#live-guilds'), pick(m,'guilds', '0'));
    text($('#live-members'), pick(m,'members', '0'));
    text($('#live-online'), pick(m,'online', '0'));
    text($('#live-latency'), pick(m,'latency_ms', '0') + ' ms');
  }

  function fetchMetrics(){
    var eps = ['/dashboard/api/metrics','/api/live/stats'];
    var i = 0;
    function next(){
      if(i>=eps.length) return Promise.resolve(null);
      var ep = eps[i++];
      return fetch(ep).then(function(r){
        if(!r.ok) return next();
        return r.json();
      }).catch(function(){ return next(); });
    }
    return next();
  }

  function refreshMetrics(){ fetchMetrics().then(function(m){ renderMetrics(m); }); }

  function refreshPhash(){
    // replaced by phash:update listener;
 })
    .then(function(arr){
      var el = $('#phash-count');
      if(el) el.textContent = Array.isArray(arr) ? String(arr.length) : '0';
    }).catch(function(){});
  }

  function renderBans(items){
    var ol = $('#ban-feed'); if(!ol) return;
    ol.innerHTML = '';
    if(!items || !items.length){ ol.innerHTML = '<li>Tidak ada ban.</li>'; return; }
    items.forEach(function(it, idx){
      var who = it.user || ('<@'+(it.user_id||'?')+'>');
      var li = document.createElement('li');
      li.textContent = (idx+1)+'. '+who+' banned '+(it.when_str||'');
      ol.appendChild(li);
    });
  }
  function refreshBans(){
    var el = $('#ban-feed'); if(!el) return;
    fetch('/dashboard/api/bans?limit=10').then(function(r){return r.json()}).then(renderBans).catch(function(){ renderBans([]); });
  }

  document.addEventListener('DOMContentLoaded', function(){
    setupDropzone('#dropzone, .dropzone, [data-dropzone="dashboard"]', '/dashboard/upload', function(){ refreshMetrics(); });
    setupDropzone('#sec-dropzone, .sec-dropzone, [data-dropzone="security"]', '/dashboard/security/upload', function(){ refreshPhash(); });

    fetch('/api/ui-config').then(r=>r.json()).then(cfg=>{var ms=(cfg && cfg.poll_interval_ms)||3000; refreshMetrics(); setInterval(refreshMetrics, ms);}).catch(function(){ refreshMetrics(); setInterval(refreshMetrics, 3000); });
    refreshPhash();
    refreshBans(); setInterval(refreshBans, 10000);
  });
})();