"""Testes qtbot para LoginPage — submit/success/error e o estado D-05.

Segue o idiom `_Captured`/stub estabelecido em 05-PATTERNS.md (Test
Patterns): `run_in_background` é monkeypatched no módulo `login_page` para
capturar `fn`/`on_success`/`on_error` sem disparar rede real nem
QThreadPool. Assinatura do stub já reflete a nova (sem `root`/`self`
implícito de Tkinter): `stub(self, fn, on_success, on_error)`.
"""

from __future__ import annotations

import pytest

from app import auth_store
from app.ui import login_page as login_page_module
from app.ui.login_page import LoginPage


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
    monkeypatch.setattr(login_page_module, "run_in_background", cap.stub)
    return cap


@pytest.fixture
def page(qtbot, captured):
    sessions: list = []
    widget = LoginPage(on_success=sessions.append)
    widget._sessions = sessions  # test-only stash for assertions
    qtbot.addWidget(widget)
    return widget


def test_submit_disables_button_and_shows_connecting_text(qtbot, page, captured):
    """D-05: ao submeter, o botão desabilita e mostra 'Conectando à API...'."""
    page._username_entry.setText("jonas")
    page._password_entry.setText("segredo")

    page._on_submit()

    assert captured.calls == 1
    assert page._entrar_button.text() == "Conectando à API..."
    assert page._entrar_button.isEnabled() is False


def test_login_success_builds_session_with_four_fields(qtbot, page, captured):
    page._username_entry.setText("jonas")
    page._password_entry.setText("segredo")
    page._on_submit()

    response = {
        "token": "tok-123",
        "user_id": "u-1",
        "username": "jonas",
        "is_admin": True,
    }
    captured.on_success(response)

    assert page._entrar_button.text() == "Entrar"
    assert page._entrar_button.isEnabled() is True
    assert page._sessions == [
        auth_store.Session(
            token="tok-123", user_id="u-1", username="jonas", is_admin=True
        )
    ]


def test_login_error_shows_detail_verbatim_and_resets_button(qtbot, page, captured):
    page._username_entry.setText("jonas")
    page._password_entry.setText("errada")
    page._on_submit()

    class _FakeError(Exception):
        detail = "Usuário ou senha inválidos."

    captured.on_error(_FakeError())

    assert page._entrar_button.text() == "Entrar"
    assert page._entrar_button.isEnabled() is True
    assert page._error_bar is not None
    assert page._error_bar.content == "Usuário ou senha inválidos."


def test_enter_in_password_field_submits(qtbot, page, captured):
    page._username_entry.setText("jonas")
    page._password_entry.setText("segredo")

    page._password_entry.returnPressed.emit()

    assert captured.calls == 1
