"""Testes qtbot para `_RootWindow._toggle_theme` — refresh-in-place em vez
de rebuild completo do `MainWindow` (modo-noturno-bugado, regressao pos
"caixas dentro de caixas": trocar de tema descartava resultados de busca
em memoria porque o toggle reconstruia o MainWindow do zero).

`auth_store.load_session` e monkeypatched para retornar `None` — evita o
auto-login de startup (que dispara `run_in_background`/rede real via
`api_client.get_profile`), mesmo idiom de stub usado nos demais testes de
tela (`test_login_page.py`, `test_busca_tab.py`, `test_admin_tab.py`).
`styles.save_theme_pref` e monkeypatched para um no-op para nao escrever
o `theme.json` real do usuario (`%APPDATA%/ConcursoFinder`) durante os
testes.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app import api_client, auth_store
from app import main as main_module
from app.main import _RootWindow
from app.ui import styles


@dataclass(frozen=True)
class _FakeSession:
    token: str = "tok"
    user_id: str = "u1"
    username: str = "jonas"
    is_admin: bool = False


@pytest.fixture
def root(qtbot, monkeypatch):
    monkeypatch.setattr(auth_store, "load_session", lambda: None)
    monkeypatch.setattr(styles, "save_theme_pref", lambda _name: None)
    window = _RootWindow()
    qtbot.addWidget(window)
    return window


def test_toggle_theme_before_login_is_a_noop(qtbot, root):
    # Still on the login screen (no session yet) — toggling must not crash
    # and must not fabricate a MainWindow out of thin air.
    assert root._main_window is None
    root._toggle_theme()
    assert root._main_window is None


def test_toggle_theme_refreshes_existing_main_window_instead_of_rebuilding(
    qtbot, root, monkeypatch
):
    root._show_main(_FakeSession())
    main_window = root._main_window
    assert main_window is not None

    calls = []
    monkeypatch.setattr(main_window, "refresh_theme", lambda: calls.append(True))

    root._toggle_theme()

    assert root._main_window is main_window  # SAME instance — no rebuild
    assert calls == [True]  # MainWindow.refresh_theme() was invoked


def test_toggle_theme_preserves_busca_tab_search_state(qtbot, root):
    root._show_main(_FakeSession())
    busca = root._main_window._busca_tab

    resultados = [{"titulo": "Concurso A", "cargos": [], "datas": {}, "noticia": {}}]
    busca._resultados = resultados
    busca._query_str = "engenheiro civil"

    root._toggle_theme()

    # Same BuscaTab instance, same in-memory search state — nothing rebuilt.
    assert root._main_window._busca_tab is busca
    assert busca._resultados == resultados
    assert busca._query_str == "engenheiro civil"


def test_toggle_theme_flips_and_persists_theme(qtbot, root, monkeypatch):
    persisted = []
    monkeypatch.setattr(styles, "save_theme_pref", lambda name: persisted.append(name))

    starting_theme = root._theme
    root._toggle_theme()

    expected = styles.THEME_LIGHT if starting_theme == styles.THEME_DARK else styles.THEME_DARK
    assert root._theme == expected
    assert persisted == [expected]


# --- T-04/T-05: auto-login error handling ---


def _make_root_with_saved_session(qtbot, monkeypatch):
    """Build a _RootWindow whose auto-login finds a saved session, capturing
    the run_in_background on_error callback instead of hitting the network."""
    captured = {}

    def _fake_bg(fn, on_success, on_error):
        captured["on_success"] = on_success
        captured["on_error"] = on_error

    monkeypatch.setattr(auth_store, "load_session", lambda: _FakeSession())
    monkeypatch.setattr(styles, "save_theme_pref", lambda _n: None)
    monkeypatch.setattr(main_module, "run_in_background", _fake_bg)
    window = _RootWindow()
    qtbot.addWidget(window)
    return window, captured


def test_auto_login_network_error_keeps_session(qtbot, monkeypatch):
    """T-04: a connection/timeout failure during startup auto-login must NOT
    clear the saved session — only fall back to the login screen."""
    cleared = []
    monkeypatch.setattr(auth_store, "clear_session", lambda: cleared.append(True))
    _window, captured = _make_root_with_saved_session(qtbot, monkeypatch)

    captured["on_error"](api_client.ConnectionFailedError("sem internet"))

    assert cleared == []  # session preserved for a later, connected launch


def test_auto_login_session_expired_clears_session(qtbot, monkeypatch):
    """T-04: a real 401 (SessionExpiredError) DOES clear the saved session."""
    cleared = []
    monkeypatch.setattr(auth_store, "clear_session", lambda: cleared.append(True))
    _window, captured = _make_root_with_saved_session(qtbot, monkeypatch)

    captured["on_error"](api_client.SessionExpiredError("expirada"))

    assert cleared == [True]
