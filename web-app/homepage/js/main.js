"use strict";

const LOGIN_REDIRECT_URL = "Login/";

const CONTACT_FORM_ACTION = "https://submit-form.com/1pIuu489V";

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
  const feedbackDark = document.getElementById("feedback-dark");
  if (feedbackDark) feedbackDark.value = theme === "dark" ? "true" : "false";
}

applyTheme(currentTheme());

document.getElementById("theme-toggle").addEventListener("click", () => {
  applyTheme(currentTheme() === "dark" ? "light" : "dark");
});

const openModals = [];

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function openModal(backdrop, triggerEl) {
  if (!backdrop || !backdrop.hasAttribute("hidden")) return;

  backdrop.dataset.triggerId = triggerEl && triggerEl.id ? triggerEl.id : "";
  backdrop.removeAttribute("hidden");
  void backdrop.offsetWidth;
  backdrop.classList.add("is-open");

  openModals.push(backdrop);
  document.body.classList.add("modal-open");

  const dialog = backdrop.querySelector(".modal");
  const firstFocusable = dialog.querySelector(FOCUSABLE);
  (firstFocusable || dialog).focus({ preventScroll: true });
}

function closeModal(backdrop) {
  if (!backdrop || backdrop.hasAttribute("hidden")) return;

  backdrop.classList.remove("is-open");

  const idx = openModals.indexOf(backdrop);
  if (idx !== -1) openModals.splice(idx, 1);
  if (openModals.length === 0) document.body.classList.remove("modal-open");

  const finish = () => {
    backdrop.setAttribute("hidden", "");
    const trigger = backdrop.dataset.triggerId
      ? document.getElementById(backdrop.dataset.triggerId)
      : null;
    if (trigger && openModals.length === 0) trigger.focus();
  };

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduceMotion) {
    finish();
  } else {
    let done = false;
    const onEnd = (ev) => {
      if (ev.target !== backdrop || done) return;
      done = true;
      backdrop.removeEventListener("transitionend", onEnd);
      finish();
    };
    backdrop.addEventListener("transitionend", onEnd);
    setTimeout(() => {
      if (!done) {
        done = true;
        backdrop.removeEventListener("transitionend", onEnd);
        finish();
      }
    }, 450);
  }
}

document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
  backdrop.addEventListener("click", (ev) => {
    if (ev.target === backdrop) closeModal(backdrop);
  });
  backdrop.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal(backdrop));
  });
});

document.addEventListener("keydown", (ev) => {
  if (openModals.length === 0) return;
  const top = openModals[openModals.length - 1];

  if (ev.key === "Escape") {
    ev.preventDefault();
    closeModal(top);
    return;
  }

  if (ev.key === "Tab") {
    const focusables = Array.from(top.querySelectorAll(FOCUSABLE)).filter(
      (el) => el.offsetParent !== null
    );
    if (focusables.length === 0) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];

    if (ev.shiftKey && document.activeElement === first) {
      ev.preventDefault();
      last.focus();
    } else if (!ev.shiftKey && document.activeElement === last) {
      ev.preventDefault();
      first.focus();
    }
  }
});

const modalTech = document.getElementById("modal-tech");
const modalLogin = document.getElementById("modal-login");
const modalContact = document.getElementById("modal-contact");

const ctaPrimary = document.getElementById("cta-primary");
const ctaSecondary = document.getElementById("cta-secondary");

ctaPrimary.addEventListener("click", () => openModal(modalLogin, ctaPrimary));
ctaSecondary.addEventListener("click", () => openModal(modalTech, ctaSecondary));

document.getElementById("login-yes").addEventListener("click", () => {
  window.location.href = LOGIN_REDIRECT_URL;
});

document.getElementById("login-no").addEventListener("click", () => {
  closeModal(modalLogin);
  openModal(modalContact, ctaPrimary);
});

document.getElementById("contact-form").setAttribute("action", CONTACT_FORM_ACTION);

const revealEls = document.querySelectorAll(".reveal");
const reduceMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

if (reduceMotionQuery.matches || !("IntersectionObserver" in window)) {
  revealEls.forEach((el) => el.classList.add("is-visible"));
} else {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
  );
  revealEls.forEach((el) => observer.observe(el));
}

document.getElementById("footer-year").textContent = new Date().getFullYear();
