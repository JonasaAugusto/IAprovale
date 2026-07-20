/* ==========================================================================
   IAprovale — /App shell store (Alpine.js CSP build)
   Registered on alpine:init so the component exists before Alpine scans the
   DOM. All logic lives here — the CSP build's HTML expressions may only
   reference properties/methods defined in this object (STACK.md sec 1/6).
   ========================================================================== */

"use strict";

/* --------------------------- FOCO DOS MODAIS --------------------------------
   Contrato de modal acessível compartilhado pelos 4 modais Alpine do /App
   (tutorial, revelar senha, renomear, confirmação) — paridade com o padrão
   já estabelecido em homepage/js/main.js: foco entra no diálogo ao abrir,
   Tab fica preso dentro dele, foco volta ao gatilho ao fechar e o scroll do
   body é travado (body.modal-open). Os stores (busca.js/admin.js) chamam
   cfModalAberto/cfModalFechado via $nextTick, depois do Alpine aplicar o
   x-show. Vanilla JS no escopo global (CSP-safe, sem eval). */

(function () {
  var FOCUSABLE =
    'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

  // Renderizado de fato na página (cobre display:none em qualquer ancestral —
  // offsetParent não serve aqui: os backdrops são position:fixed).
  function cfVisivel(el) {
    return !!el && el.getClientRects().length > 0;
  }

  function cfBackdropAberto() {
    var backdrops = document.querySelectorAll(".modal-backdrop");
    var aberto = null;
    for (var i = 0; i < backdrops.length; i++) {
      if (cfVisivel(backdrops[i])) aberto = backdrops[i]; // último visível = topo
    }
    return aberto;
  }

  // Chamar via $nextTick depois de abrir (x-show já aplicado): trava o
  // scroll e move o foco pro primeiro focável do diálogo (ou pro próprio
  // diálogo, que tem tabindex="-1").
  window.cfModalAberto = function (dialogId) {
    document.body.classList.add("modal-open");
    var dialog = document.getElementById(dialogId);
    if (!cfVisivel(dialog)) return;
    var first = dialog.querySelector(FOCUSABLE);
    (first || dialog).focus({ preventScroll: true });
  };

  // Chamar via $nextTick depois de fechar: se nenhum modal segue visível
  // (cadeias como confirmação -> revelar senha mantêm o lock), destrava o
  // scroll e devolve o foco ao gatilho original (se ele ainda existe/aparece).
  window.cfModalFechado = function (trigger) {
    if (cfBackdropAberto()) return;
    document.body.classList.remove("modal-open");
    if (cfVisivel(trigger) && typeof trigger.focus === "function") {
      trigger.focus({ preventScroll: true });
    }
  };

  // Focus trap: com um modal aberto, Tab/Shift+Tab circulam só dentro dele.
  // aria-modal="true" passa a ser verdade de fato, não só declaração.
  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Tab") return;
    var top = cfBackdropAberto();
    if (!top) return;
    var focusables = Array.prototype.filter.call(
      top.querySelectorAll(FOCUSABLE),
      cfVisivel
    );
    if (focusables.length === 0) {
      ev.preventDefault();
      return;
    }
    var first = focusables[0];
    var last = focusables[focusables.length - 1];
    var active = document.activeElement;
    var dentro = top.contains(active);
    if (ev.shiftKey && (!dentro || active === first)) {
      ev.preventDefault();
      last.focus();
    } else if (!ev.shiftKey && (!dentro || active === last)) {
      ev.preventDefault();
      first.focus();
    }
  });
})();

document.addEventListener("alpine:init", () => {
  Alpine.data("appShell", () => ({
    tab: "busca",
    // Guarda a aba de onde o usuário veio antes de abrir o Perfil, pra
    // "Voltar" levar de volta pra Busca/Admin em vez de sempre cair na
    // primeira aba. Perfil não é uma aba do tabbar (nav.app-tabbar só lista
    // Busca/Admin) — é acessado só pelo botão "Perfil" do header, mas troca
    // o painel principal do mesmo jeito que as abas (#panel-perfil abaixo,
    // igual #panel-busca/#panel-admin), reaproveitando o padrão já
    // estabelecido de x-data aninhado lendo `tab` do escopo pai (appShell).
    previousTab: "busca",

    select(t) {
      this.tab = t;
    },

    openPerfil() {
      if (this.tab !== "perfil") {
        this.previousTab = this.tab;
      }
      this.tab = "perfil";
    },

    voltarDoPerfil() {
      this.tab = this.previousTab;
    },

    // Server-first logout (paridade com desktop/app/main.py _logout/_finish_logout):
    // revoga a sessão no backend PRIMEIRO, depois limpa local — e limpa local
    // em ambos os caminhos (sucesso E falha da chamada), pra nunca deixar um
    // token morto no sessionStorage por causa de uma falha de rede.
    async sair() {
      try {
        await window.cfApi.logout();
      } catch (e) {
        /* revogação server-side falhou (rede/timeout) — limpa local mesmo assim */
      }
      try {
        sessionStorage.removeItem("cf-token");
        sessionStorage.removeItem("cf-user");
        sessionStorage.removeItem("cf-last-activity");
      } catch (e) {
        /* sessionStorage indisponível — segue pro redirect de qualquer forma */
      }
      window.location.href = "../Login/";
    },
  }));
});
