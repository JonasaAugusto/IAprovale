/* ==========================================================================
   IAprovale — shared boot script
   BLOCKING (load in <head>, no defer) so it runs before first paint.
   No inline script anywhere on the page depends on this file — keeps CSP
   script-src 'self' with no 'unsafe-inline'.
   ========================================================================== */

"use strict";

// Frame-busting — defense-in-depth against clickjacking (GitHub Pages cannot
// send X-Frame-Options / CSP frame-ancestors via <meta>; run this early).
if (window.top !== window.self) {
  window.top.location = window.self.location;
}

// Pre-paint theme application — avoids a flash of the wrong theme.
(function () {
  var stored = null;
  try {
    stored = localStorage.getItem("cf-theme");
  } catch (e) {
    /* localStorage indisponível (ex.: modo privado) — segue sem persistir */
  }
  var theme =
    stored ||
    (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light");
  document.documentElement.setAttribute("data-theme", theme);
})();
