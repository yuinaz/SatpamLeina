(function(){ try{
  function resize(){ document.documentElement.style.setProperty('--vh', (window.innerHeight*0.01)+'px'); }
  window.addEventListener('resize', resize); resize();
  console.log('[hotfix_dashboard_size] applied');
} catch(e){} })();
