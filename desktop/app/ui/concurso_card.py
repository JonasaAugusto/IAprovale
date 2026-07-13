"""Reusable search-result card widget (D-03 redesign, ENTREGA-02).

`ConcursoCard` is purely presentational: it renders one concurso's title,
cargos, prazo de inscrição and link. It never recomputes `is_new` itself —
that flag arrives pre-computed from the backend.

Field access preserves the verified nested-dict shape (never flattened):
`concurso["titulo"]`, `concurso.get("cargos", [])`, `concurso.get("datas",
{}).get("fim", ...)`, `concurso.get("noticia", {}).get("link", ...)`.

D-03 redesign vs. the Tkinter analog:
- cargos render as neutral pill chips in a `FlowLayout`, collapsing to at
  most 5 with a "+N outros" overflow control that expands/collapses
  ("mostrar menos") instead of one wall-of-text label.
- `is_new` is signaled ONLY by a small "NOVO" pill badge anchored at the
  card's top-right corner — the old full-card background swap for new
  results is removed entirely; every card uses the same surface.

ENTREGA-02: when `noticia.link` is non-empty, a "Copiar link" button copies
the URL to the clipboard and shows "Copiado!" feedback for 1.5s via
`QTimer.singleShot`. Cards with no link omit the button entirely.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, CardWidget, FlowLayout, FluentIcon as FIF, PushButton, StrongBodyLabel
from qfluentwidgets.common.style_sheet import isDarkTheme

from app.ui import styles

_MAX_VISIBLE_CARGOS = 5
_LINK_MISSING_TEXT = "link não disponível"
_COPIED_TEXT = "Copiado!"
_COPIED_FEEDBACK_MS = 1500


def _chip_qss(*, accent: bool) -> str:
    bg = "rgba(255, 255, 255, 0.08)" if isDarkTheme() else "rgba(0, 0, 0, 0.06)"
    color = styles.ACCENT if accent else "palette(window-text)"
    return (
        f"background-color: {bg}; color: {color}; "
        f"border-radius: 9px; padding: {styles.SPACING_XS}px {styles.SPACING_SM}px; "
        "font-size: 12px;"
    )


def _make_chip(text: str) -> QLabel:
    chip = QLabel(text)
    chip.setStyleSheet(_chip_qss(accent=False))
    return chip


class _OverflowChip(QPushButton):
    """Clickable pill toggling the cargo chip list between collapsed/expanded."""

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(_chip_qss(accent=True))


class ConcursoCard(CardWidget):
    def __init__(self, concurso: dict, parent=None) -> None:
        super().__init__(parent)
        self.setClickEnabled(False)

        is_new = bool(concurso.get("is_new"))
        titulo = concurso["titulo"]
        self._cargos = list(concurso.get("cargos", []))
        prazo = concurso.get("datas", {}).get("fim", "não informado")
        link = concurso.get("noticia", {}).get("link", "")
        self._expanded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            styles.SPACING_MD, styles.SPACING_MD, styles.SPACING_MD, styles.SPACING_MD
        )
        layout.setSpacing(styles.SPACING_SM)

        title_row = QHBoxLayout()
        title_label = StrongBodyLabel(titulo, self)
        title_label.setWordWrap(True)
        title_row.addWidget(title_label, 1)
        if is_new:
            title_row.addWidget(self._make_novo_badge(), 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(title_row)

        chip_host = QWidget(self)
        self._chip_flow = FlowLayout(chip_host)
        self._chip_flow.setHorizontalSpacing(styles.SPACING_SM)
        self._chip_flow.setVerticalSpacing(styles.SPACING_SM)
        layout.addWidget(chip_host)
        self._render_chips()

        layout.addWidget(BodyLabel(f"Inscrições até: {prazo}", self))

        link_row = QHBoxLayout()
        link_label = BodyLabel(link or _LINK_MISSING_TEXT, self)
        if link:
            link_label.setStyleSheet(f"color: {styles.ACCENT};")
        link_row.addWidget(link_label)

        if link:
            self._link = link
            copy_button = PushButton(FIF.COPY, "Copiar link", self)
            copy_button.clicked.connect(self._copiar_link)
            link_row.addWidget(copy_button)

            self._feedback_label = CaptionLabel("", self)
            link_row.addWidget(self._feedback_label)

        link_row.addStretch(1)
        layout.addLayout(link_row)

    def _make_novo_badge(self) -> QLabel:
        badge = CaptionLabel("NOVO", self)
        badge.setStyleSheet(
            f"border-radius: 9px; padding: {styles.SPACING_XS}px {styles.SPACING_SM}px; "
            f"background: {styles.COLOR_BADGE_BG}; color: {styles.COLOR_BADGE_FG}; "
            "font-weight: 600;"
        )
        return badge

    def _render_chips(self) -> None:
        self._chip_flow.takeAllWidgets()

        overflow = len(self._cargos) - _MAX_VISIBLE_CARGOS
        visible = (
            self._cargos
            if self._expanded or overflow <= 0
            else self._cargos[:_MAX_VISIBLE_CARGOS]
        )
        for cargo in visible:
            self._chip_flow.addWidget(_make_chip(cargo))

        if overflow > 0:
            label = "mostrar menos" if self._expanded else f"+{overflow} outros"
            toggle = _OverflowChip(label, self)
            toggle.clicked.connect(self._toggle_cargos)
            self._chip_flow.addWidget(toggle)

    def _toggle_cargos(self) -> None:
        self._expanded = not self._expanded
        self._render_chips()

    def refresh_theme(self) -> None:
        """Recompute cargo-chip colors after a live theme toggle.

        Chips are plain `QLabel`/`QPushButton` with hand-built QSS decided
        via `isDarkTheme()` at construction time (`_chip_qss`) — unlike the
        registered qfluentwidgets components used elsewhere (`CardWidget`,
        `StrongBodyLabel`, etc.), they are NOT re-styled automatically by
        `qfluentwidgets.setTheme()`. Called by `BuscaTab.refresh_theme()`
        (in turn called by `MainWindow.refresh_theme()` from
        `main.py::_toggle_theme`) INSTEAD OF rebuilding the card, so
        already-rendered search results survive a theme toggle
        (modo-noturno-bugado). Reuses `_render_chips()`, which already
        recomputes chip QSS from scratch — same code path as the existing
        "+N outros" expand/collapse toggle.
        """
        self._render_chips()

    def _copiar_link(self) -> None:
        QApplication.clipboard().setText(self._link)
        self._feedback_label.setText(_COPIED_TEXT)
        QTimer.singleShot(_COPIED_FEEDBACK_MS, lambda: self._feedback_label.setText(""))
