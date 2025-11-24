// ui_theme_bridge.js - apply theme/background (image/particles/video) to login/dashboard
(function(){
  const root = document.documentElement.style;
  function applyColors(colors){
    if(!colors) return;
    root.setProperty("--bg", colors.bg);
    root.setProperty("--text", colors.text);
    root.setProperty("--panel", colors.panel);
    root.setProperty("--line", colors.line);
    root.setProperty("--muted", colors.muted);
  }
  function escapeCssUrl(u){return u.replace(/["'()\\s]/g, c => '\\\\' + c);}
  function setBgImage(url){
    document.body.style.backgroundImage = "linear-gradient(rgba(0,0,0,.25), rgba(0,0,0,.25)), url(\""+escapeCssUrl(url)+"\")";
    document.body.style.backgroundSize = "cover"; document.body.style.backgroundPosition="center";
  }
  function setVideo(url){
    var v = document.getElementById("bgVideo"); if(!v) return;
    v.src = url; v.style.display = "block";
  }
  function initParticles(preset){
    if(window.particlesJS){
      var config = {
        "particles":{"number":{"value":60},"size":{"value":3},"move":{"speed":2},"line_linked":{"enable":preset==='lines'}}
      };
      if(preset==='snow'){config.particles.number.value=120; config.particles.size.value=2;}
      if(preset==='bubbles'){config.particles.number.value=40; config.particles.size.value=8;}
      particlesJS("particles-js", config);
      return;
    }
    if(window.tsParticles){
      window.tsParticles.load({id:"particles-js", options:{particles:{number:{value:80},size:{value:3},move:{speed:2}}}});
      return;
    }
  }
  async function fetchConfig() {
    try { const r1 = await fetch("/api/ui-settings", {cache:"no-store"}); if (r1.ok) return await r1.json(); } catch(e) {}
    try { const r2 = await fetch("/api/ui-config",   {cache:"no-store"}); if (r2.ok) return await r2.json(); } catch(e) {}
    return null;
  }
  fetchConfig().then(ui=>{
    if(!ui) return;
    if(ui.apply_to_login === false) return;
    var themes = ui._themes||{}; 
    var colors = themes[ui.theme] || themes["dark"] || {"bg":"#0b111b","text":"#e6edf3","panel":"#111827","line":"#1f2937","muted":"#9aa4b2"};
    applyColors(colors);
    if(ui.accent){ root.setProperty("--accent", ui.accent); }
    var mode = ui.bg_mode || "image";
    if(mode==="video" && ui.video_url){ setVideo(ui.video_url); }
    else if(mode==="particles"){ initParticles(ui.particles_preset || "default"); }
    else if(ui.bg_url){ setBgImage(ui.bg_url); }
  }).catch(()=>{});
})();