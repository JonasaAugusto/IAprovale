"use strict";

try {
  if (window.top !== window.self) {
    window.top.location.replace(window.self.location.href);
  }
} catch (e) {
}

(function () {
  var stored = null;
  try {
    stored = localStorage.getItem("cf-theme");
  } catch (e) {
  }
  var theme =
    stored === "dark" || stored === "light"
      ? stored
      : (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light");
  document.documentElement.setAttribute("data-theme", theme);
})();
