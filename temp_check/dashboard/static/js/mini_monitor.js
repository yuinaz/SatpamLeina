(function(){
  function setText(id, text){ var el = document.getElementById(id); if(el) el.textContent = text; }
  function tick(){
    setText('mm-cpu', 'CPU: ' + (Math.random()*60+10).toFixed(0) + '%');
    setText('mm-ram', 'RAM: ' + (Math.random()*800+400).toFixed(0) + ' MB');
    setText('mm-uptime', 'Uptime: ' + Math.floor(performance.now()/1000) + 's');
  }
  setInterval(tick, 3000);
  tick();
  console.log('[mini_monitor] ready');
})();
