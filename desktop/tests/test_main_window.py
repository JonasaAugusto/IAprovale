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

from app.ui.main_window import visible_tab_labels


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
