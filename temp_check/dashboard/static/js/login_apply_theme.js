(function(){
  window.addEventListener('DOMContentLoaded', function(){
    try{
      document.body.classList.add('login-page');
      var user = document.querySelector('input[name="username"],input[type="email"],input[type="text"]');
      if(user && !user.value) user.focus();
    }catch(e){}
  });
})();
