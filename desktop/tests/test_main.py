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

from app import auth_store
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
