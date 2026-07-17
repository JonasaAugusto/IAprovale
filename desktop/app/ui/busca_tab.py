"""Search screen: query box + Buscar button + progress indicator + results
(PySide6/qfluentwidgets rewrite of `busca_tab.py`, BUSCA-06/D-02/D-03/D-04).

`BuscaTab` is the primary user-facing screen: it lets the user type a
free-text description of what they're looking for, dispatches
`api_client.search()` off the GUI thread via `async_helpers.run_in_background`
(HARD RULE — a direct call inside a clicked-signal handler would freeze the
UI for the full 30-90s round-trip), and renders one `ConcursoCard` per result
into a `SmoothScrollArea` (replaces the Tkinter analog's hand-built
low-level-canvas-widget + Scrollbar + manual `<MouseWheel>` binding entirely).

Click-handling is factored into `_start_search()` so tests can call it
directly and assert the button/progress/label state flips synchronously,
BEFORE `run_in_background` (referenced as a module-level name, monkeypatchable)
actually dispatches anything.

Error handling follows 05-UI-SPEC.md's Error Display Contract: failures are
shown in an inline `InfoBar.error` (never a modal dialog), displaying the
backend's `exc.detail` string verbatim — never a generic/rephrased message.
Empty results show the backend's `message` verbatim, falling back to the
UI-SPEC copy only when `message` is `None`.

The query is sent as raw free text with zero client-side validation/cleaning
(security contract, T-05-INJECT) — the backend's fixed tool-allowlist +
schema validation is the actual prompt-injection boundary; client-side
pre-filtering could weaken it. `SearchLineEdit.setPlaceholderText()` replaces
the Tkinter analog's focus-in/focus-out placeholder simulation entirely —
no such handlers exist here.

PDF export (ENTREGA-01): `_btn_gerar_pdf` is enabled after a successful
non-empty search. `_gerar_pdf()` calls `pdf_export.gerar_pdf()` (REUSED
UNCHANGED) and writes the bytes to `APP_DIR/resultados.pdf`. All PDF-related
imports (`os`, `shutil`, `app.pdf_export`, `app.config`) are lazy imports
inside the methods that use them — reduces surface area for ImportError in
the frozen `.exe` and keeps startup fast.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    FluentIcon as FIF,
    IndeterminateProgressBar,
    InfoBar,
    InfoBarPosition,
    MessageBox,
    MessageBoxBase,
    PrimaryPushButton,
    PushButton,
    SearchLineEdit,
    SmoothScrollArea,
    StrongBodyLabel,
    SwitchButton,
    TransparentPushButton,
)

from app import api_client
from app.async_helpers import run_in_background
from app.ui import styles
from app.ui.concurso_card import ConcursoCard

_QUERY_PLACEHOLDER = "Ex: concurso de saúde com graduação em enfermagem"

# Verbatim section copy from the Tkinter analog's `_mostrar_ajuda` tutorial.
_AJUDA_SECTIONS: list[tuple[str | None, str]] = [
    (
        None,
        "Descreva o que você procura em português natural — não "
        "precisa de comandos especiais, frases completas funcionam "
        "melhor que palavras soltas.",
    ),
    (
        "FORMAÇÃO OU CARGO",
        "Cite a área ou cargo que te interessa: \"concurso de "
        "enfermagem\", \"vaga de técnico em informática\", "
        "\"professor de matemática\". Se você não citar nada, o "
        "sistema usa automaticamente a formação salva no seu "
        "perfil.",
    ),
    (
        "ONDE BUSCAR",
        "- Brasil todo: não cite estado nem cidade — a busca é "
        "ampla.\n"
        "- Um estado específico: cite o nome ou a sigla — "
        "\"concurso em SP\", \"concurso na Bahia\".\n"
        "- Uma cidade específica: cite cidade + estado — "
        "\"concurso em Campinas, SP\".\n"
        "- Uma região inteira: cite a região — \"concursos no "
        "Nordeste\", \"concursos no Sul do país\".",
    ),
    (
        "BUSCANDO PARA OUTRA PESSOA",
        "Mencione a relação — \"concurso para minha esposa, que é "
        "engenheira\", \"meu amigo é professor, tem vaga pra "
        "ele?\". O sistema entende que a formação citada é de "
        "outra pessoa, sem mexer no seu perfil salvo.",
    ),
    (
        "CONCURSOS DE PROFESSOR",
        "Cite \"professor\" ou \"docente\" na busca para focar em "
        "vagas de magistério.",
    ),
    (
        "COMBINE PARA IR MAIS FUNDO",
        "Junte formação + local numa frase só: \"vaga de "
        "enfermeiro em Recife\", \"técnico em edificações no "
        "Paraná\", \"concursos de saúde no Nordeste\". Quanto mais "
        "natural e específica a frase, melhor o resultado — o "
        "sistema já filtra automaticamente só o que tem "
        "inscrições abertas e aceita a sua formação.",
    ),
]


class _AjudaDialog(MessageBoxBase):
    """Read-only 'Como pesquisar' tutorial modal.

    Reproduces the same section headings/body copy as the Tkinter analog's
    `_mostrar_ajuda` (`tk.Text` inside a centered `Toplevel`) inside a
    `SmoothScrollArea`, auto-centered/masked by `MessageBoxBase` — no manual
    geometry-centering code survives from the analog. Only a single
    `Fechar` button is shown (the primary `yesButton` is hidden; the modal
    is read-only, there is nothing to confirm).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.viewLayout.addWidget(StrongBodyLabel("Como pesquisar", self.widget))

        scroll = SmoothScrollArea(self.widget)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background: transparent; border: none;}")
        scroll.setMinimumSize(420, 320)

        content = QWidget(scroll)
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(styles.SPACING_SM)

        for heading, body in _AJUDA_SECTIONS:
            if heading is not None:
                heading_label = StrongBodyLabel(heading, content)
                content_layout.addWidget(heading_label)
            body_label = BodyLabel(body, content)
            body_label.setWordWrap(True)
            content_layout.addWidget(body_label)

        content_layout.addStretch(1)
        scroll.setWidget(content)
        self.viewLayout.addWidget(scroll)

        self.hideYesButton()
        self.cancelButton.setText("Fechar")


class BuscaTab(QWidget):
    LOADING_TEXT = "Procurando..."
    EMPTY_FALLBACK = (
        "Nenhum concurso encontrado com esses critérios. "
        "Tente ajustar sua busca ou sua formação salva."
    )
    _CURRICULO_TOOLTIP_DEFAULT = (
        "Quando ligado, a IA lê o currículo salvo no seu perfil pra achar "
        "concursos que combinam com você."
    )
    _CURRICULO_TOOLTIP_DISABLED = "Anexe seu currículo no Perfil pra usar esta opção"

    def __init__(self, session, parent=None) -> None:
        super().__init__(parent)
        self._session = session

        # PDF state — tracked here so all _*_pdf methods share state cleanly
        self._pdf_path: Path | None = None
        self._resultados: list[dict] = []
        self._query_str: str = ""
        self._extracted_summary: str | None = None
        self._error_bar: InfoBar | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            styles.SPACING_LG, styles.SPACING_LG, styles.SPACING_LG, styles.SPACING_LG
        )
        layout.setSpacing(styles.SPACING_MD)

        query_row = QHBoxLayout()
        query_row.setSpacing(styles.SPACING_SM)

        self._query_entry = SearchLineEdit(self)
        self._query_entry.setPlaceholderText(_QUERY_PLACEHOLDER)
        self._query_entry.returnPressed.connect(self._start_search)
        query_row.addWidget(self._query_entry, 1)

        self._buscar_button = PrimaryPushButton("Buscar", self)
        self._buscar_button.clicked.connect(self._start_search)
        query_row.addWidget(self._buscar_button)

        # Busca guiada pelo perfil: pode deixar a caixa vazia (procura "na minha
        # área") ou digitar só o que muda (localização/cargo). A IA completa o
        # resto com o seu perfil. Ícone de pessoa reforça a ideia visualmente.
        self._buscar_perfil_button = PushButton(FIF.PEOPLE, "Buscar com meu perfil", self)
        self._buscar_perfil_button.setToolTip(
            "Busca com base no seu perfil. Pode deixar a caixa vazia, ou digitar "
            "só a localização/cargo — o resto a IA usa do seu perfil."
        )
        self._buscar_perfil_button.clicked.connect(self._start_search_perfil)
        query_row.addWidget(self._buscar_perfil_button)

        layout.addLayout(query_row)

        # Linha de ações secundárias: ajuda (esquerda) + Gerar PDF (direita,
        # habilitado após uma busca com resultados). Tira o excesso de botões da
        # linha de busca, deixando-a limpa.
        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(styles.SPACING_SM)

        self._help_button = TransparentPushButton(FIF.HELP, "Como pesquisar", self)
        self._help_button.clicked.connect(self._mostrar_ajuda)
        actions_row.addWidget(self._help_button)

        # Toggle explícito e visível (CURRICULO-TOGGLE-01): desligado por
        # padrão a cada sessão (não persiste), habilitado por padrão
        # (fail-open) até a busca de perfil em background decidir o
        # contrário — ver _fetch_curriculo_state.
        self._curriculo_switch = SwitchButton(self)
        self._curriculo_switch.setOnText("Usar meu currículo")
        self._curriculo_switch.setOffText("Usar meu currículo")
        self._curriculo_switch.setChecked(False)
        self._curriculo_switch.setToolTip(self._CURRICULO_TOOLTIP_DEFAULT)
        actions_row.addWidget(self._curriculo_switch)

        actions_row.addStretch(1)

        self._btn_gerar_pdf = PushButton(FIF.DOCUMENT, "Gerar PDF", self)
        self._btn_gerar_pdf.setEnabled(False)
        self._btn_gerar_pdf.clicked.connect(self._gerar_pdf)
        actions_row.addWidget(self._btn_gerar_pdf)

        layout.addLayout(actions_row)

        # Progress indicator + loading text (BUSCA-06) — hidden until a
        # search is in flight.
        self._progress = IndeterminateProgressBar(self)
        self._progress.hide()
        layout.addWidget(self._progress)

        self._status_label = CaptionLabel("", self)
        self._status_label.hide()
        layout.addWidget(self._status_label)

        # PDF action row — hidden until first PDF is generated (ENTREGA-01).
        self._pdf_row = QWidget(self)
        pdf_row_layout = QHBoxLayout(self._pdf_row)
        pdf_row_layout.setContentsMargins(0, 0, 0, 0)
        pdf_row_layout.setSpacing(styles.SPACING_SM)

        pdf_row_layout.addStretch(1)

        self._btn_visualizar = PushButton("Visualizar", self._pdf_row)
        self._btn_visualizar.clicked.connect(self._visualizar_pdf)
        pdf_row_layout.addWidget(self._btn_visualizar)

        self._btn_salvar = PushButton("Salvar", self._pdf_row)
        self._btn_salvar.clicked.connect(self._salvar_pdf)
        pdf_row_layout.addWidget(self._btn_salvar)

        self._btn_apagar = PushButton("Apagar", self._pdf_row)
        self._btn_apagar.clicked.connect(self._apagar_pdf)
        pdf_row_layout.addWidget(self._btn_apagar)

        pdf_row_layout.addStretch(1)
        self._pdf_row.hide()
        layout.addWidget(self._pdf_row)

        # Empty-state label — shown in place of the results list.
        self._empty_label = BodyLabel("", self)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

        # Results scroll area — replaces the Tkinter analog's hand-built
        # low-level-canvas-widget + Scrollbar + manual <MouseWheel> binding entirely.
        self._scroll_area = SmoothScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet(
            "QScrollArea{background: transparent; border: none;}"
        )

        self._results_container = QWidget(self)
        self._results_container.setStyleSheet("background: transparent;")
        self._results_layout = QVBoxLayout(self._results_container)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(styles.SPACING_SM)
        self._results_layout.addStretch(1)

        self._scroll_area.setWidget(self._results_container)
        layout.addWidget(self._scroll_area, 1)

        self._fetch_curriculo_state()

    # ------------------------------------------------------------------
    # Search dispatch (BUSCA-06)
    # ------------------------------------------------------------------

    _PERFIL_QUERY = "concursos na minha área"

    def _start_search(self) -> None:
        """Busca o texto digitado (a IA já usa o seu perfil por baixo)."""
        self._dispatch_search(self._query_entry.text())

    def _start_search_perfil(self) -> None:
        """Busca guiada pelo perfil: caixa vazia -> procura "na minha área";
        com texto -> usa o que você digitou (a IA completa com o perfil)."""
        query = self._query_entry.text().strip() or self._PERFIL_QUERY
        self._dispatch_search(query)

    def _dispatch_search(self, query: str) -> None:
        self._clear_error()
        self._clear_cards()
        self._empty_label.hide()

        # Guarda o texto REALMENTE enviado (pode diferir da caixa numa busca por
        # perfil com caixa vazia) — usado no cabeçalho do PDF.
        self._query_str = query
        self._set_search_enabled(False)
        self._progress.show()
        self._status_label.setText(self.LOADING_TEXT)
        self._status_label.show()

        run_in_background(
            lambda: api_client.search(query, usar_curriculo=self._curriculo_switch.isChecked()),
            self._on_success,
            self._on_error,
        )

    def _set_search_enabled(self, enabled: bool) -> None:
        self._buscar_button.setEnabled(enabled)
        self._buscar_perfil_button.setEnabled(enabled)

    # ------------------------------------------------------------------
    # "Usar meu currículo" toggle state (CURRICULO-TOGGLE-01) — a
    # background profile fetch on mount decides whether the switch is
    # enabled. Does NOT block UI construction (dispatched via
    # run_in_background like every other network call in this file).
    # ------------------------------------------------------------------

    def _fetch_curriculo_state(self) -> None:
        run_in_background(
            lambda: api_client.get_profile(),
            self._on_profile_loaded_curriculo,
            self._on_profile_error_curriculo,
        )

    def _on_profile_loaded_curriculo(self, profile: dict) -> None:
        if profile.get("curriculo"):
            self._curriculo_switch.setEnabled(True)
            self._curriculo_switch.setToolTip(self._CURRICULO_TOOLTIP_DEFAULT)
        else:
            self._curriculo_switch.setEnabled(False)
            self._curriculo_switch.setToolTip(self._CURRICULO_TOOLTIP_DISABLED)

    def _on_profile_error_curriculo(self, exc: Exception) -> None:
        # Fail-open: the backend ignores usar_curriculo when there's no
        # saved currículo, so leaving the switch enabled on a profile-fetch
        # error is safe. No-op, kept as an explicit method so it stays
        # greppable/testable.
        pass

    def _on_success(self, response: dict) -> None:
        self._stop_progress()
        self._set_search_enabled(True)
        self._clear_cards()

        self._resultados = response.get("results", [])
        self._extracted_summary = response.get("extracted_summary")

        self._btn_gerar_pdf.setEnabled(bool(self._resultados))

        for concurso in self._resultados:
            card = ConcursoCard(concurso, self._results_container)
            self._results_layout.insertWidget(self._results_layout.count() - 1, card)

        if response.get("is_empty"):
            message = response.get("message")
            self._empty_label.setText(
                message if message is not None else self.EMPTY_FALLBACK
            )
            self._empty_label.show()
        else:
            self._empty_label.hide()

    def _on_error(self, exc: Exception) -> None:
        self._stop_progress()
        self._set_search_enabled(True)
        self._show_error(getattr(exc, "detail", str(exc)))

    def _stop_progress(self) -> None:
        self._progress.hide()
        self._status_label.hide()

    def _clear_cards(self) -> None:
        # Layout always keeps a trailing stretch item (no widget) as its
        # last entry — remove everything before it.
        while self._results_layout.count() > 1:
            item = self._results_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _show_error(self, text: str) -> None:
        self._clear_error()
        self._error_bar = InfoBar.error(
            title="",
            content=text,
            duration=-1,
            position=InfoBarPosition.TOP,
            parent=self,
        )

    def _clear_error(self) -> None:
        if self._error_bar is not None:
            self._error_bar.close()
            self._error_bar = None

    # ------------------------------------------------------------------
    # Live theme toggle (modo-noturno-bugado) — refresh non-reactive
    # widgets in place instead of losing search state to a full rebuild.
    # ------------------------------------------------------------------

    def refresh_theme(self) -> None:
        """Re-style already-rendered `ConcursoCard`s after a live theme
        toggle, without re-querying the API or discarding `_resultados`/
        `_query_str`. Called by `MainWindow.refresh_theme()` (in turn
        called by `main.py::_RootWindow._toggle_theme`) in place of the
        old rebuild-the-whole-view approach — see `ConcursoCard.refresh_theme`
        for why cards specifically need this (chip QSS is decided via
        `isDarkTheme()` at construction time, not reactive).
        """
        for i in range(self._results_layout.count()):
            item = self._results_layout.itemAt(i)
            widget = item.widget() if item is not None else None
            if isinstance(widget, ConcursoCard):
                widget.refresh_theme()

    # ------------------------------------------------------------------
    # Tutorial modal — "?" button next to the query row
    # ------------------------------------------------------------------

    def _mostrar_ajuda(self) -> None:
        dialog = _AjudaDialog(parent=self.window())
        dialog.exec()

    # ------------------------------------------------------------------
    # PDF export — ENTREGA-01
    # All imports below are lazy (inside each method) to reduce frozen
    # .exe ImportError surface and keep startup time minimal.
    # ------------------------------------------------------------------

    def _gerar_pdf(self) -> None:
        """Gera o PDF com os resultados atuais e o salva em APP_DIR."""
        from app.pdf_export import gerar_pdf
        from app.config import APP_DIR

        pdf_bytes = gerar_pdf(self._resultados, self._query_str, self._extracted_summary)
        APP_DIR.mkdir(parents=True, exist_ok=True)
        pdf_path = APP_DIR / "resultados.pdf"
        pdf_path.write_bytes(pdf_bytes)
        self._pdf_path = pdf_path

        self._pdf_row.show()
        self._mostrar_popup_pdf_gerado()

    def _mostrar_popup_pdf_gerado(self) -> None:
        """Exibe um popup de sucesso confirmando a geração do PDF.

        Fatorado num método próprio (em vez de inline em `_gerar_pdf`) para
        que os testes possam monkeypatchá-lo — `MessageBox.exec()` é uma
        chamada `QDialog.exec()` bloqueante e travaria a suíte se rodada de
        verdade num teste headless.
        """
        box = MessageBox(
            "PDF gerado",
            "O PDF foi gerado com sucesso. As ações Visualizar, Salvar e "
            "Apagar estão disponíveis abaixo da área de pesquisa.",
            self.window(),
        )
        box.hideCancelButton()
        box.exec()

    def _visualizar_pdf(self) -> None:
        """Abre o PDF gerado no visualizador padrão do Windows."""
        import os

        if self._pdf_path and self._pdf_path.exists():
            os.startfile(str(self._pdf_path))

    def _salvar_pdf(self) -> None:
        """Abre file dialog para o usuário escolher onde salvar uma cópia."""
        if not self._pdf_path or not self._pdf_path.exists():
            return
        import shutil

        dest, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Salvar resultados como...",
            "concursos.pdf",
            "Arquivo PDF (*.pdf)",
        )
        if dest:
            shutil.copy2(self._pdf_path, dest)

    def _apagar_pdf(self) -> None:
        """Remove o arquivo PDF temporário e esconde o pdf_row."""
        if self._pdf_path:
            self._pdf_path.unlink(missing_ok=True)
            self._pdf_path = None
        self._pdf_row.hide()
