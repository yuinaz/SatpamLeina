
// Remove any UI controls that literally show "OPTION" text.
(function(){
  function purgeOptions(){
    var candidates = Array.from(document.querySelectorAll("button, a, .btn, .dropdown-toggle, [role='button']"));
    candidates.forEach(function(el){
      if (!el || !el.textContent) return;
      var t = (el.textContent || "").trim().toUpperCase();
      if (t === "OPTION" || t === "OPTIONS") {
        var parent = el.closest("#option, #options, #option-menu, .option, .options, .options-menu") || el;
        if (parent && parent.remove) parent.remove();
      }
    });
    ["option","options","option-menu","options-menu"].forEach(function(id){
      var n = document.getElementById(id);
      if (n && n.remove) n.remove();
    });
  }
  document.addEventListener("DOMContentLoaded", purgeOptions);
  setTimeout(purgeOptions, 500);
  setTimeout(purgeOptions, 1500);
})();
