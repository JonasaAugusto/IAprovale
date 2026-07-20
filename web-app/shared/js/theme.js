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
  }
}

const themeToggle = document.getElementById("theme-toggle");
if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    applyTheme(currentTheme() === "dark" ? "light" : "dark");
  });
}
