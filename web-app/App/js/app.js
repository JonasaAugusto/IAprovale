"use strict";

(function () {
  var FOCUSABLE =
    'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function cfVisivel(el) {
    return !!el && el.getClientRects().length > 0;
  }

  function cfBackdropAberto() {
    var backdrops = document.querySelectorAll(".modal-backdrop");
    var aberto = null;
    for (var i = 0; i < backdrops.length; i++) {
      if (cfVisivel(backdrops[i])) aberto = backdrops[i];
    }
    return aberto;
  }

  window.cfModalAberto = function (dialogId) {
    document.body.classList.add("modal-open");
    var dialog = document.getElementById(dialogId);
    if (!cfVisivel(dialog)) return;
    var first = dialog.querySelector(FOCUSABLE);
    (first || dialog).focus({ preventScroll: true });
  };

  window.cfModalFechado = function (trigger) {
    if (cfBackdropAberto()) return;
    document.body.classList.remove("modal-open");
    if (cfVisivel(trigger) && typeof trigger.focus === "function") {
      trigger.focus({ preventScroll: true });
    }
  };

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

    async sair() {
      try {
        await window.cfApi.logout();
      } catch (e) {
      }
      try {
        sessionStorage.removeItem("cf-token");
        sessionStorage.removeItem("cf-user");
        sessionStorage.removeItem("cf-last-activity");
      } catch (e) {
      }
      window.location.href = "../Login/";
    },
  }));
});
