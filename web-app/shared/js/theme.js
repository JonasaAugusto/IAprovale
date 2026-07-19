/* ==========================================================================
   IAprovale — shared theme toggle
   DEFERRED script. Wires #theme-toggle, mirrors homepage's
   applyTheme/currentTheme logic. Safe to include on every page even if
   #theme-toggle is missing.
   ========================================================================== */

"use strict";

const THEME_KEY = "cf-theme";
const root = document.documentElement;

function currentTheme() {
  return root.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

function applyTheme(theme) {
  root.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch (e) {
    /* localStorage indisponível (ex.: modo privado) — segue sem persistir */
  }
}

const themeToggle = document.getElementById("theme-toggle");
if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    applyTheme(currentTheme() === "dark" ? "light" : "dark");
  });
}
