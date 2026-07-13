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
