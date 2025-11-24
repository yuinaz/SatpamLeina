
(function(){
  var origFetch = window.fetch;
  var lastJSON = null;
  var lastTS = 0;
  var MIN_MS = 5000;
  window.fetch = function(input, init){
    try {
      var url = (typeof input === "string") ? input : (input && input.url);
      if (typeof url === "string" && url.indexOf("/dashboard/api/metrics") >= 0) {
        var now = Date.now();
        if (now - lastTS < MIN_MS && lastJSON) {
          return Promise.resolve(new Response(JSON.stringify(lastJSON), {status: 200, headers: {"Content-Type":"application/json"}}));
        }
        return origFetch(input, init).then(function(res){
          lastTS = Date.now();
          try { res.clone().json().then(function(j){ lastJSON = j; }).catch(function(){}); } catch(e){}
          return res;
        });
      }
    } catch(e){}
    return origFetch(input, init);
  };
  document.addEventListener("visibilitychange", function(){
    MIN_MS = document.hidden ? 15000 : 5000;
  });
})();
