/* ==========================================================================
   IAprovale — /Login submit handler
   MOCK for this phase: zero network calls, just navigates to ../App/.
   ========================================================================== */

"use strict";

document.getElementById("login-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  window.location.href = "../App/";
});
