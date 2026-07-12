"""Shared ttk style tokens (visual contract) for the desktop client.

Every later screen (`login_frame.py`, `busca_tab.py`, `concurso_card.py`,
`admin_tab.py`) references these styles by name — this module is the single
configure-once site for the app's design tokens.

Styling is built on `ttkbootstrap.Style` with two real themes: `flatly`
(light) and `darkly` (dark) — see THEME_LIGHT / THEME_DARK below. This
replaces the earlier `ttk.Style().theme_use("clam")` approach (Windows'
native `vista`/`winnative` ttk theme silently ignores custom `background=`
styling — 03-RESEARCH.md Pattern 3 / Pitfall 5 — but ttkbootstrap's themes
honor custom background styling natively, so a forced `clam` fallback is no
longer needed). See 03-UI-SPEC.md's "Amendment 2026-07-10" for the full
design-contract change.

MANDATORY: `apply_theme(root, theme_name)` must be called once at startup,
before any widget referencing these style names is constructed, and again
on every live theme toggle (it re-derives the surface COLOR_* globals and
re-registers every brand/surface style token for the newly active theme).
"""

from __future__ import annotations

import json
import tkinter.font as tkfont

import ttkbootstrap as tb

from app.config import APP_DIR, THEME_FILE

# --- Window geometry (03-UI-SPEC.md Window & Layout) ---
WINDOW_SIZE = "900x650"
MIN_SIZE = (700, 500)
TITLE = "Concurso Finder"

# --- Fonts (03-UI-SPEC.md Typography) ---
# Tuples usable directly as a `font=` kwarg; also exposed as real
# tkinter.font.Font objects below once a Tk root exists (get_fonts() call),
# if a caller prefers Font objects over raw tuples.
FONT_DISPLAY = ("Segoe UI", 16, "bold")
FONT_HEADING = ("Segoe UI", 11, "bold")
FONT_BODY = ("Segoe UI", 10, "normal")
FONT_SMALL = ("Segoe UI", 8, "bold")

# --- Theme names (ttkbootstrap built-in themes) ---
THEME_LIGHT = "flatly"
THEME_DARK = "darkly"

# --- Fixed brand hues (03-UI-SPEC.md Color) — identical in both themes ---
COLOR_BADGE_BG = "#ffc107"  # Badge.TLabel background ("NOVO")
COLOR_BADGE_FG = "#3a2e00"  # Badge.TLabel text-on-badge
COLOR_ACCENT = "#0d6efd"  # Accent.TButton / Accent.Horizontal.TProgressbar
COLOR_DESTRUCTIVE = "#dc3545"  # Destructive.TButton / Banner.TLabel

# --- Theme-aware surface colors ---
# Mutated by apply_theme() to match the active theme's palette. Widget
# files read these as module attributes (styles.COLOR_DOMINANT, etc.) at
# CONSTRUCTION time, so updating these globals before a frame rebuild is
# sufficient to repaint every freshly-built widget in the new theme — no
# widget file needs editing. Seeded here with light-theme (flatly) values
# so anything reading them before apply_theme() still works.
COLOR_DOMINANT = "#f5f5f5"  # Root.TFrame background / tab pane surface
COLOR_SECONDARY = "#ffffff"  # Card.TFrame background / content surface
COLOR_NEW_BG = "#fff8e1"  # CardNew.TFrame background (is_new highlight, light)
COLOR_TEXT = "#212529"  # standard theme foreground/text color (flatly fg default)

_NEW_BG_LIGHT = "#fff8e1"
_NEW_BG_DARK = "#4d3d00"

_style: tb.Style | None = None


def _derive_surface_colors(
    style: tb.Style, theme_name: str
) -> tuple[str, str, str, str]:
    """Return (dominant, secondary, new_bg, text) derived from the active theme's palette."""
    colors = style.colors
    if theme_name == THEME_DARK:
        dominant = colors.bg  # darkest surface — root/tab background
        secondary = colors.inputbg  # slightly lighter — card/content surface
        new_bg = _NEW_BG_DARK
    else:
        dominant = colors.light  # muted neutral — root/tab background
        secondary = colors.bg  # white — card/content surface
        new_bg = _NEW_BG_LIGHT
    text = colors.fg  # standard theme foreground/text color, both themes
    return dominant, secondary, new_bg, text


def configure_styles(style: tb.Style) -> tb.Style:
    """(Re)register every brand/surface style token on `style`.

    Safe to call repeatedly — `theme_use()` resets ttk's custom style
    registrations, so this must be re-run after every theme switch.
    """
    style.configure("Root.TFrame", background=COLOR_DOMINANT)

    style.configure(
        "Card.TFrame",
        background=COLOR_SECONDARY,
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "CardNew.TFrame",
        background=COLOR_NEW_BG,
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "Badge.TLabel",
        background=COLOR_BADGE_BG,
        foreground=COLOR_BADGE_FG,
        font=FONT_SMALL,
    )
    style.configure(
        "Accent.TButton",
        background=COLOR_ACCENT,
        foreground="white",
    )
    style.map(
        "Accent.TButton",
        background=[("active", COLOR_ACCENT), ("disabled", COLOR_ACCENT)],
        foreground=[("disabled", "white")],
    )
    style.configure(
        "Destructive.TButton",
        background=COLOR_DESTRUCTIVE,
        foreground="white",
    )
    style.map(
        "Destructive.TButton",
        background=[("active", COLOR_DESTRUCTIVE), ("disabled", COLOR_DESTRUCTIVE)],
        foreground=[("disabled", "white")],
    )
    style.configure("Banner.TLabel", foreground=COLOR_DESTRUCTIVE)
    style.configure(
        "Accent.Horizontal.TProgressbar",
        troughcolor=COLOR_DOMINANT,
        background=COLOR_ACCENT,
    )

    return style


def apply_theme(root, theme_name: str) -> tb.Style:
    """Switch the app to `theme_name` ("flatly" or "darkly"), live.

    Single entry point for both initial startup styling and runtime
    light/dark toggling. Get-or-creates the ttkbootstrap Style bound to
    `root`, switches its base theme, re-derives the surface COLOR_*
    globals from the new palette, then re-registers every brand/surface
    style token. Returns the Style instance.
    """
    global _style, COLOR_DOMINANT, COLOR_SECONDARY, COLOR_NEW_BG, COLOR_TEXT

    if _style is None:
        _style = tb.Style(theme=theme_name)
    else:
        _style.theme_use(theme_name)

    COLOR_DOMINANT, COLOR_SECONDARY, COLOR_NEW_BG, COLOR_TEXT = _derive_surface_colors(
        _style, theme_name
    )
    configure_styles(_style)

    return _style


def load_theme_pref() -> str:
    """Return the persisted theme name, or THEME_LIGHT if missing/corrupt.

    Mirrors auth_store.load_session's never-raise-on-corrupt behavior —
    startup must never crash because of a bad theme.json.
    """
    if not THEME_FILE.exists():
        return THEME_LIGHT
    try:
        data = json.loads(THEME_FILE.read_text(encoding="utf-8"))
        theme = data["theme"]
        if theme not in (THEME_LIGHT, THEME_DARK):
            return THEME_LIGHT
        return theme
    except (json.JSONDecodeError, OSError, KeyError, TypeError):
        return THEME_LIGHT


def save_theme_pref(name: str) -> None:
    """Atomically persist the chosen theme (tmp + replace), like auth_store."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = THEME_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"theme": name}), encoding="utf-8")
    tmp.replace(THEME_FILE)  # atomic on Windows (same volume)


def get_fonts() -> dict[str, tkfont.Font]:
    """Return real `tkinter.font.Font` objects for the four typography roles.

    Requires an existing Tk root (call after `apply_theme`). Optional
    convenience for callers that want `Font` objects (e.g. for `measure()`)
    instead of raw tuples — most callers can just use the module-level
    FONT_* tuples directly as a widget's `font=` kwarg.
    """
    return {
        "display": tkfont.Font(family="Segoe UI", size=16, weight="bold"),
        "heading": tkfont.Font(family="Segoe UI", size=11, weight="bold"),
        "body": tkfont.Font(family="Segoe UI", size=10, weight="normal"),
        "small": tkfont.Font(family="Segoe UI", size=8, weight="bold"),
    }
