"""Pre-login screen (PySide6/qfluentwidgets rewrite of `login_frame.py`).

`LoginPage` collects username/password, submits `api_client.login()` off
the GUI thread via `async_helpers.run_in_background` (HARD RULE — a direct
call inside a clicked-signal handler would freeze the UI for the full
round-trip, up to Render's ~30-90s cold-start latency), and reports a
constructed `auth_store.Session` upward through `on_success` on a
successful login.

D-05 (NEW behavior — not present in the Tkinter analog): the instant login
is submitted, the "Entrar" button disables AND its text changes to
"Conectando à API...", visible feedback during Render's cold-start wait
(the old version only disabled the button with no explanatory text).
Reverts to "Entrar"/enabled on success or error.

Error handling follows 05-UI-SPEC.md's Error Display Contract: failures
are shown in an inline `InfoBar.error` directly above the "Entrar" button
area (never a modal dialog), displaying the backend's `exc.detail` string
verbatim — never a generic/rephrased message.

This page does NOT persist the session itself — `auth_store.save_session`
remains the entry point's (`main.py`) responsibility.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PasswordLineEdit,
    PrimaryPushButton,
    TitleLabel,
)

from app import api_client, auth_store
from app.async_helpers import run_in_background
from app.ui import styles

_ENTRAR_TEXT = "Entrar"
_CONNECTING_TEXT = "Conectando à API..."  # D-05


class LoginPage(QWidget):
    """Centered login card. `on_success(session)` fires after a successful login."""

    def __init__(self, on_success, parent=None) -> None:
        super().__init__(parent)
        self._on_success = on_success
        self._error_bar: InfoBar | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = CardWidget(self)
        card.setMaximumWidth(420)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(
            styles.SPACING_XL,
            styles.SPACING_XL,
            styles.SPACING_XL,
            styles.SPACING_XL,
        )

        card_layout.addWidget(TitleLabel("Concurso Finder", card))
        card_layout.addSpacing(styles.SPACING_LG)

        card_layout.addWidget(BodyLabel("Usuário", card))
        self._username_entry = LineEdit(card)
        self._username_entry.setClearButtonEnabled(True)
        card_layout.addWidget(self._username_entry)
        card_layout.addSpacing(styles.SPACING_MD)

        card_layout.addWidget(BodyLabel("Senha", card))
        self._password_entry = PasswordLineEdit(card)
        self._password_entry.returnPressed.connect(self._on_submit)
        card_layout.addWidget(self._password_entry)

        card_layout.addSpacing(styles.SPACING_SM)

        self._entrar_button = PrimaryPushButton(_ENTRAR_TEXT, card)
        self._entrar_button.clicked.connect(self._on_submit)
        card_layout.addWidget(self._entrar_button)

        outer.addWidget(card)

    def _on_submit(self) -> None:
        username = self._username_entry.text()
        password = self._password_entry.text()

        self._clear_error()
        self._entrar_button.setEnabled(False)
        self._entrar_button.setText(_CONNECTING_TEXT)

        run_in_background(
            lambda: api_client.login(username, password),
            self._on_login_success,
            self._on_login_error,
        )

    def _on_login_success(self, response: dict) -> None:
        self._entrar_button.setEnabled(True)
        self._entrar_button.setText(_ENTRAR_TEXT)
        session = auth_store.Session(
            token=response["token"],
            user_id=response["user_id"],
            username=response["username"],
            is_admin=response["is_admin"],
        )
        self._on_success(session)

    def _on_login_error(self, exc: Exception) -> None:
        self._entrar_button.setEnabled(True)
        self._entrar_button.setText(_ENTRAR_TEXT)
        detail = getattr(exc, "detail", str(exc))
        self._show_error(detail)

    def _show_error(self, detail: str) -> None:
        self._clear_error()
        self._error_bar = InfoBar.error(
            title="",
            content=detail,
            duration=-1,
            position=InfoBarPosition.TOP,
            parent=self,
        )

    def _clear_error(self) -> None:
        if self._error_bar is not None:
            self._error_bar.close()
            self._error_bar = None
