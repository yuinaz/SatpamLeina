(function(){
  function enableList(list){
    if(!list) return;
    var placeholder = document.createElement('div');
    placeholder.className = 'dnd-placeholder';
    var dragEl = null;
    list.querySelectorAll('[data-id], li, .dnd-item').forEach(function(item){
      item.setAttribute('draggable','true');
      item.classList.add('dnd-item');
      item.addEventListener('dragstart', function(e){
        dragEl = item;
        item.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        try{ e.dataTransfer.setData('text/plain', item.dataset.id || item.id || item.textContent.trim()); }catch(_){}
        item.parentNode.insertBefore(placeholder, item.nextSibling);
      });
      item.addEventListener('dragend', function(){
        item.classList.remove('dragging');
        if(placeholder.parentNode) placeholder.parentNode.replaceChild(item, placeholder);
        dragEl = null;
        save();
      });
    });
    list.addEventListener('dragover', function(e){
      e.preventDefault();
      var target = e.target.closest('.dnd-item');
      if(!target || target===placeholder || target===dragEl) return;
      var rect = target.getBoundingClientRect();
      var before = (e.clientY - rect.top) < rect.height / 2;
      if(before) target.parentNode.insertBefore(placeholder, target);
      else target.parentNode.insertBefore(placeholder, target.nextSibling);
    });
    function save(){
      var items = Array.from(list.querySelectorAll('.dnd-item')).map(function(el){
        return el.dataset.id || el.id || el.textContent.trim();
      });
      fetch('/api/security/reorder',{
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({list: list.getAttribute('data-dnd-list') || 'security', items: items})
      }).catch(function(){});
      console.log('[dnd_security] saved order', items);
    }
  }
  // auto-bind common targets
  enableList(document.querySelector('[data-dnd-list="security"]') || document.querySelector('#security-list') || document.querySelector('.security-list'));
  console.log('[dnd_security] ready');
})();
