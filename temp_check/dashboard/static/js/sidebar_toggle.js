(function(){
  var btn=document.querySelector('[data-action="toggle-sidebar"]');
  var root=document.documentElement;
  if(btn){ btn.addEventListener('click', function(){ root.classList.toggle('sidebar-collapsed'); }); }
  console.log('[sidebar_toggle] ready');
})();
