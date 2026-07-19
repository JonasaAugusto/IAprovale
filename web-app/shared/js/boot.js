/* ==========================================================================
   IAprovale — shared boot script
   BLOCKING (load in <head>, no defer) so it runs before first paint.
   No inline script anywhere on the page depends on this file — keeps CSP
   script-src 'self' with no 'unsafe-inline'.
   ========================================================================== */

"use strict";

// Frame-busting — defense-in-depth against clickjacking (GitHub Pages cannot
// send X-Frame-Options / CSP frame-ancestors via <meta>; run this early).
// Em try/catch: num <iframe sandbox="allow-scripts"> (sem
// allow-top-navigation) a navegação do top lança SecurityError — sem o
// catch, a exceção abortava o resto deste arquivo e o tema pré-paint abaixo
// nunca rodava (página inteira sem design system). location.replace() evita
// ainda poluir o histórico do frame pai. NOTA Fase 7 (auth real): adotar o
// padrão OWASP completo (conteúdo oculto por padrão, revelado só quando não
// enquadrado) antes de servir telas autenticadas.
try {
  if (window.top !== window.self) {
    window.top.location.replace(window.self.location.href);
  }
} catch (e) {
  /* enquadrado + sandboxed: busting bloqueado; segue pro tema mesmo assim */
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
