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


def test_refresh_theme_recomputes_chip_colors_on_theme_change(qtbot, monkeypatch):
    """modo-noturno-bugado: chip QSS is decided via isDarkTheme() at
    construction time (_chip_qss), so it does NOT auto-update when
    qfluentwidgets.setTheme() runs — refresh_theme() must recompute it
    on demand (called by BuscaTab.refresh_theme() on a live theme toggle,
    in place of rebuilding the card from scratch).
    """
    from app.ui import concurso_card as concurso_card_module

    monkeypatch.setattr(concurso_card_module, "isDarkTheme", lambda: False)
    concurso = _base_concurso(cargos=["Engenheiro"])
    card = ConcursoCard(concurso)
    qtbot.addWidget(card)

    light_style = _chip_widgets(card)[0].styleSheet()

    monkeypatch.setattr(concurso_card_module, "isDarkTheme", lambda: True)
    card.refresh_theme()

    dark_style = _chip_widgets(card)[0].styleSheet()

    assert light_style != dark_style
    assert "rgba(0, 0, 0, 0.06)" in light_style
    assert "rgba(255, 255, 255, 0.08)" in dark_style


def test_chip_text_color_is_explicit_not_native_palette(qtbot, monkeypatch):
    """modo-noturno-bugado: non-accent chip text used to be
    `color: palette(window-text)`, a QSS palette reference resolved
    against the QApplication's native/OS-influenced QPalette — which
    `qfluentwidgets.setTheme()` never touches — decoupling the chip's
    text color from the app's own in-app theme selection (illegible
    whenever the OS native theme and the in-app theme disagree). The
    color must instead be an explicit value keyed on `isDarkTheme()`,
    exactly like `bg` already was.
    """
    from app.ui import concurso_card as concurso_card_module

    monkeypatch.setattr(concurso_card_module, "isDarkTheme", lambda: False)
    concurso = _base_concurso(cargos=["Engenheiro"])
    card = ConcursoCard(concurso)
    qtbot.addWidget(card)

    light_style = _chip_widgets(card)[0].styleSheet()
    assert "palette(" not in light_style
    assert "color: black" in light_style

    monkeypatch.setattr(concurso_card_module, "isDarkTheme", lambda: True)
    card.refresh_theme()

    dark_style = _chip_widgets(card)[0].styleSheet()
    assert "palette(" not in dark_style
    assert "color: white" in dark_style


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
