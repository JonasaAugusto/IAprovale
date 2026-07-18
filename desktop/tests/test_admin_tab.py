"""Testes qtbot para AdminTab — CRUD completo (D-02, DESKTOP-01).

Segue o idiom `_Captured`/stub estabelecido em 05-PATTERNS.md (Test
Patterns): `run_in_background` é monkeypatched no módulo `admin_tab` para
capturar `fn`/`on_success`/`on_error` sem disparar rede real nem
QThreadPool. Assinatura do stub já reflete a nova (sem `root`):
`stub(self, fn, on_success, on_error)`.

Onde acionar o `MessageBox`/`MessageBoxBase` real complicaria o teste
headless (modais bloqueantes via `.exec()`), a copy é verificada via
`inspect.getsource` sobre os métodos que constroem o diálogo — mesmo
espírito do Phase 3, que verificou copy via grep quando o modal real era
flaky em headless.
"""

from __future__ import annotations

import inspect

import pytest

from app.ui import admin_tab as admin_tab_module
from app.ui.admin_tab import AdminTab


class _Captured:
    def __init__(self) -> None:
        self.fn = None
        self.on_success = None
        self.on_error = None
        self.calls = 0

    def stub(self, fn, on_success, on_error) -> None:
        self.fn = fn
        self.on_success = on_success
        self.on_error = on_error
        self.calls += 1


@pytest.fixture
def captured(monkeypatch):
    cap = _Captured()
    monkeypatch.setattr(admin_tab_module, "run_in_background", cap.stub)
    return cap


class _FakeSession:
    def __init__(self, user_id: str, username: str = "jonas", is_admin: bool = True) -> None:
        self.user_id = user_id
        self.username = username
        self.is_admin = is_admin


@pytest.fixture
def tab(qtbot, captured):
    session = _FakeSession(user_id="admin-1")
    widget = AdminTab(session)
    qtbot.addWidget(widget)
    return widget


# ---------------------------------------------------------------------------
# (a) self-row guard: Excluir hidden on the acting admin's own row
# ---------------------------------------------------------------------------


def test_own_row_hides_excluir_other_row_shows_it(qtbot, tab, captured):
    users = [
        {"user_id": "admin-1", "username": "jonas", "is_admin": True, "is_active": True},
        {"user_id": "user-2", "username": "ana", "is_admin": False, "is_active": True},
    ]
    # _load_users() ran on construction; drive its stubbed on_success directly.
    captured.on_success(users)

    from qfluentwidgets import PushButton

    rows = [
        tab._list_layout.itemAt(i).widget()
        for i in range(tab._list_layout.count())
        if tab._list_layout.itemAt(i).widget() is not None
    ]
    assert len(rows) == 2

    own_row_buttons = [b.text() for b in rows[0].findChildren(PushButton)]
    other_row_buttons = [b.text() for b in rows[1].findChildren(PushButton)]

    assert "Excluir" not in own_row_buttons
    assert "Excluir" in other_row_buttons
    # Button order (per 05-UI-SPEC.md Admin tab contract) preserved on the
    # non-self row: Editar nome, Gerar nova senha, Desativar, Excluir.
    assert other_row_buttons == ["Editar nome", "Gerar nova senha", "Desativar", "Excluir"]
    assert own_row_buttons == ["Editar nome", "Gerar nova senha", "Desativar"]


def test_inactive_user_shows_reativar_not_desativar(qtbot, tab, captured):
    users = [
        {"user_id": "user-3", "username": "bob", "is_admin": False, "is_active": False},
    ]
    captured.on_success(users)

    from qfluentwidgets import PushButton

    row = tab._list_layout.itemAt(0).widget()
    button_texts = [b.text() for b in row.findChildren(PushButton)]
    assert "Reativar" in button_texts
    assert "Desativar" not in button_texts


# ---------------------------------------------------------------------------
# (b) confirmation copy locked byte-for-byte (verified via source inspection,
#     since MessageBox.exec() is a blocking native modal in headless tests)
# ---------------------------------------------------------------------------


def test_deactivate_confirmation_copy_matches_ui_spec():
    src = inspect.getsource(AdminTab._on_deactivate_click)
    assert "Desativar usuário" in src
    assert (
        "O acesso será revogado imediatamente e a sessão ativa dele será encerrada." in src
    )
    assert '"Desativar"' in src


def test_reactivate_confirmation_copy_matches_ui_spec():
    src = inspect.getsource(AdminTab._on_reactivate_click)
    assert "Reativar usuário" in src
    assert "poderá fazer login novamente" in src
    assert '"Reativar"' in src


def test_delete_confirmation_copy_matches_ui_spec():
    src = inspect.getsource(AdminTab._on_delete_click)
    assert "Excluir usuário" in src
    assert "Esta ação é PERMANENTE" in src
    assert '"Excluir"' in src


def test_reset_password_confirmation_copy_matches_ui_spec():
    src = inspect.getsource(AdminTab._on_reset_click)
    assert "Gerar nova senha" in src
    assert "a senha atual" in src


def test_password_reveal_dialog_copy_matches_ui_spec():
    src = inspect.getsource(admin_tab_module._PasswordRevealDialog)
    assert "Nova senha gerada" in src
    assert "Senha para" in src
    assert "Anote ou copie agora — ela não será mostrada novamente." in src
    assert "Copiar senha" in src
    assert "Fechar" in src


def test_rename_dialog_copy_matches_ui_spec():
    src = inspect.getsource(admin_tab_module._RenameDialog)
    assert "Editar nome de usuário" in src
    assert "Novo nome de usuário para" in src
    assert "Salvar" in src
    assert "Cancelar" in src


# ---------------------------------------------------------------------------
# (c) create success reveals the password then reloads the list
# ---------------------------------------------------------------------------


def test_create_success_reveals_password_then_reloads(qtbot, tab, captured, monkeypatch):
    revealed = []
    monkeypatch.setattr(
        tab,
        "_reveal_password",
        lambda username, password: revealed.append((username, password)),
    )

    tab._username_entry.setText("nova")
    calls_before = captured.calls
    tab._on_add_click()
    assert captured.calls == calls_before + 1

    captured.on_success({"username": "nova", "generated_password": "s3nha-forte"})

    assert revealed == [("nova", "s3nha-forte")]
    # _load_users() dispatched again after the reveal (reload-after-mutate).
    assert captured.calls == calls_before + 2


def test_reset_password_success_reveals_and_reloads(qtbot, tab, captured, monkeypatch):
    revealed = []
    monkeypatch.setattr(
        tab,
        "_reveal_password",
        lambda username, password: revealed.append((username, password)),
    )

    calls_before = captured.calls
    user = {"user_id": "user-2", "username": "ana", "is_admin": False, "is_active": True}
    tab._on_password_reset(user, {"generated_password": "outra-senha"})

    assert revealed == [("ana", "outra-senha")]
    # _load_users() dispatched again for the reload-after-mutate.
    assert captured.calls == calls_before + 1


# ---------------------------------------------------------------------------
# (d) blank username on add-user shows the inline error without dispatching
# ---------------------------------------------------------------------------


def test_blank_username_shows_error_without_dispatch(qtbot, tab, captured):
    calls_before = captured.calls
    tab._username_entry.setText("   ")

    tab._on_add_click()

    assert captured.calls == calls_before
    assert tab._error_bar is not None
    assert tab._error_bar.content == "Informe um nome de usuário."


# ---------------------------------------------------------------------------
# (e) live theme toggle (modo-noturno-bugado) — refresh destructive-button
#     coloring in place, without re-fetching the user list, and without
#     unbounded stylesheet growth across repeated toggles
# ---------------------------------------------------------------------------


def test_refresh_theme_restyles_destructive_buttons_without_reloading(
    qtbot, tab, captured, monkeypatch
):
    users = [
        {"user_id": "admin-1", "username": "jonas", "is_admin": True, "is_active": True},
        {"user_id": "user-2", "username": "ana", "is_admin": False, "is_active": True},
    ]
    captured.on_success(users)
    calls_before = captured.calls

    original = admin_tab_module._style_destructive
    styled = []

    def _spy(button):
        styled.append(button.text())
        original(button)

    monkeypatch.setattr(admin_tab_module, "_style_destructive", _spy)

    tab.refresh_theme()

    assert captured.calls == calls_before  # no re-fetch of the user list
    # Own row only has "Desativar" (Excluir hidden on the acting admin);
    # the other row has both.
    assert sorted(styled) == ["Desativar", "Desativar", "Excluir"]


def test_style_destructive_is_idempotent_across_repeated_calls(qtbot, tab, captured):
    """Repeated calls (one per live theme toggle) must not keep
    concatenating duplicate destructive-color rules onto the button's
    stylesheet — the base style is cached so each call replaces, not
    appends onto, the previous destructive rule.
    """
    from qfluentwidgets import PushButton

    button = PushButton("Desativar")
    qtbot.addWidget(button)

    admin_tab_module._style_destructive(button)
    once = button.styleSheet()
    admin_tab_module._style_destructive(button)
    twice = button.styleSheet()
    admin_tab_module._style_destructive(button)
    thrice = button.styleSheet()

    assert once == twice == thrice


def test_style_destructive_refreshes_chrome_after_real_theme_change(qtbot, tab, captured):
    """modo-noturno-bugado: _style_destructive used to cache the button's
    pre-destructive stylesheet ONCE (on first call) and reuse that frozen
    snapshot as the append base forever. But `qfluentwidgets.setTheme()`
    (invoked by `styles.apply_theme()` on every live theme toggle) resets
    EVERY registered PushButton's styleSheet() to a fresh, theme-correct
    chrome as a side effect — a snapshot cached before that reset goes
    stale, so a destructive button's chrome (background/border/hover)
    used to stay frozen at whatever theme was active on its FIRST call,
    forever, while its color text kept recomputing correctly. The chrome
    (not just the color) must match a freshly-styled button in the
    CURRENT theme after any number of theme changes.
    """
    from qfluentwidgets import PushButton

    from app.ui import styles

    styles.apply_theme(styles.THEME_LIGHT)
    button = PushButton("Desativar")
    qtbot.addWidget(button)
    admin_tab_module._style_destructive(button)

    # Real theme change (not just isDarkTheme() flipping) — this is what
    # resets every registered PushButton's styleSheet() as a side effect.
    styles.apply_theme(styles.THEME_DARK)
    admin_tab_module._style_destructive(button)

    color = styles.COLOR_DESTRUCTIVE_DARK
    suffix = f"\nQPushButton {{ color: {color}; font-weight: 600; }}"
    assert button.styleSheet().endswith(suffix)
    chrome = button.styleSheet()[: -len(suffix)]

    reference = PushButton("Editar nome")
    qtbot.addWidget(reference)
    assert chrome == reference.styleSheet()

    # Restore light theme so this test doesn't leak global theme state
    # into other tests running in the same process.
    styles.apply_theme(styles.THEME_LIGHT)


def test_add_button_disabled_then_reenabled_on_error(qtbot, tab, captured):
    tab._username_entry.setText("nova")
    tab._on_add_click()
    assert tab._add_button.isEnabled() is False

    class _FakeError(Exception):
        detail = "Acesso negado."

    captured.on_error(_FakeError())

    assert tab._add_button.isEnabled() is True
    assert tab._error_bar.content == "Acesso negado."


# ---------------------------------------------------------------------------
# Busca de usuário (v1.5.1) — filtro client-side normalizado
# ---------------------------------------------------------------------------


def _rendered_usernames(tab) -> list[str]:
    from qfluentwidgets import BodyLabel, CardWidget

    nomes = []
    for i in range(tab._list_layout.count()):
        item = tab._list_layout.itemAt(i)
        row = item.widget() if item is not None else None
        if isinstance(row, CardWidget):
            label = row.findChildren(BodyLabel)[0]
            nomes.append(label.text())
    return nomes


def test_normalizar_remove_acentos_e_caixa():
    assert admin_tab_module._normalizar("MÁRCOS") == "marcos"


def test_filtro_acha_caixa_insensitive(qtbot, tab, captured):
    users = [
        {"user_id": "u1", "username": "marcoshenrique", "is_admin": False, "is_active": True},
        {"user_id": "u2", "username": "ana", "is_admin": False, "is_active": True},
    ]
    captured.on_success(users)

    tab._search_entry.setText("MARCOS")
    assert _rendered_usernames(tab) == ["marcoshenrique"]


def test_filtro_vazio_mostra_todos(qtbot, tab, captured):
    users = [
        {"user_id": "u1", "username": "marcoshenrique", "is_admin": False, "is_active": True},
        {"user_id": "u2", "username": "ana", "is_admin": False, "is_active": True},
    ]
    captured.on_success(users)

    tab._search_entry.setText("MARCOS")
    assert _rendered_usernames(tab) == ["marcoshenrique"]

    tab._search_entry.setText("")
    assert _rendered_usernames(tab) == ["marcoshenrique", "ana"]


def test_filtro_acha_com_acento_no_dado(qtbot, tab, captured):
    users = [
        {"user_id": "u1", "username": "joão", "is_admin": False, "is_active": True},
        {"user_id": "u2", "username": "ana", "is_admin": False, "is_active": True},
    ]
    captured.on_success(users)

    tab._search_entry.setText("joao")
    assert _rendered_usernames(tab) == ["joão"]


def test_filtro_persiste_apos_reload_sem_crash(qtbot, tab, captured):
    users = [
        {"user_id": "u1", "username": "marcoshenrique", "is_admin": False, "is_active": True},
        {"user_id": "u2", "username": "ana", "is_admin": False, "is_active": True},
    ]
    captured.on_success(users)
    tab._search_entry.setText("marcos")
    assert _rendered_usernames(tab) == ["marcoshenrique"]

    # Simula reload-after-mutate (_load_users -> _render_users): o filtro
    # digitado continua aplicado.
    captured.on_success(users)
    assert _rendered_usernames(tab) == ["marcoshenrique"]
