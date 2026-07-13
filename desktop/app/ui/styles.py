"""Fluent design tokens (visual contract) for the desktop client.

Every later screen (`login_page.py`, `busca_tab.py`, `concurso_card.py`,
`admin_tab.py`, `main_window.py`) references these tokens — this module is
the single configure-once site for the app's design tokens.

Styling is built on `qfluentwidgets.setTheme`/`setThemeColor` (PySide6 +
PyQt-Fluent-Widgets, per 05-UI-SPEC.md's Design System table). This
replaces the earlier Bootstrap-styled-ttk-based approach entirely — see
05-CONTEXT.md D-01 and 05-PATTERNS.md for the full rewrite rationale.

MANDATORY: `apply_theme(theme_name)` must be called once at startup,
before any widget referencing these tokens is constructed, and again on
every live theme toggle.
"""

from __future__ import annotations

import json

from qfluentwidgets import Theme, setTheme, setThemeColor

from app.config import APP_DIR, THEME_FILE

# --- Window geometry (05-UI-SPEC.md Window & Layout) ---
WINDOW_SIZE = (900, 650)
MIN_SIZE = (700, 500)
TITLE = "Concurso Finder"

# --- Theme names (new persisted values) ---
THEME_LIGHT = "light"
THEME_DARK = "dark"

# --- Legacy persisted values (previous Bootstrap-styled-ttk client) mapped for read compat ---
_LEGACY_THEME_MAP = {
    "flatly": THEME_LIGHT,
    "darkly": THEME_DARK,
}

# --- Accent (05-UI-SPEC.md Color — Windows 11 system accent blue) ---
# Never leave qfluentwidgets' out-of-box teal default (#009faa) in place.
ACCENT = "#0078D4"

# --- Semantic/brand hues (05-UI-SPEC.md Color) — identical in both themes ---
COLOR_BADGE_BG = "#ffc107"  # NOVO badge background
COLOR_BADGE_FG = "#3a2e00"  # NOVO badge text
COLOR_DESTRUCTIVE_LIGHT = "#C42B1C"  # Desativar/Excluir, light theme
COLOR_DESTRUCTIVE_DARK = "#FF99A4"  # Desativar/Excluir, dark theme

# --- Top-level window background (bug fix, modo-noturno-bugado) ---
# qfluentwidgets' setTheme()/updateStyleSheet() only re-styles genuine
# Fluent components registered via FluentStyleSheet.apply() — plain
# PySide6 QWidget containers (this app's `_RootWindow`/`MainWindow`/
# `LoginPage`, by design D-06, are NOT FluentWindow/FluentWidget
# subclasses) are never touched by it and keep the OS-default (light)
# background regardless of theme. Values mirror qfluentwidgets'
# `FluentWindow` canonical background colors (see
# `qfluentwidgets.window.fluent_window.FluentWidget`) so a plain
# top-level QWidget looks identical to a real FluentWindow once themed.
COLOR_WINDOW_BG_LIGHT = "#F0F4F9"
COLOR_WINDOW_BG_DARK = "#202020"

# objectName `_RootWindow` must set on itself so `window_background_qss`
# below can scope its rule with an ID selector (`#RootWindow { ... }`)
# instead of a bare/unscoped declaration. A bare `setStyleSheet(
# "background-color: ...;")` on a QWidget is a well-documented Qt Style
# Sheets gotcha (see Qt docs Q&A "Why does the style sheet inheritance
# not work as I expect?" / countless "child widgets get parent's
# background" reports): once ANY widget in the hierarchy carries a style
# sheet, Qt's QStyleSheetStyle engine starts treating the whole subtree
# as "styled", and an unscoped `background-color` rule cascades down to
# every plain-QWidget-derived descendant that doesn't have its own rule
# (this app's `MainWindow`/`LoginPage`/`QStackedWidget` are all plain
# `QWidget` subclasses) — each one then paints its own opaque background
# rect, producing "boxes inside boxes" around `TitleLabel`/`BodyLabel`
# inside `CardWidget` on the login screen (regression introduced by the
# first modo-noturno-bugado fix; see debug session "Evidence (continuacao
# pos verificacao humana)"). Scoping with an ID selector restricts the
# rule to exactly this one widget instance, eliminating the cascade
# while still painting the top-level window's own background.
ROOT_WINDOW_OBJECT_NAME = "RootWindow"

# --- Spacing scale (05-UI-SPEC.md Spacing Scale, px) ---
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 16
SPACING_LG = 24
SPACING_XL = 32


def apply_theme(name: str) -> None:
    """Apply the Fluent theme (`THEME_LIGHT`/`THEME_DARK`) and accent color.

    Single entry point for both initial startup styling and runtime
    light/dark toggling. Never leaves the qfluentwidgets default teal
    accent (#009faa) in place — always (re)applies ACCENT.
    """
    setTheme(Theme.DARK if name == THEME_DARK else Theme.LIGHT)
    setThemeColor(ACCENT)


def window_background_qss(name: str) -> str:
    """Return the scoped `background-color` QSS for the app's top-level window.

    Must be (re)applied to the real top-level widget (`_RootWindow` in
    `main.py`) on startup and on every theme toggle, since plain QWidget
    containers are outside qfluentwidgets' own theme-repaint mechanism
    (see `COLOR_WINDOW_BG_LIGHT`/`COLOR_WINDOW_BG_DARK` above). Nested
    plain QWidgets (`MainWindow`, `LoginPage`, and the "background:
    transparent;" containers already used in `busca_tab.py`) rely on this
    color showing through from the top-level window.

    The rule is scoped with an ID selector (`#RootWindow { ... }`)
    against `ROOT_WINDOW_OBJECT_NAME` — NOT a bare/unscoped declaration —
    so it applies to `_RootWindow` alone and does not cascade down to
    descendant plain QWidgets (`MainWindow`, `LoginPage`,
    `QStackedWidget`), which would otherwise start painting their own
    opaque background ("boxes inside boxes" regression; see
    `ROOT_WINDOW_OBJECT_NAME`'s docstring above). Callers must
    `setObjectName(ROOT_WINDOW_OBJECT_NAME)` on the target widget before
    applying this QSS for the selector to match.
    """
    color = COLOR_WINDOW_BG_DARK if name == THEME_DARK else COLOR_WINDOW_BG_LIGHT
    return f"#{ROOT_WINDOW_OBJECT_NAME} {{ background-color: {color}; }}"


def load_theme_pref() -> str:
    """Return the persisted theme name, or THEME_LIGHT if missing/corrupt.

    Mirrors auth_store.load_session's never-raise-on-corrupt behavior —
    startup must never crash because of a bad theme.json. Legacy values
    from the previous Bootstrap-styled-ttk client ("flatly"/"darkly") are
    mapped to their new equivalents for backward compatibility with
    existing installs; any other unrecognized value falls back to
    THEME_LIGHT.
    """
    if not THEME_FILE.exists():
        return THEME_LIGHT
    try:
        data = json.loads(THEME_FILE.read_text(encoding="utf-8"))
        theme = data["theme"]
        if theme in (THEME_LIGHT, THEME_DARK):
            return theme
        if theme in _LEGACY_THEME_MAP:
            return _LEGACY_THEME_MAP[theme]
        return THEME_LIGHT
    except (json.JSONDecodeError, OSError, KeyError, TypeError):
        return THEME_LIGHT


def save_theme_pref(name: str) -> None:
    """Atomically persist the chosen theme (tmp + replace), like auth_store.

    Always writes the new values ("light"/"dark"), never the legacy
    Bootstrap-styled-ttk names.
    """
    APP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = THEME_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"theme": name}), encoding="utf-8")
    tmp.replace(THEME_FILE)  # atomic on Windows (same volume)
