"""Tests for main_frame's tab-visibility logic (D-05/D-06).

`visible_tab_labels` is a pure, Tk-free function (no root needed) — the
DESKTOP-01 test target per 03-RESEARCH.md's Validation Architecture
(admin-tab conditional test should not require a real Tk mainloop).

Full `build_main_frame` widget construction (Notebook tab count/order, Sair
button wiring) is intentionally NOT exercised with a second real `tk.Tk()`
root here: this environment (Windows/Tcl 8.6/Python 3.14) is documented in
`test_busca_tab.py` to intermittently raise a spurious
`_tkinter.TclError: Can't find a usable tk.tcl` when multiple `tk.Tk()`
instances are constructed across test modules within one process — creating
a second module-scoped root reproduced that failure reliably here. The
Admin-tab-gating and Sair-wiring acceptance criteria are instead verified
by static inspection (grep for `is_admin`/`Sair`/`on_logout`, absence of
`.hide(`) per the plan's acceptance criteria, and by the live e2e manual
checkpoint (Task 3).
"""

from dataclasses import dataclass

from app.ui.main_frame import visible_tab_labels


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
