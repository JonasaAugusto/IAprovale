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

    select(t) {
      this.tab = t;
    },

    // MOCK: o modal de Perfil (#perfil-modal) é preenchido pelo plano 06-03.
    // Aqui só existe o gatilho — sem estado/abertura real ainda.
    openPerfil() {
      // no-op nesta fase — placeholder documentado, ver #perfil-modal no HTML.
    },
  }));
});
