"""Post-login screen: `Pivot` + `QStackedWidget` with Busca always + Admin
conditionally (PySide6/qfluentwidgets rewrite of `main_frame.py`, D-02).

`visible_tab_labels(session)` is a pure, Qt-free helper isolating the
tab-visibility decision (["Busca"] + ["Admin"] iff `session.is_admin`) so it
can be unit-tested without a `QApplication`.

`MainWindow(session, on_logout, on_toggle_theme)` builds the container: a
header row (right-aligned) with a theme-toggle `TransparentToolButton` and
a "Sair" `PushButton` (wired to the injected `on_logout` callback, per
05-UI-SPEC.md's Copywriting Contract — no confirmation dialog), plus a
`Pivot` + `QStackedWidget` with `BuscaTab` added unconditionally and
`AdminTab` added only inside an `if session.is_admin` branch — never
toggled at runtime via `.hide()`/`.show()`, since `is_admin` is immutable
within a session (same rule as the Tkinter analog).

Admin-tab visibility here is UX only (T-05-ADMINGATE) — the backend's
`require_admin` dependency remains the actual authorization boundary.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import FluentIcon as FIF, Pivot, PushButton, TransparentToolButton

from app.ui import styles
from app.ui.admin_tab import AdminTab
from app.ui.busca_tab import BuscaTab

_BUSCA_ROUTE = "Busca"
_ADMIN_ROUTE = "Admin"


def visible_tab_labels(session) -> list[str]:
    """Return the tab labels that should be visible for `session`.

    Pure function, no QApplication required — isolates the tab-visibility
    decision for a Qt-free unit test.
    """
    labels = ["Busca"]
    if session.is_admin:
        labels.append("Admin")
    return labels


class MainWindow(QWidget):
    """Post-login container: header (theme toggle + Sair) + Pivot tabs."""

    def __init__(self, session, on_logout, on_toggle_theme, parent=None) -> None:
        super().__init__(parent)
        self._session = session

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(
            styles.SPACING_MD, styles.SPACING_SM, styles.SPACING_MD, styles.SPACING_SM
        )
        header.setSpacing(styles.SPACING_SM)
        header.addStretch(1)

        self._theme_button = TransparentToolButton(FIF.CONSTRACT, self)
        self._theme_button.setToolTip("Alternar tema claro/escuro")
        self._theme_button.clicked.connect(on_toggle_theme)
        header.addWidget(self._theme_button)

        self._sair_button = PushButton("Sair", self)
        self._sair_button.clicked.connect(on_logout)
        header.addWidget(self._sair_button)

        layout.addLayout(header)

        self._pivot = Pivot(self)
        self._stack = QStackedWidget(self)

        self._busca_tab = BuscaTab(session, self._stack)
        self._stack.addWidget(self._busca_tab)
        self._pivot.addItem(
            routeKey=_BUSCA_ROUTE,
            text=_BUSCA_ROUTE,
            onClick=lambda: self._stack.setCurrentWidget(self._busca_tab),
        )

        # Admin tab decided ONCE here, at build time — session.is_admin is
        # immutable for the lifetime of a session, never re-checked/toggled.
        self._admin_tab: AdminTab | None = None
        if session.is_admin:
            self._admin_tab = AdminTab(session, self._stack)
            self._stack.addWidget(self._admin_tab)
            self._pivot.addItem(
                routeKey=_ADMIN_ROUTE,
                text=_ADMIN_ROUTE,
                onClick=lambda: self._stack.setCurrentWidget(self._admin_tab),
            )

        layout.addWidget(self._pivot)
        layout.addWidget(self._stack, 1)

        self._pivot.setCurrentItem(_BUSCA_ROUTE)

    def refresh_theme(self) -> None:
        """Re-style child widgets that don't auto-update via qfluentwidgets'
        `setTheme()` after a live theme toggle (modo-noturno-bugado).

        Called by `main.py::_RootWindow._toggle_theme()` on the EXISTING
        `MainWindow` instance, instead of the old approach of discarding
        it and building a fresh one — that used to also discard in-memory
        search state (query text, rendered results) on every toggle.
        Registered qfluentwidgets components (`PushButton`, `CardWidget`,
        `Pivot`, `SearchLineEdit`, etc.) already re-style themselves
        reactively via the library's own theme-change mechanism and need
        no help here; only the few widgets with manually-built,
        construction-time QSS do.
        """
        self._busca_tab.refresh_theme()
        if self._admin_tab is not None:
            self._admin_tab.refresh_theme()
