// Aman kalau sudah ada; file ini hanya memastikan theme.css terpasang
(function(){
  try{
    if(!document.querySelector('link[href*="themes/gtake/theme.css"]')){
      var l=document.createElement('link'); l.rel='stylesheet';
      l.href='/dashboard-static/themes/gtake/theme.css'; document.head.appendChild(l);
    }
  }catch(e){}
})();
