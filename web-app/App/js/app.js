/* ==========================================================================
   IAprovale — /App shell store (Alpine.js CSP build)
   Registered on alpine:init so the component exists before Alpine scans the
   DOM. All logic lives here — the CSP build's HTML expressions may only
   reference properties/methods defined in this object (STACK.md sec 1/6).
   ========================================================================== */

"use strict";

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
  }));
});
