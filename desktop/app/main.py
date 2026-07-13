"""Entry point: QApplication bootstrap, startup auto-login, frame swap,
logout (PySide6/qfluentwidgets rewrite of `main.py`, DESKTOP-01/D-01/D-06).

Wires every module built in Plans 01-06 into a runnable app:

- Creates the single `QApplication` + one root `QWidget` (D-06 — one
  window, content swapped internally via a `QStackedWidget`, never
  multiple top-level windows), sets title/size/minimum-size from `styles`'
  constants, loads the persisted theme preference, and calls
  `styles.apply_theme(theme)` exactly once at startup, before any page is
  built.
- A live light/dark toggle (`_toggle_theme`) switches the qfluentwidgets
  theme, persists the new preference, and refreshes the EXISTING
  post-login view in place (`MainWindow.refresh_theme()`) rather than
  rebuilding it from scratch — registered qfluentwidgets components
  already re-style themselves reactively, so only the few widgets with
  manually-built, construction-time QSS need an explicit nudge. This
  preserves in-memory search state (query text, rendered results) across
  a manual theme toggle (see debug session modo-noturno-bugado — the old
  full-rebuild approach used to discard that state; a "carried over from
  the Tkinter analog" tradeoff that no longer applies).
- Startup auto-login (D-01): a saved `auth_store.Session` is validated via
  the cheapest authenticated call, `GET /profile` (DB-only, no
  DeepSeek/MCP round trip) — an invalid/revoked token clears the session
  and falls back to the login screen. There is no client-side clock-expiry
  heuristic (the backend has none).
- `_after_login`: persists the just-logged-in session (D-01) and attaches
  the token to every subsequent `api_client` call before showing the Main
  page.
- `_logout` (T-05-LOGOUT): calls `POST /auth/logout` server-side FIRST to
  revoke the token, then clears the local session — in that order, and
  local clearing still happens even if the network call errors (both
  on_success AND on_error route to `_finish_logout`), so the token is
  never left server-valid-but-locally-gone.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QStackedWidget, QVBoxLayout, QWidget

from app import api_client, auth_store
from app.async_helpers import run_in_background
from app.ui import styles
from app.ui.login_page import LoginPage
from app.ui.main_window import MainWindow


class _RootWindow(QWidget):
    """Single top-level window. Content is swapped via a `QStackedWidget`
    (Login <-> Main) — replaces the Tkinter analog's destroy/rebuild of
    `root.winfo_children()`.
    """

    def __init__(self) -> None:
        super().__init__()
        # Required so `styles.window_background_qss`'s scoped `#RootWindow
        # {...}` ID selector matches this widget and only this widget (see
        # `styles.ROOT_WINDOW_OBJECT_NAME` — prevents the background rule
        # from cascading into descendant plain QWidgets, which caused the
        # "boxes inside boxes" regression around login-screen labels).
        self.setObjectName(styles.ROOT_WINDOW_OBJECT_NAME)
        self.setWindowTitle(styles.TITLE)
        self.resize(*styles.WINDOW_SIZE)
        self.setMinimumSize(*styles.MIN_SIZE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack)

        self._theme = styles.load_theme_pref()
        styles.apply_theme(self._theme)  # must run before any page is built
        # This widget is the real top-level window — qfluentwidgets'
        # setTheme() never re-styles plain QWidgets (only registered
        # Fluent components), so its background must be set explicitly
        # here and again on every toggle (see modo-noturno-bugado).
        self.setStyleSheet(styles.window_background_qss(self._theme))

        self._session: auth_store.Session | None = None
        self._main_window: MainWindow | None = None

        self._try_auto_login()

    # ------------------------------------------------------------------
    # Page swap
    # ------------------------------------------------------------------

    def _swap(self, widget: QWidget) -> None:
        old = self._stack.currentWidget()
        self._stack.addWidget(widget)
        self._stack.setCurrentWidget(widget)
        if old is not None:
            self._stack.removeWidget(old)
            old.deleteLater()

    def _show_login(self) -> None:
        self._main_window = None
        self._swap(LoginPage(on_success=self._after_login))

    def _show_main(self, session: auth_store.Session) -> None:
        self._session = session
        self._main_window = MainWindow(
            session,
            on_logout=self._logout,
            on_toggle_theme=self._toggle_theme,
        )
        self._swap(self._main_window)

    # ------------------------------------------------------------------
    # Theme toggle
    # ------------------------------------------------------------------

    def _toggle_theme(self) -> None:
        new_theme = (
            styles.THEME_LIGHT if self._theme == styles.THEME_DARK else styles.THEME_DARK
        )
        styles.apply_theme(new_theme)
        styles.save_theme_pref(new_theme)
        self.setStyleSheet(styles.window_background_qss(new_theme))
        self._theme = new_theme
        # Refresh the EXISTING post-login view in place instead of
        # rebuilding it — registered qfluentwidgets components (PushButton,
        # CardWidget, Pivot, SearchLineEdit, etc.) already re-style
        # themselves reactively via styles.apply_theme()/setTheme() above;
        # MainWindow.refresh_theme() only needs to explicitly re-style the
        # few widgets with manually-built, construction-time QSS (cargo
        # chips in ConcursoCard, destructive buttons in AdminTab). This
        # preserves in-memory search state (query text, rendered results)
        # across a manual theme toggle (see modo-noturno-bugado).
        if self._main_window is not None:
            self._main_window.refresh_theme()

    # ------------------------------------------------------------------
    # Login / logout
    # ------------------------------------------------------------------

    def _after_login(self, session: auth_store.Session) -> None:
        auth_store.save_session(session)  # persist token for next launch (D-01)
        api_client.set_token(session.token)
        self._show_main(session)

    def _logout(self) -> None:
        def _finish_logout(_result=None) -> None:
            api_client.set_token(None)
            auth_store.clear_session()
            self._session = None
            self._show_login()

        run_in_background(
            api_client.logout,  # server-side revocation FIRST (T-05-LOGOUT)
            on_success=_finish_logout,
            on_error=_finish_logout,  # clear locally even if the call errored
        )

    # ------------------------------------------------------------------
    # Startup auto-login (D-01)
    # ------------------------------------------------------------------

    def _try_auto_login(self) -> None:
        session = auth_store.load_session()
        if session is None:
            self._show_login()
            return

        def _on_startup_valid(_profile) -> None:
            self._show_main(session)  # token still valid — skip login entirely

        def _on_startup_invalid(_exc) -> None:
            auth_store.clear_session()
            self._show_login()

        api_client.set_token(session.token)
        run_in_background(
            api_client.get_profile,
            on_success=_on_startup_valid,
            on_error=_on_startup_invalid,
        )


def main() -> None:
    app = QApplication(sys.argv)
    window = _RootWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
