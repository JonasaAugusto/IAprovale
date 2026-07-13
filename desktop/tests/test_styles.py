"""Tests for `styles.window_background_qss` (bug fix, modo-noturno-bugado).

Pure, Qt-free function — no QApplication needed (same testing approach as
`test_main_window.py`'s `visible_tab_labels`). Regression coverage for the
top-level window background never following the theme toggle: qfluentwidgets'
`setTheme()` only re-styles registered Fluent components, so the app's real
top-level window (`_RootWindow` in `main.py`) must set this QSS explicitly on
startup and on every toggle.

The QSS is scoped with an ID selector (`#RootWindow { ... }`) rather than a
bare/unscoped declaration — regression coverage for the "boxes inside boxes"
follow-up bug, where an unscoped rule cascaded into descendant plain
QWidgets (`MainWindow`/`LoginPage`) and made `TitleLabel`/`BodyLabel` inside
`CardWidget` paint their own opaque background rectangles.
"""

from app.ui import styles


def test_window_background_qss_light():
    assert styles.window_background_qss(styles.THEME_LIGHT) == (
        f"#{styles.ROOT_WINDOW_OBJECT_NAME} {{ background-color: "
        f"{styles.COLOR_WINDOW_BG_LIGHT}; }}"
    )


def test_window_background_qss_dark():
    assert styles.window_background_qss(styles.THEME_DARK) == (
        f"#{styles.ROOT_WINDOW_OBJECT_NAME} {{ background-color: "
        f"{styles.COLOR_WINDOW_BG_DARK}; }}"
    )


def test_window_background_qss_unknown_falls_back_to_light():
    # Mirrors apply_theme's own fallback (anything not THEME_DARK -> light).
    assert styles.window_background_qss("bogus") == (
        f"#{styles.ROOT_WINDOW_OBJECT_NAME} {{ background-color: "
        f"{styles.COLOR_WINDOW_BG_LIGHT}; }}"
    )


def test_window_background_qss_is_scoped_to_root_window_id_selector():
    # Regression: a bare/unscoped `background-color: ...;` declaration
    # cascades into descendant plain QWidgets in Qt Style Sheets, causing
    # child labels inside CardWidget to paint their own opaque background
    # ("boxes inside boxes"). The rule must be scoped to the specific
    # `#RootWindow` object name so only `_RootWindow` itself matches.
    qss = styles.window_background_qss(styles.THEME_DARK)
    assert qss.startswith(f"#{styles.ROOT_WINDOW_OBJECT_NAME}")


def test_light_and_dark_colors_are_distinct():
    assert styles.COLOR_WINDOW_BG_LIGHT != styles.COLOR_WINDOW_BG_DARK
