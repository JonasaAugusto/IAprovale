"""Tests for main_window's tab-visibility logic (D-02).

`visible_tab_labels` is a pure, Qt-free function (no QApplication needed) —
the DESKTOP-01 test target per 05-PATTERNS.md's Test Patterns (admin-tab
conditional test should not require a real Qt widget construction).

Full `MainWindow` widget construction (Pivot tab count/order, Sair button
wiring) is intentionally NOT exercised here with real `BuscaTab`/`AdminTab`
instances — those are already covered by their own test files (05-04/05-05).
The Admin-tab-gating and Sair-wiring acceptance criteria are instead
verified by static inspection (grep for `session.is_admin`/`Sair`, absence
of `.hide(`) per the plan's acceptance criteria — same approach as the
Tkinter analog's `test_main_frame.py`.
"""

from dataclasses import dataclass

import pytest

from app.ui.main_window import MainWindow, visible_tab_labels


@dataclass(frozen=True)
class _FakeSession:
    token: str = "tok"
    user_id: str = "u1"
    username: str = "jonas"
    is_admin: bool = False


def test_admin_tab_conditional():
    assert visible_tab_labels(_FakeSession(username="jonas", is_admin=True)) == [
        "Busca",
        "Admin",
    ]
    assert visible_tab_labels(_FakeSession(username="ana", is_admin=False)) == ["Busca"]


# ---------------------------------------------------------------------------
# refresh_theme() delegation (modo-noturno-bugado) — MainWindow.refresh_theme
# must re-style its child tabs in place rather than being rebuilt itself, so
# main.py::_RootWindow._toggle_theme can keep the same MainWindow instance.
# ---------------------------------------------------------------------------


def test_refresh_theme_delegates_to_busca_and_admin_tabs(qtbot, monkeypatch):
    from app.ui import admin_tab as admin_tab_module

    monkeypatch.setattr(admin_tab_module, "run_in_background", lambda *a, **k: None)

    window = MainWindow(
        _FakeSession(is_admin=True), on_logout=lambda: None, on_toggle_theme=lambda: None
    )
    qtbot.addWidget(window)

    calls = []
    monkeypatch.setattr(window._busca_tab, "refresh_theme", lambda: calls.append("busca"))
    monkeypatch.setattr(window._admin_tab, "refresh_theme", lambda: calls.append("admin"))

    window.refresh_theme()

    assert calls == ["busca", "admin"]


def test_refresh_theme_skips_admin_tab_when_absent(qtbot):
    window = MainWindow(
        _FakeSession(is_admin=False), on_logout=lambda: None, on_toggle_theme=lambda: None
    )
    qtbot.addWidget(window)
    assert window._admin_tab is None

    window.refresh_theme()  # must not raise with no admin tab present
