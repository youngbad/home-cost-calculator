// Auto-dismiss flash messages after 4 seconds
document.addEventListener("DOMContentLoaded", function () {
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = "opacity 0.5s ease";
      alert.style.opacity = "0";
      setTimeout(function () { alert.remove(); }, 500);
    }, 4000);
  });

  // Dark mode toggle
  const themeToggle = document.getElementById("theme-toggle");
  if (themeToggle) {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    themeToggle.textContent = currentTheme === "dark" ? "☀️" : "🌙";

    themeToggle.addEventListener("click", function () {
      let theme = document.documentElement.getAttribute("data-theme");
      let newTheme = theme === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", newTheme);
      localStorage.setItem("theme", newTheme);
      themeToggle.textContent = newTheme === "dark" ? "☀️" : "🌙";
      
      // Dispatch event for charts to update
      window.dispatchEvent(new Event('themeChanged'));
    });
  }
});
