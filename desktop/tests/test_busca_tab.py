"""Testes qtbot para BuscaTab — dispatch/progress (BUSCA-06), resultados,
empty-state, erro, e exportação de PDF (ENTREGA-01).

Segue o idiom `_Captured`/stub estabelecido em 05-PATTERNS.md (Test
Patterns) e já usado em `test_login_page.py`: `run_in_background` é
monkeypatched no módulo `busca_tab` para capturar `fn`/`on_success`/
`on_error` sem disparar rede real nem QThreadPool. Assinatura do stub já
reflete a nova (sem `root`): `stub(self, fn, on_success, on_error)`.
"""

from __future__ import annotations

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
    monkeypatch.setattr(busca_tab_module, "run_in_background", cap.stub)
    return cap


@pytest.fixture
def tab(qtbot, captured):
    widget = BuscaTab(_FakeSession())
    qtbot.addWidget(widget)
    # Discard the mount-time profile-fetch dispatch (_fetch_curriculo_state)
    # so every existing search test's `captured.calls == 1` assertion stays
    # valid — it only cares about the dispatch triggered by the test itself.
    captured.calls = 0
    captured.fn = captured.on_success = captured.on_error = None
    return widget


def _cards(tab: BuscaTab) -> list[ConcursoCard]:
    return [
        tab._results_layout.itemAt(i).widget()
        for i in range(tab._results_layout.count())
        if tab._results_layout.itemAt(i).widget() is not None
    ]


def test_button_disabled_and_progress_shown_during_search(qtbot, tab, captured):
    tab._query_entry.setText("concurso na área de saúde")

    tab._start_search()

    assert captured.calls == 1  # dispatched, but stubbed — no response yet
    assert tab._buscar_button.isEnabled() is False
    assert tab._progress.isHidden() is False
    assert tab._status_label.isHidden() is False
    assert tab._status_label.text() == BuscaTab.LOADING_TEXT


def test_buscar_com_perfil_vazio_usa_query_de_perfil(qtbot, tab, captured):
    tab._query_entry.setText("")
    tab._start_search_perfil()

    assert captured.calls == 1
    assert tab._query_str == BuscaTab._PERFIL_QUERY
    assert tab._buscar_button.isEnabled() is False
    assert tab._buscar_perfil_button.isEnabled() is False


def test_buscar_com_perfil_com_texto_usa_o_texto_digitado(qtbot, tab, captured):
    tab._query_entry.setText("Recife")
    tab._start_search_perfil()

    assert tab._query_str == "Recife"


def test_ambos_botoes_de_busca_reabilitam_apos_sucesso(qtbot, tab, captured):
    tab._start_search_perfil()
    captured.on_success({"results": [], "count": 0, "is_empty": True, "message": None})

    assert tab._buscar_button.isEnabled() is True
    assert tab._buscar_perfil_button.isEnabled() is True


def test_success_renders_cards_and_enables_pdf_and_reenables_buscar(qtbot, tab, captured):
    tab._query_entry.setText("concurso na área de saúde")
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

    assert tab._buscar_button.isEnabled() is True
    assert tab._progress.isHidden() is True
    assert tab._status_label.isHidden() is True
    assert tab._btn_gerar_pdf.isEnabled() is True
    assert len(_cards(tab)) == 2
    assert tab._empty_label.isHidden() is True


def test_empty_shows_backend_message_verbatim(qtbot, tab, captured):
    tab._query_entry.setText("algo bem específico")
    tab._start_search()

    response = {"results": [], "count": 0, "is_empty": True, "message": "Nada encontrado"}
    captured.on_success(response)

    assert tab._empty_label.isHidden() is False
    assert tab._empty_label.text() == "Nada encontrado"
    assert len(_cards(tab)) == 0
    assert tab._btn_gerar_pdf.isEnabled() is False


def test_empty_falls_back_when_message_none(qtbot, tab, captured):
    tab._query_entry.setText("algo bem específico")
    tab._start_search()

    response = {"results": [], "count": 0, "is_empty": True, "message": None}
    captured.on_success(response)

    assert tab._empty_label.isHidden() is False
    assert tab._empty_label.text() == BuscaTab.EMPTY_FALLBACK


def test_error_shows_detail_verbatim_via_infobar(qtbot, tab, captured):
    class _FakeSearchFailedError(Exception):
        def __init__(self, detail):
            self.detail = detail
            super().__init__(detail)

    tab._query_entry.setText("concurso na área de saúde")
    tab._start_search()

    captured.on_error(_FakeSearchFailedError("Falha na IA"))

    assert tab._buscar_button.isEnabled() is True
    assert tab._progress.isHidden() is True
    assert tab._error_bar is not None
    assert tab._error_bar.content == "Falha na IA"


def test_gerar_pdf_writes_file_and_shows_pdf_row(qtbot, tab, captured, monkeypatch, tmp_path):
    from app.ui import busca_tab as module

    monkeypatch.setattr(
        "app.pdf_export.gerar_pdf",
        lambda resultados, query, extracted_summary=None: b"%PDF-1.4 test",
    )
    monkeypatch.setattr("app.config.APP_DIR", tmp_path)
    monkeypatch.setattr(tab, "_mostrar_popup_pdf_gerado", lambda: None)

    tab._resultados = [{"titulo": "Concurso A", "cargos": [], "datas": {}, "noticia": {}}]
    tab._query_str = "busca teste"

    tab._gerar_pdf()

    assert tab._pdf_path == tmp_path / "resultados.pdf"
    assert tab._pdf_path.exists()
    assert tab._pdf_path.read_bytes() == b"%PDF-1.4 test"
    assert tab._pdf_row.isHidden() is False


def test_refresh_theme_restyles_rendered_cards_without_losing_state(qtbot, tab, captured):
    """modo-noturno-bugado: a live theme toggle must re-style already
    rendered ConcursoCards in place (chip QSS is decided via isDarkTheme()
    at construction time, not reactive to setTheme()) WITHOUT discarding
    _resultados/_query_str or re-querying the API.
    """
    tab._query_entry.setText("concurso na área de saúde")
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

    cards = _cards(tab)
    assert len(cards) == 2
    calls_before = captured.calls

    refreshed = []
    for card in cards:
        card.refresh_theme = lambda card=card: refreshed.append(card)

    tab.refresh_theme()

    assert refreshed == cards  # every rendered card got refreshed
    assert captured.calls == calls_before  # no re-query dispatched
    assert tab._resultados == response["results"]  # state untouched
    assert tab._query_str == "concurso na área de saúde"
    assert _cards(tab) == cards  # same instances — nothing rebuilt


def test_refresh_theme_is_a_noop_with_no_results(qtbot, tab):
    tab.refresh_theme()  # must not raise when no cards are rendered yet
    assert _cards(tab) == []


def test_gerar_pdf_dispara_popup(qtbot, tab, captured, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.pdf_export.gerar_pdf",
        lambda resultados, query, extracted_summary=None: b"%PDF-1.4 test",
    )
    monkeypatch.setattr("app.config.APP_DIR", tmp_path)

    calls: list[None] = []
    monkeypatch.setattr(tab, "_mostrar_popup_pdf_gerado", lambda: calls.append(None))

    tab._resultados = [{"titulo": "Concurso A", "cargos": [], "datas": {}, "noticia": {}}]
    tab._query_str = "busca teste"

    tab._gerar_pdf()

    assert len(calls) == 1


def test_pdf_row_botoes_centralizados(qtbot, tab, captured):
    pdf_row_layout = tab._pdf_row.layout()
    count = pdf_row_layout.count()

    assert pdf_row_layout.itemAt(0).widget() is None  # spacer
    assert pdf_row_layout.itemAt(count - 1).widget() is None  # spacer

    middle_widgets = [
        pdf_row_layout.itemAt(i).widget() for i in range(1, count - 1)
    ]
    assert middle_widgets == [tab._btn_visualizar, tab._btn_salvar, tab._btn_apagar]


def test_gerar_pdf_preserva_show_dinamico(qtbot, tab, captured, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.pdf_export.gerar_pdf",
        lambda resultados, query, extracted_summary=None: b"%PDF-1.4 test",
    )
    monkeypatch.setattr("app.config.APP_DIR", tmp_path)
    monkeypatch.setattr(tab, "_mostrar_popup_pdf_gerado", lambda: None)

    tab._resultados = [{"titulo": "Concurso A", "cargos": [], "datas": {}, "noticia": {}}]
    tab._query_str = "busca teste"

    tab._gerar_pdf()
    assert tab._pdf_row.isHidden() is False

    tab._apagar_pdf()
    assert tab._pdf_row.isHidden() is True


# ---------------------------------------------------------------------------
# quick-260717-i43: "Usar meu currículo" toggle (CURRICULO-TOGGLE-01)
# ---------------------------------------------------------------------------


def test_curriculo_switch_exists_and_starts_unchecked(qtbot, tab, captured):
    assert tab._curriculo_switch.isChecked() is False


def test_search_dispatches_usar_curriculo_true_when_switch_on(qtbot, tab, captured, monkeypatch):
    tab._curriculo_switch.setChecked(True)
    tab._query_entry.setText("concurso na área de saúde")
    tab._start_search()

    recorded = {}

    def _fake_search(query, usar_curriculo=False):
        recorded["usar_curriculo"] = usar_curriculo
        return {"results": [], "count": 0, "is_empty": True, "message": None}

    monkeypatch.setattr(busca_tab_module.api_client, "search", _fake_search)
    captured.fn()

    assert recorded["usar_curriculo"] is True


def test_search_dispatches_usar_curriculo_false_when_switch_off(qtbot, tab, captured, monkeypatch):
    tab._query_entry.setText("concurso na área de saúde")
    tab._start_search()

    recorded = {}

    def _fake_search(query, usar_curriculo=False):
        recorded["usar_curriculo"] = usar_curriculo
        return {"results": [], "count": 0, "is_empty": True, "message": None}

    monkeypatch.setattr(busca_tab_module.api_client, "search", _fake_search)
    captured.fn()

    assert recorded["usar_curriculo"] is False


def test_profile_with_curriculo_enables_switch(qtbot, tab, captured):
    tab._on_profile_loaded_curriculo({"curriculo": "meu cv"})
    assert tab._curriculo_switch.isEnabled() is True


def test_profile_without_curriculo_disables_switch_with_tooltip(qtbot, tab, captured):
    tab._on_profile_loaded_curriculo({"curriculo": None})
    assert tab._curriculo_switch.isEnabled() is False
    assert tab._curriculo_switch.toolTip() == "Anexe seu currículo no Perfil pra usar esta opção"


def test_profile_fetch_error_leaves_switch_enabled(qtbot, tab, captured):
    tab._on_profile_error_curriculo(Exception("boom"))
    assert tab._curriculo_switch.isEnabled() is True


def test_apagar_pdf_removes_file_and_hides_row(qtbot, tab, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.pdf_export.gerar_pdf",
        lambda resultados, query, extracted_summary=None: b"%PDF-1.4 test",
    )
    monkeypatch.setattr("app.config.APP_DIR", tmp_path)
    monkeypatch.setattr(tab, "_mostrar_popup_pdf_gerado", lambda: None)

    tab._resultados = [{"titulo": "Concurso A", "cargos": [], "datas": {}, "noticia": {}}]
    tab._query_str = "busca teste"
    tab._gerar_pdf()
    pdf_path = tab._pdf_path
    assert pdf_path.exists()

    tab._apagar_pdf()

    assert not pdf_path.exists()
    assert tab._pdf_path is None
    assert tab._pdf_row.isHidden() is True
