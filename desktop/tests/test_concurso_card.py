"""Testes qtbot para ConcursoCard — chips com overflow (D-03), badge NOVO,
e "Copiar link" (ENTREGA-02).

Clipboard é monkeypatched diretamente no objeto retornado por
`QApplication.clipboard()` (substitui o antigo monkeypatch de
`clipboard_clear`/`clipboard_append` do Tk root, per 05-PATTERNS.md Test
Patterns).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from app.ui.concurso_card import ConcursoCard, _OverflowChip


def _chip_widgets(card):
    flow = card._chip_flow
    return [flow.itemAt(i).widget() for i in range(flow.count())]


def _chip_texts(card):
    return [w.text() for w in _chip_widgets(card)]


def _base_concurso(**overrides) -> dict:
    concurso = {
        "titulo": "Concurso Teste",
        "cargos": [],
        "datas": {"fim": "31/12/2026"},
        "noticia": {"link": "https://test.com/edital"},
        "is_new": False,
    }
    concurso.update(overrides)
    return concurso


def test_tres_cargos_sem_overflow(qtbot):
    concurso = _base_concurso(cargos=["Engenheiro", "Analista", "Técnico"])
    card = ConcursoCard(concurso)
    qtbot.addWidget(card)

    texts = _chip_texts(card)
    assert texts == ["Engenheiro", "Analista", "Técnico"]
    assert not any(isinstance(w, _OverflowChip) for w in _chip_widgets(card))


def test_oito_cargos_colapsa_em_cinco_com_overflow_expansivel(qtbot):
    cargos = [f"Cargo {i}" for i in range(1, 9)]  # 8 cargos
    concurso = _base_concurso(cargos=cargos)
    card = ConcursoCard(concurso)
    qtbot.addWidget(card)

    widgets = _chip_widgets(card)
    assert len(widgets) == 6  # 5 chips + 1 controle de overflow
    toggle = widgets[-1]
    assert isinstance(toggle, _OverflowChip)
    assert toggle.text() == "+3 outros"

    qtbot.mouseClick(toggle, Qt.MouseButton.LeftButton)

    widgets = _chip_widgets(card)
    assert len(widgets) == 9  # 8 chips + o controle relabeled
    toggle = widgets[-1]
    assert isinstance(toggle, _OverflowChip)
    assert toggle.text() == "mostrar menos"

    qtbot.mouseClick(toggle, Qt.MouseButton.LeftButton)

    widgets = _chip_widgets(card)
    assert len(widgets) == 6
    assert widgets[-1].text() == "+3 outros"


def test_copiar_link_seta_clipboard_e_mostra_feedback(qtbot, monkeypatch):
    concurso = _base_concurso(cargos=[])
    card = ConcursoCard(concurso)
    qtbot.addWidget(card)

    calls = []
    monkeypatch.setattr(
        QApplication.clipboard(), "setText", lambda text: calls.append(text)
    )

    card._copiar_link()

    assert calls == ["https://test.com/edital"]
    assert card._feedback_label.text() == "Copiado!"


def test_badge_novo_presente_quando_is_new(qtbot):
    concurso = _base_concurso(cargos=[], is_new=True)
    card = ConcursoCard(concurso)
    qtbot.addWidget(card)

    novo_labels = [w for w in card.findChildren(QLabel) if w.text() == "NOVO"]
    assert len(novo_labels) == 1


def test_badge_novo_ausente_quando_nao_new(qtbot):
    concurso = _base_concurso(cargos=[], is_new=False)
    card = ConcursoCard(concurso)
    qtbot.addWidget(card)

    novo_labels = [w for w in card.findChildren(QLabel) if w.text() == "NOVO"]
    assert len(novo_labels) == 0


def test_card_sem_link_omite_botao_copiar_e_mostra_fallback(qtbot):
    concurso = _base_concurso(cargos=[], noticia={"link": ""})
    card = ConcursoCard(concurso)
    qtbot.addWidget(card)

    assert not hasattr(card, "_feedback_label")
    assert not hasattr(card, "_link")

    copiar_buttons = [
        w for w in card.findChildren(QPushButton) if w.text() == "Copiar link"
    ]
    assert copiar_buttons == []

    fallback_labels = [w for w in card.findChildren(QLabel) if w.text() == "link não disponível"]
    assert len(fallback_labels) == 1
