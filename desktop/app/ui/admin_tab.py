"""Admin tab: user list + full CRUD (D-02, DESKTOP-01).

`AdminTab` is the admin-only screen: it lists every user (username +
admin/inativo tags) and performs all six admin operations against the
existing backend endpoints (`GET/POST /auth/users`, `PATCH .../deactivate`,
`PATCH .../reactivate`, `POST .../reset-password`, `PATCH .../username`,
`DELETE /auth/users/{id}`) via `api_client`.

All backend authorization is enforced server-side by `require_admin`
(Phase 1) — this tab's own visibility (gated by `session.is_admin` in
`main_window.py`) is UX convenience only (T-05-ADMINUX). A stray `403` here
is handled the same way as any other error: surfaced verbatim in the inline
`InfoBar.error`, never a crash.

Per 05-UI-SPEC.md's Error Display Contract, only these things ever use a
modal (`MessageBox`/`MessageBoxBase`): the four destructive/state-changing
confirmations (deactivate/reactivate/delete/reset password), the one-time
generated-password reveal, and the rename input dialog. Every other
status/error uses the inline `InfoBar` at the top of the tab.
"""

from __future__ import annotations

import unicodedata

from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    CaptionLabel,
    CheckBox,
    FluentStyleSheet,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    MessageBox,
    MessageBoxBase,
    PrimaryPushButton,
    PushButton,
    SearchLineEdit,
    StrongBodyLabel,
    isDarkTheme,
)

from app import api_client
from app.async_helpers import run_in_background
from app.ui import styles

_BLANK_USERNAME_MSG = "Informe um nome de usuário."


def _normalizar(texto: str) -> str:
    """Normaliza pra comparação de filtro: sem acentos, caixa ignorada
    ("MÁRCOS" -> "marcos"). Espelho da ideia do normalizar() do backend."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").casefold()


def _style_destructive(button) -> None:
    """Recolor a button's text as destructive (Desativar/Excluir), keeping
    the rest of its Fluent chrome (pill shape, hover state) intact — the
    extra rule is appended after the library's own stylesheet so it wins
    the cascade for `color`/`font-weight` only.

    Idempotent/re-callable: on EVERY call, the base chrome is regenerated
    fresh via `FluentStyleSheet.BUTTON.apply(button)` (the exact same call
    `PushButton.__init__` makes) — which resolves to the CURRENT
    `qfluentwidgets` theme (`Theme.AUTO` -> `qconfig.theme`) — instead of
    reusing a stylesheet snapshot cached from an earlier call.

    This matters because `qfluentwidgets.setTheme()` (called by
    `styles.apply_theme()` on every live theme toggle) ALSO resets every
    registered `PushButton`'s `styleSheet()` to a fresh, correct,
    current-theme chrome as a side effect of `updateStyleSheet()` — a
    stylesheet cached from a PREVIOUS call (e.g. the button's construction
    theme) would silently go stale: repeated calls after a real theme
    change used to keep re-appending the new destructive COLOR onto the
    OLD theme's frozen background/border/hover chrome, so Desativar/
    Excluir's chrome (unlike Editar nome/Gerar nova senha, never touched
    by `_style_destructive`) never actually updated past its first
    construction theme (modo-noturno-bugado). Regenerating fresh each call
    is still idempotent across repeated calls WITHOUT an intervening theme
    change — `FluentStyleSheet.BUTTON.apply()` is deterministic for a
    given theme, so the resulting stylesheet string is identical run to
    run (see `test_style_destructive_is_idempotent_across_repeated_calls`).
    """
    FluentStyleSheet.BUTTON.apply(button)
    color = styles.COLOR_DESTRUCTIVE_DARK if isDarkTheme() else styles.COLOR_DESTRUCTIVE_LIGHT
    button.setStyleSheet(
        button.styleSheet() + f"\nQPushButton {{ color: {color}; font-weight: 600; }}"
    )


class _PasswordRevealDialog(MessageBoxBase):
    """One-time generated-password reveal (new user + reset password).

    Read-only field + `Copiar senha` (copies to clipboard and relabels
    itself `Copiado!`, staying open) + `Fechar` (closes). Auto-centered/
    masked by `MessageBoxBase` — no manual geometry math (unlike the
    Tkinter analog's requested-size-based centering).
    """

    def __init__(self, username: str, password: str, parent=None) -> None:
        super().__init__(parent)
        self.viewLayout.addWidget(StrongBodyLabel("Nova senha gerada", self))
        self.viewLayout.addWidget(BodyLabel(f"Senha para {username}:", self))
        self.viewLayout.addWidget(
            BodyLabel("Anote ou copie agora — ela não será mostrada novamente.", self)
        )

        self._password_edit = LineEdit(self)
        self._password_edit.setText(password)
        self._password_edit.setReadOnly(True)
        self.viewLayout.addWidget(self._password_edit)

        self.yesButton.setText("Copiar senha")
        self.cancelButton.setText("Fechar")
        self.yesButton.clicked.disconnect()
        self.yesButton.clicked.connect(lambda: self._copy(password))

    def _copy(self, password: str) -> None:
        QApplication.clipboard().setText(password)
        self.yesButton.setText("Copiado!")


class _RenameDialog(MessageBoxBase):
    """Editable rename dialog (`Editar nome`), pre-filled with the current
    username. Blank input is rejected client-side (`validate()` keeps the
    dialog open and reports via `on_blank`) using the same copy as the
    add-user row.
    """

    def __init__(self, username: str, on_blank, parent=None) -> None:
        super().__init__(parent)
        self._on_blank = on_blank
        self.viewLayout.addWidget(StrongBodyLabel("Editar nome de usuário", self))
        self.viewLayout.addWidget(
            BodyLabel(f"Novo nome de usuário para {username}:", self)
        )

        self._name_edit = LineEdit(self)
        self._name_edit.setText(username)
        self.viewLayout.addWidget(self._name_edit)

        self.yesButton.setText("Salvar")
        self.cancelButton.setText("Cancelar")

    def validate(self) -> bool:
        if not self._name_edit.text().strip():
            self._on_blank()
            return False
        return True

    def new_username(self) -> str:
        return self._name_edit.text().strip()


class AdminTab(QWidget):
    def __init__(self, session, parent=None) -> None:
        super().__init__(parent)
        self._session = session
        self._users: list[dict] = []
        self._error_bar: InfoBar | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            styles.SPACING_LG, styles.SPACING_LG, styles.SPACING_LG, styles.SPACING_LG
        )
        layout.setSpacing(styles.SPACING_MD)

        add_row = QWidget(self)
        add_row_layout = QHBoxLayout(add_row)
        add_row_layout.setContentsMargins(0, 0, 0, 0)
        add_row_layout.setSpacing(styles.SPACING_SM)

        self._username_entry = LineEdit(add_row)
        self._username_entry.setClearButtonEnabled(True)
        add_row_layout.addWidget(self._username_entry, 1)

        self._is_admin_check = CheckBox("admin", add_row)
        add_row_layout.addWidget(self._is_admin_check)

        self._add_button = PrimaryPushButton("Adicionar usuário", add_row)
        self._add_button.clicked.connect(self._on_add_click)
        add_row_layout.addWidget(self._add_button)

        layout.addWidget(add_row)

        # Campo de busca (v1.5.1) — filtro client-side sobre a lista já
        # carregada; o SearchLineEdit tem botão de limpar embutido (limpar
        # dispara textChanged com "" -> lista completa volta).
        self._search_entry = SearchLineEdit(self)
        self._search_entry.setPlaceholderText("Procurar usuário...")
        self._search_entry.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self._search_entry)

        self._list_container = QWidget(self)
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(styles.SPACING_SM)
        self._list_layout.addStretch(1)

        layout.addWidget(self._list_container, 1)

        self._load_users()

    # --- data loading -----------------------------------------------

    def _load_users(self) -> None:
        run_in_background(lambda: api_client.list_users(), self._render_users, self._on_error)

    def _render_users(self, users: list[dict]) -> None:
        self._users = users
        self._rerender()

    def _rerender(self) -> None:
        # Sempre lê o texto ATUAL do campo de busca — assim o filtro digitado
        # continua aplicado após qualquer ação que recarrega a lista
        # (_load_users -> _render_users -> _rerender).
        termo = _normalizar(self._search_entry.text())

        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for user in self._users:
            if not termo or termo in _normalizar(user["username"]):
                self._list_layout.addWidget(self._build_user_row(user))
        self._list_layout.addStretch(1)

    def _on_filter_changed(self, _text: str | None = None) -> None:
        self._rerender()

    def _build_user_row(self, user: dict) -> CardWidget:
        row = CardWidget(self._list_container)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(
            styles.SPACING_MD, styles.SPACING_SM, styles.SPACING_MD, styles.SPACING_SM
        )
        row_layout.setSpacing(styles.SPACING_SM)

        row_layout.addWidget(BodyLabel(user["username"], row))

        if user.get("is_admin"):
            row_layout.addWidget(CaptionLabel("[admin]", row))
        if not user.get("is_active", True):
            row_layout.addWidget(CaptionLabel("[inativo]", row))

        row_layout.addStretch(1)

        # Button order (right-aligned, per 05-UI-SPEC.md Admin tab
        # contract): Editar nome, Gerar nova senha, Desativar|Reativar,
        # Excluir (hidden on the acting admin's own row).
        rename_button = PushButton("Editar nome", row)
        rename_button.clicked.connect(lambda _checked=False, u=user: self._on_rename_click(u))
        row_layout.addWidget(rename_button)

        reset_button = PushButton("Gerar nova senha", row)
        reset_button.clicked.connect(lambda _checked=False, u=user: self._on_reset_click(u))
        row_layout.addWidget(reset_button)

        if user.get("is_active", True):
            toggle_button = PushButton("Desativar", row)
            _style_destructive(toggle_button)
            toggle_button.clicked.connect(
                lambda _checked=False, u=user: self._on_deactivate_click(u)
            )
        else:
            toggle_button = PushButton("Reativar", row)
            toggle_button.clicked.connect(
                lambda _checked=False, u=user: self._on_reactivate_click(u)
            )
        row_layout.addWidget(toggle_button)

        # Permanent delete — hidden on the acting admin's own row (no
        # self-delete from the UI; the backend also refuses it).
        if user["user_id"] != self._session.user_id:
            delete_button = PushButton("Excluir", row)
            _style_destructive(delete_button)
            delete_button.clicked.connect(lambda _checked=False, u=user: self._on_delete_click(u))
            row_layout.addWidget(delete_button)

        return row

    # --- add user -----------------------------------------------------

    def _on_add_click(self) -> None:
        username = self._username_entry.text().strip()
        is_admin = self._is_admin_check.isChecked()

        if not username:
            self._show_error(_BLANK_USERNAME_MSG)
            return

        self._clear_error()
        self._add_button.setEnabled(False)

        run_in_background(
            lambda: api_client.create_user(username, is_admin),
            self._on_user_created,
            self._on_error,
        )

    def _on_user_created(self, resp: dict) -> None:
        self._add_button.setEnabled(True)
        self._username_entry.clear()
        self._is_admin_check.setChecked(False)
        self._reveal_password(resp["username"], resp["generated_password"])
        self._load_users()

    # --- deactivate -----------------------------------------------------

    def _on_deactivate_click(self, user: dict) -> None:
        if not self._confirm(
            "Desativar usuário",
            f"Tem certeza que deseja desativar {user['username']}? "
            "O acesso será revogado imediatamente e a sessão ativa dele será encerrada.",
            "Desativar",
            destructive=True,
        ):
            return

        self._clear_error()
        run_in_background(
            lambda: api_client.deactivate_user(user["user_id"]),
            self._on_mutation_ok,
            self._on_error,
        )

    def _on_mutation_ok(self, _resp: dict) -> None:
        self._load_users()

    # --- delete (permanent) -----------------------------------------------------

    def _on_delete_click(self, user: dict) -> None:
        if not self._confirm(
            "Excluir usuário",
            "Esta ação é PERMANENTE e não pode ser desfeita. Excluir o usuário "
            f"'{user['username']}' e todo o seu histórico de buscas?",
            "Excluir",
            destructive=True,
        ):
            return

        self._clear_error()
        run_in_background(
            lambda: api_client.delete_user(user["user_id"]),
            self._on_mutation_ok,
            self._on_error,
        )

    # --- reactivate -----------------------------------------------------

    def _on_reactivate_click(self, user: dict) -> None:
        if not self._confirm(
            "Reativar usuário",
            f"Tem certeza que deseja reativar {user['username']}? "
            "O acesso será restaurado e ele(a) poderá fazer login novamente "
            "com a senha atual (ou a última gerada em um reset).",
            "Reativar",
        ):
            return

        self._clear_error()
        run_in_background(
            lambda: api_client.reactivate_user(user["user_id"]),
            self._on_mutation_ok,
            self._on_error,
        )

    # --- reset password -----------------------------------------------------

    def _on_reset_click(self, user: dict) -> None:
        if not self._confirm(
            "Gerar nova senha",
            f"Uma nova senha será gerada para {user['username']} e a senha atual "
            "deixará de funcionar. Deseja continuar?",
            "Gerar nova senha",
        ):
            return

        self._clear_error()
        run_in_background(
            lambda: api_client.reset_password(user["user_id"]),
            lambda resp: self._on_password_reset(user, resp),
            self._on_error,
        )

    def _on_password_reset(self, user: dict, resp: dict) -> None:
        self._reveal_password(user["username"], resp["generated_password"])
        self._load_users()

    # --- rename (Editar nome) -----------------------------------------------------

    def _on_rename_click(self, user: dict) -> None:
        dialog = _RenameDialog(
            user["username"],
            on_blank=lambda: self._show_error(_BLANK_USERNAME_MSG),
            parent=self.window(),
        )
        if not dialog.exec():
            return

        new_name = dialog.new_username()
        self._clear_error()
        run_in_background(
            lambda: api_client.rename_user(user["user_id"], new_name),
            self._on_mutation_ok,
            self._on_error,
        )

    # --- shared helpers -----------------------------------------------------

    def _confirm(self, title: str, body: str, yes_text: str, destructive: bool = False) -> bool:
        """Show a `MessageBox` confirmation, copy locked byte-for-byte to
        05-UI-SPEC.md's Copywriting Contract. Returns True iff the user
        confirmed (clicked the relabeled `yesButton`).
        """
        box = MessageBox(title, body, self.window())
        box.yesButton.setText(yes_text)
        box.cancelButton.setText("Cancelar")
        if destructive:
            _style_destructive(box.yesButton)
        return bool(box.exec())

    def _reveal_password(self, username: str, generated_password: str) -> None:
        dialog = _PasswordRevealDialog(username, generated_password, parent=self.window())
        dialog.exec()

    def _on_error(self, exc: Exception) -> None:
        self._add_button.setEnabled(True)
        self._show_error(getattr(exc, "detail", str(exc)))

    def _show_error(self, text: str) -> None:
        self._clear_error()
        self._error_bar = InfoBar.error(
            title="",
            content=text,
            duration=-1,
            position=InfoBarPosition.TOP,
            parent=self,
        )

    def _clear_error(self) -> None:
        if self._error_bar is not None:
            self._error_bar.close()
            self._error_bar = None

    # --- live theme toggle (modo-noturno-bugado) -----------------------

    def refresh_theme(self) -> None:
        """Re-apply destructive-button coloring on already-rendered user
        rows after a live theme toggle, without re-fetching the user list.

        `_style_destructive`'s color choice is decided via `isDarkTheme()`
        at row-build time (`_build_user_row`) and is NOT reactive to
        `qfluentwidgets.setTheme()` on its own (it's a manual QSS append
        on a plain `PushButton`, not something the library's own
        stylesheet-manager tracks) — called by `MainWindow.refresh_theme()`
        (in turn called by `main.py::_RootWindow._toggle_theme`) in place
        of the old rebuild-the-whole-view approach.
        """
        for i in range(self._list_layout.count()):
            item = self._list_layout.itemAt(i)
            row = item.widget() if item is not None else None
            if row is None:
                continue
            for button in row.findChildren(PushButton):
                if button.text() in ("Desativar", "Excluir"):
                    _style_destructive(button)
