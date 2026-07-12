"""Tests for BuscaTab's click-wiring/state-flip logic (BUSCA-06).

Uses a real `tk.Tk()` root (widget construction/state requires a live Tk
display) but stubs `busca_tab.run_in_background` at the module level so no
real network dispatch/threading happens — these are logic-level tests on
the callback wiring, not full end-to-end/visual tests (per 03-RESEARCH.md's
Validation Architecture note on Tkinter GUI testability).

The Tk root is created once per module (not once per test) and reused: this
environment (Windows/Tcl 8.6/Python 3.14) intermittently raises a spurious
`_tkinter.TclError: Can't find a usable init.tcl` when many `tk.Tk()`
instances are constructed/destroyed back-to-back within one process — a
known Tcl interpreter re-initialization flakiness unrelated to any code in
this module (reproduced with a trivial fixture-only script with zero
`BuscaTab`/`ConcursoCard` involvement). Reusing a single hidden root and
destroying only its children between tests avoids repeated interpreter
teardown/creation and eliminates the flakiness.
"""

import tkinter as tk
from dataclasses import dataclass

import pytest

from app.ui import busca_tab as busca_tab_module
from app.ui.busca_tab import BuscaTab
from app.ui.concurso_card import ConcursoCard


@dataclass(frozen=True)
class _FakeSession:
    token: str = "tok"
    user_id: str = "u1"
    username: str = "jonas"
    is_admin: bool = False


class _Captured:
    """Captures fn/on_success/on_error from a stubbed run_in_background call."""

    def __init__(self):
        self.fn = None
        self.on_success = None
        self.on_error = None
        self.calls = 0

    def stub(self, _root, fn, on_success, on_error):
        self.fn = fn
        self.on_success = on_success
        self.on_error = on_error
        self.calls += 1


@pytest.fixture(scope="module")
def _shared_root():
    r = tk.Tk()
    r.withdraw()
    yield r
    r.destroy()


@pytest.fixture
def root(_shared_root):
    yield _shared_root
    for child in _shared_root.winfo_children():
        child.destroy()


@pytest.fixture
def captured(monkeypatch):
    cap = _Captured()
    monkeypatch.setattr(busca_tab_module, "run_in_background", cap.stub)
    return cap


def test_button_disabled_during_search(root, captured):
    tab = BuscaTab(root, _FakeSession())
    tab._query_entry.insert(0, "concurso na área de saúde")

    tab._start_search()

    assert captured.calls == 1  # dispatched, but stubbed — no response yet
    assert str(tab._buscar_button["state"]) == "disabled"
    assert tab._status_label["text"] == BuscaTab.LOADING_TEXT
    assert tab._progress.winfo_manager() == "pack"


def test_success_renders_cards_and_reenables(root, captured):
    tab = BuscaTab(root, _FakeSession())
    tab._query_entry.insert(0, "concurso na área de saúde")
    tab._start_search()

    response = {
        "results": [
            {"titulo": "Concurso A", "cargos": ["X"], "datas": {}, "noticia": {}},
            {"titulo": "Concurso B", "cargos": ["Y"], "datas": {}, "noticia": {}},
        ],
        "count": 2,
        "is_empty": False,
        "message": None,
    }
    captured.on_success(response)

    assert str(tab._buscar_button["state"]) == "normal"
    cards = [
        child
        for child in tab._results_frame.winfo_children()
        if isinstance(child, ConcursoCard)
    ]
    assert len(cards) == 2


def test_empty_shows_message(root, captured):
    tab = BuscaTab(root, _FakeSession())
    tab._query_entry.insert(0, "algo bem específico")
    tab._start_search()

    response = {"results": [], "count": 0, "is_empty": True, "message": "Nada encontrado"}
    captured.on_success(response)

    assert tab._status_label["text"] == "Nada encontrado"


def test_empty_falls_back_when_message_none(root, captured):
    tab = BuscaTab(root, _FakeSession())
    tab._query_entry.insert(0, "algo bem específico")
    tab._start_search()

    response = {"results": [], "count": 0, "is_empty": True, "message": None}
    captured.on_success(response)

    assert tab._status_label["text"] == BuscaTab.EMPTY_FALLBACK


def test_error_shows_banner_verbatim(root, captured):
    class _FakeSearchFailedError(Exception):
        def __init__(self, detail):
            self.detail = detail
            super().__init__(detail)

    tab = BuscaTab(root, _FakeSession())
    tab._query_entry.insert(0, "concurso na área de saúde")
    tab._start_search()

    captured.on_error(_FakeSearchFailedError("Falha na IA"))

    assert str(tab._buscar_button["state"]) == "normal"
    assert tab._banner["text"] == "Falha na IA"
