/* ==========================================================================
   IAprovale — shared auth guard
   BLOCKING (load in <head>, no defer) so it runs before first paint.
   Só é carregado no /App (o /Login não é protegido) — checa sessionStorage
   por token + timestamp da última atividade e redireciona pro /Login antes
   de qualquer pintura de conteúdo autenticado, caso ausente/expirado.
   Deve ser carregado no <head>, depois de boot.js (tema/frame-busting) e
   antes do CDN do Alpine.
   ========================================================================== */

"use strict";

(function () {
  var SIX_HOURS_MS = 6 * 60 * 60 * 1000;

  // O cutoff de 6h é 100% client-side (o backend nunca expira a sessão por
  // relógio — token opaco revogado só em /auth/logout ou desativação de
  // usuário) — por isso essa checagem tem que rodar antes de qualquer
  // pintura de conteúdo autenticado, não depois.
  var token = null;
  var lastActivity = null;
  try {
    token = sessionStorage.getItem("cf-token");
    lastActivity = Number(sessionStorage.getItem("cf-last-activity"));
  } catch (e) {
    /* sessionStorage indisponível (ex.: modo privado) — fail closed, trata como deslogado */
  }

  var expired = !token || !lastActivity || Date.now() - lastActivity > SIX_HOURS_MS;

  if (expired) {
    try {
      sessionStorage.removeItem("cf-token");
      sessionStorage.removeItem("cf-user");
      sessionStorage.removeItem("cf-last-activity");
    } catch (e) {
      /* ignore */
    }
    // replace (não href) — não polui o histórico do navegador com a página protegida.
    window.location.replace("../Login/");
  }
})();
