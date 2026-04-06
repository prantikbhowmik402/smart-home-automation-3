function showLogin() {
    document.getElementById("loginForm").style.display = "block";
    document.getElementById("signupForm").style.display = "none";
  }
  
  function showSignup() {
    document.getElementById("loginForm").style.display = "none";
    document.getElementById("signupForm").style.display = "block";
  }
  
  document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("loginForm").addEventListener("submit", function (e) {
      e.preventDefault();
      const inputs = this.querySelectorAll("input");
      const email = inputs[0].value;
      const password = inputs[1].value;
  
      fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.success) {
            window.location.href = "/";
          } else {
            alert(data.message);
          }
        });
    });
  
    document.getElementById("signupForm").addEventListener("submit", function (e) {
      e.preventDefault();
      const inputs = this.querySelectorAll("input");
      const name = inputs[0].value;
      const email = inputs[1].value;
      const password = inputs[2].value;
  
      fetch("/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      })
        .then((res) => res.json())
        .then((data) => alert(data.message));
    });
  });
  