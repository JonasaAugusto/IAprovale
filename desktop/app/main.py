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
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStackedWidget, QVBoxLayout, QWidget

from app import api_client, auth_store
from app.async_helpers import run_in_background
from app.ui import styles
from app.ui.login_page import LoginPage
from app.ui.main_window import MainWindow

# Titlebar/taskbar icon while the app is running — separate from both the
# PDF/login logo (drawn at runtime from assets/logo.png) and the frozen
# .exe's own file icon (baked in by PyInstaller at build time via
# ConcursoFinder.spec's `icon=` — that one requires a rebuild to change).
# Existence-checked so absence never raises (asset may not exist yet).
#
# PyInstaller quirk (confirmed via debug session icone-exe-nao-aparece):
# unlike a normally-imported submodule, THIS file is the frozen bundle's
# entry-point script, so its own __file__ inside the .exe resolves to
# "<bundle_root>/main.py" (no "app/" prefix) instead of mirroring the
# source tree like every other module does — Path(__file__).parent alone
# would silently point one directory too shallow and never find the icon.
# app/assets/ is bundled at "<bundle_root>/app/assets/" (ConcursoFinder.spec),
# so the frozen base must be sys._MEIPASS/app explicitly.
if getattr(sys, "frozen", False):
    _APP_DIR = Path(sys._MEIPASS) / "app"
else:
    _APP_DIR = Path(__file__).parent

_ICON_PATH = _APP_DIR / "assets" / "icon.ico"


class _ConnectingPage(QWidget):
    """Transient centered "Conectando ao servidor..." state shown while the
    startup auto-login validates the saved token (T-05) — avoids a blank
    window during Render's cold-start wait. Uses lazy imports of qfluentwidgets
    widgets to keep them out of module import time.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from qfluentwidgets import BodyLabel, IndeterminateProgressBar

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(styles.SPACING_MD)

        label = BodyLabel("Conectando ao servidor...", self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar = IndeterminateProgressBar(self)
        bar.setFixedWidth(220)

        layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(bar, alignment=Qt.AlignmentFlag.AlignCenter)


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

        # Reconnect timer for startup auto-login: on a network/cold-start
        # failure the app stays on the "Conectando..." screen and retries,
        # only leaving it once actually connected (or on a real 401). Child of
        # this widget, so it is destroyed with the window (never fires late).
        self._pending_session: auth_store.Session | None = None
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.setInterval(3000)
        self._reconnect_timer.timeout.connect(self._attempt_auto_login)

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
        self._pending_session = auth_store.load_session()
        if self._pending_session is None:
            self._show_login()
            return

        # Show a "connecting" state instead of a blank window while GET /profile
        # validates the saved token — this can take 30-60s on a Render free-tier
        # cold start (T-05), during which the window would otherwise be empty.
        # The app STAYS on this screen until it actually connects (see
        # _on_startup_invalid) — it never shows login/main while disconnected.
        self._swap(_ConnectingPage())
        api_client.set_token(self._pending_session.token)
        self._attempt_auto_login()

    def _attempt_auto_login(self) -> None:
        run_in_background(
            api_client.get_profile,
            on_success=self._on_startup_valid,
            on_error=self._on_startup_invalid,
        )

    def _on_startup_valid(self, _profile) -> None:
        self._show_main(self._pending_session)  # token valid — skip login

    def _on_startup_invalid(self, exc) -> None:
        # A real 401 (SessionExpiredError) means the saved token is dead: clear
        # it and fall back to login. A network/timeout/cold-start failure must
        # NOT leave the "Conectando..." screen — keep retrying until the server
        # answers, so the app only leaves this screen once truly connected.
        if isinstance(exc, api_client.SessionExpiredError):
            auth_store.clear_session()
            self._show_login()
            return
        self._reconnect_timer.start()


def main() -> None:
    if sys.platform == "win32":
        # Without an explicit AppUserModelID, Windows can represent the
        # taskbar button using the *host* python.exe's own icon when run
        # unfrozen (dev mode) instead of the window icon set below — a
        # well-known Windows taskbar quirk for interpreted GUI apps.
        import ctypes

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "IAprovale.ConcursoFinder.Desktop.1"
            )
        except (AttributeError, OSError):
            pass

    app = QApplication(sys.argv)
    if _ICON_PATH.exists():
        icon = QIcon(str(_ICON_PATH))
        app.setWindowIcon(icon)
    window = _RootWindow()
    if _ICON_PATH.exists():
        # Belt-and-suspenders: set it on the window itself too, not just the
        # QApplication default. On some Windows/Qt combinations the native
        # titlebar/taskbar HICON is only reliably picked up when the icon is
        # set on the concrete top-level widget, not only propagated from
        # QApplication.setWindowIcon() before that widget existed.
        window.setWindowIcon(icon)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
