"""Tests for main_window's tab-visibility logic (D-02).

`visible_tab_labels` is a pure, Qt-free function (no QApplication needed) —
the DESKTOP-01 test target per 05-PATTERNS.md's Test Patterns (admin-tab
conditional test should not require a real Qt widget construction).

Full `MainWindow` widget construction (Pivot tab count/order, Sair button
wiring) is intentionally NOT exercised here with real `BuscaTab`/`AdminTab`
instances — those are already covered by their own test files (05-04/05-05).
The Admin-tab-gating and Sair-wiring acceptance criteria are instead
verified by static inspection (grep for `session.is_admin`/`Sair`, absence
of `.hide(`) per the plan's acceptance criteria — same approach as the
Tkinter analog's `test_main_frame.py`.
"""

import json
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from app.ui.main_window import MainWindow, visible_tab_labels


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


# ---------------------------------------------------------------------------
# refresh_theme() delegation (modo-noturno-bugado) — MainWindow.refresh_theme
# must re-style its child tabs in place rather than being rebuilt itself, so
# main.py::_RootWindow._toggle_theme can keep the same MainWindow instance.
# ---------------------------------------------------------------------------


def test_refresh_theme_delegates_to_busca_and_admin_tabs(qtbot, monkeypatch):
    from app.ui import admin_tab as admin_tab_module
    from app.ui import busca_tab as busca_tab_module
    from app.ui import main_window as main_window_module

    monkeypatch.setattr(admin_tab_module, "run_in_background", lambda *a, **k: None)
    monkeypatch.setattr(busca_tab_module, "run_in_background", lambda *a, **k: None)
    # MainWindow.__init__ also fires the update-check via run_in_background —
    # no-op it here too so no real network call happens during construction.
    monkeypatch.setattr(main_window_module, "run_in_background", lambda *a, **k: None)
    # Popup web (v1.5.2) would block exec() in headless tests — stub it out
    # (lição da quick 260716-w75 aplicada ao popup PDF).
    monkeypatch.setattr(MainWindow, "_mostrar_popup_web", lambda self: None)

    window = MainWindow(
        _FakeSession(is_admin=True), on_logout=lambda: None, on_toggle_theme=lambda: None
    )
    qtbot.addWidget(window)

    calls = []
    monkeypatch.setattr(window._busca_tab, "refresh_theme", lambda: calls.append("busca"))
    monkeypatch.setattr(window._admin_tab, "refresh_theme", lambda: calls.append("admin"))

    window.refresh_theme()

    assert calls == ["busca", "admin"]


def test_refresh_theme_skips_admin_tab_when_absent(qtbot, monkeypatch):
    from app.ui import busca_tab as busca_tab_module
    from app.ui import main_window as main_window_module

    monkeypatch.setattr(busca_tab_module, "run_in_background", lambda *a, **k: None)
    monkeypatch.setattr(main_window_module, "run_in_background", lambda *a, **k: None)
    monkeypatch.setattr(MainWindow, "_mostrar_popup_web", lambda self: None)

    window = MainWindow(
        _FakeSession(is_admin=False), on_logout=lambda: None, on_toggle_theme=lambda: None
    )
    qtbot.addWidget(window)
    assert window._admin_tab is None

    window.refresh_theme()  # must not raise with no admin tab present


# ---------------------------------------------------------------------------
# Auto-update check (U-3) — fired off-thread at the end of MainWindow.__init__.
# ---------------------------------------------------------------------------


def _sync_run_in_background(fn, on_success, on_error):
    """Test double for `run_in_background` that runs `fn` synchronously and
    routes the result straight into `on_success` — mirrors the plan's
    prescribed monkeypatch so the update check can be asserted deterministically."""
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001 - mirrors real worker error routing
        on_error(exc)
    else:
        on_success(result)


def test_update_available_shows_infobar(qtbot, monkeypatch):
    from app.ui import admin_tab as admin_tab_module
    from app.ui import busca_tab as busca_tab_module
    from app.ui import main_window as main_window_module

    monkeypatch.setattr(admin_tab_module, "run_in_background", lambda *a, **k: None)
    monkeypatch.setattr(busca_tab_module, "run_in_background", lambda *a, **k: None)
    monkeypatch.setattr(main_window_module, "run_in_background", _sync_run_in_background)
    monkeypatch.setattr(
        main_window_module,
        "check_for_update",
        lambda: {
            "version": "1.6.0",
            "url": "https://github.com/JonasaAugusto/IAprovale/releases/tag/v1.6.0",
        },
    )
    monkeypatch.setattr(MainWindow, "_mostrar_popup_web", lambda self: None)

    calls = []

    class _FakeBar:
        def addWidget(self, _widget) -> None:
            pass

    def _fake_success(**kwargs):
        calls.append(kwargs)
        return _FakeBar()

    monkeypatch.setattr(main_window_module.InfoBar, "success", _fake_success)

    window = MainWindow(
        _FakeSession(is_admin=False), on_logout=lambda: None, on_toggle_theme=lambda: None
    )
    qtbot.addWidget(window)

    assert len(calls) == 1
    content = f"{calls[0].get('title', '')} {calls[0].get('content', '')}"
    assert "1.6.0" in content


def test_no_update_shows_no_infobar(qtbot, monkeypatch):
    from app.ui import busca_tab as busca_tab_module
    from app.ui import main_window as main_window_module

    monkeypatch.setattr(busca_tab_module, "run_in_background", lambda *a, **k: None)
    monkeypatch.setattr(main_window_module, "run_in_background", _sync_run_in_background)
    monkeypatch.setattr(main_window_module, "check_for_update", lambda: None)
    monkeypatch.setattr(MainWindow, "_mostrar_popup_web", lambda self: None)

    calls = []
    monkeypatch.setattr(
        main_window_module.InfoBar, "success", lambda **kwargs: calls.append(kwargs)
    )

    window = MainWindow(
        _FakeSession(is_admin=False), on_logout=lambda: None, on_toggle_theme=lambda: None
    )
    qtbot.addWidget(window)

    assert calls == []


# ---------------------------------------------------------------------------
# Popup do app web (v1.5.2) — mostrado uma vez por instalação, gated por
# flag persistida em APP_DIR/web_promo.json, roda após o update-check.
# ---------------------------------------------------------------------------


def _make_fake_message_box(exec_returns: bool):
    """Test double para qfluentwidgets.MessageBox — evita o modal nativo
    bloqueante (`.exec()`) em testes headless. `exec_returns` controla o
    retorno de exec() (True == usuário clicou "Sim")."""

    class _FakeMessageBox:
        last_instance: "_FakeMessageBox | None" = None
        instances: list["_FakeMessageBox"] = []

        def __init__(self, title, content, parent=None) -> None:
            self.title = title
            self.content = content
            self.yesButton = MagicMock()
            self.cancelButton = MagicMock()
            _FakeMessageBox.last_instance = self
            _FakeMessageBox.instances.append(self)

        def exec(self) -> bool:
            return exec_returns

    return _FakeMessageBox


def _base_window_kwargs():
    return dict(on_logout=lambda: None, on_toggle_theme=lambda: None)


def test_popup_web_shown_when_flag_absent_and_writes_flag(qtbot, monkeypatch, tmp_path):
    from app.ui import busca_tab as busca_tab_module
    from app.ui import main_window as main_window_module

    monkeypatch.setattr(busca_tab_module, "run_in_background", lambda *a, **k: None)
    monkeypatch.setattr(main_window_module, "run_in_background", lambda *a, **k: None)
    monkeypatch.setattr(main_window_module, "APP_DIR", tmp_path)

    fake_cls = _make_fake_message_box(exec_returns=False)
    monkeypatch.setattr(main_window_module, "MessageBox", fake_cls)

    window = MainWindow(_FakeSession(is_admin=False), **_base_window_kwargs())
    qtbot.addWidget(window)

    assert fake_cls.last_instance is not None
    assert fake_cls.last_instance.title == "IAprovale na web!"

    flag_path = tmp_path / "web_promo.json"
    assert flag_path.exists()
    assert json.loads(flag_path.read_text(encoding="utf-8"))["shown"] is True


def test_popup_web_nao_mostra_quando_flag_presente(qtbot, monkeypatch, tmp_path):
    from app.ui import busca_tab as busca_tab_module
    from app.ui import main_window as main_window_module

    monkeypatch.setattr(busca_tab_module, "run_in_background", lambda *a, **k: None)
    monkeypatch.setattr(main_window_module, "run_in_background", lambda *a, **k: None)
    monkeypatch.setattr(main_window_module, "APP_DIR", tmp_path)

    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "web_promo.json").write_text(
        json.dumps({"shown": True}), encoding="utf-8"
    )

    fake_cls = _make_fake_message_box(exec_returns=True)
    monkeypatch.setattr(main_window_module, "MessageBox", fake_cls)

    window = MainWindow(_FakeSession(is_admin=False), **_base_window_kwargs())
    qtbot.addWidget(window)

    assert fake_cls.instances == []


def test_popup_web_sim_abre_url_via_qdesktopservices(qtbot, monkeypatch, tmp_path):
    from app.ui import busca_tab as busca_tab_module
    from app.ui import main_window as main_window_module

    monkeypatch.setattr(busca_tab_module, "run_in_background", lambda *a, **k: None)
    monkeypatch.setattr(main_window_module, "run_in_background", lambda *a, **k: None)
    monkeypatch.setattr(main_window_module, "APP_DIR", tmp_path)

    fake_cls = _make_fake_message_box(exec_returns=True)
    monkeypatch.setattr(main_window_module, "MessageBox", fake_cls)

    opened = []
    monkeypatch.setattr(
        main_window_module.QDesktopServices,
        "openUrl",
        staticmethod(lambda url: opened.append(url)),
    )

    window = MainWindow(_FakeSession(is_admin=False), **_base_window_kwargs())
    qtbot.addWidget(window)

    assert len(opened) == 1
    assert opened[0].toString() == "https://jonasaaugusto.github.io/IAprovale/"


def test_popup_web_io_failure_never_crasha(qtbot, monkeypatch, tmp_path):
    from app.ui import busca_tab as busca_tab_module
    from app.ui import main_window as main_window_module

    monkeypatch.setattr(busca_tab_module, "run_in_background", lambda *a, **k: None)
    monkeypatch.setattr(main_window_module, "run_in_background", lambda *a, **k: None)

    # APP_DIR aponta pra um caminho que é um ARQUIVO, não diretório — leitura
    # e escrita de web_promo.json sob ele levantam erro (T-sp8-01).
    blocked = tmp_path / "not_a_dir"
    blocked.write_text("x", encoding="utf-8")
    monkeypatch.setattr(main_window_module, "APP_DIR", blocked)

    fake_cls = _make_fake_message_box(exec_returns=True)
    monkeypatch.setattr(main_window_module, "MessageBox", fake_cls)
    monkeypatch.setattr(
        main_window_module.QDesktopServices,
        "openUrl",
        staticmethod(lambda url: None),
    )

    # Não deve levantar exceção.
    window = MainWindow(_FakeSession(is_admin=False), **_base_window_kwargs())
    qtbot.addWidget(window)

    assert fake_cls.last_instance is not None  # leitura falhou -> trata como não-mostrado
