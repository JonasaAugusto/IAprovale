"""Diálogo de edição de perfil (v1.1.0, Fase 6).

`PerfilDialog` é um `MessageBoxBase` scrollável (muito campo) que deixa
qualquer usuário logado preencher e PERSISTIR o próprio perfil. Acionado
pelo botão "Perfil" no header (`main_window.py`), pré-populado com o perfil
atual (`api_client.get_profile()`), e salva via `api_client.update_profile()`.

Decisões de UX (do PLANO-v1.1.0-edicao-perfil.md):
- **Formação = checkboxes cumulativos.** Marcar Graduação/Técnico/Pós
  auto-marca Médio; marcar Médio auto-marca Fundamental. Desmarcar um nível
  base desmarca os que dependem dele — mantém o conjunto sempre coerente
  (superior ⇒ médio ⇒ fundamental) sem um diálogo de aviso.
- **Escolaridade/Mobilidade = ComboBox** (lista fixa, dados limpos).
- **Currículo = texto** (1 por conta; salvar substitui). O uso do currículo
  pela IA é v1.3.0 — aqui ele só é persistido.

Nada aqui usa a chave DeepSeek nem qualquer segredo — só fala com o backend
via `api_client` (restrição de segurança do projeto).
"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CheckBox,
    ComboBox,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    MessageBoxBase,
    PushButton,
    StrongBodyLabel,
    TextEdit,
    TitleLabel,
)

from app import api_client, curriculo
from app.async_helpers import run_in_background

# Ordem dos níveis + rótulos. A ordem importa para a lógica cumulativa.
_NIVEIS = [
    ("fundamental", "Ensino Fundamental"),
    ("medio", "Ensino Médio"),
    ("tecnico", "Técnico"),
    ("superior", "Graduação (Superior)"),
    ("pos", "Pós-graduação"),
]

# Níveis que exigem "qual?" (campo de curso) e a coluna de perfil que guarda.
_CURSO_FIELD = {"tecnico": "tecnico", "superior": "graduacao", "pos": "pos_graduacao"}

_UFS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
]

# (rótulo exibido, valor persistido). Índice 0 = "não informado" -> None.
_MOBILIDADE = [
    ("Não informado", None),
    ("Só na minha cidade", "local"),
    ("No meu estado", "estado"),
    ("Qualquer lugar", "qualquer"),
]


def _none_if_blank(text: str) -> str | None:
    text = text.strip()
    return text or None


# Data de formação (v1.4.0): o usuário digita MM/AAAA (leigo); a API fala
# YYYY-MM. A conversão vive nestes dois helpers de módulo, espelháveis nos
# testes.
_MMAAAA_RE = re.compile(r"^(0[1-9]|1[0-2])/(\d{4})$")


def _mmaaaa_to_iso(text: str) -> str | None:
    """"MM/AAAA" -> "AAAA-MM". Vazio -> None. Inválido -> ValueError leigo."""
    text = text.strip()
    if not text:
        return None
    m = _MMAAAA_RE.match(text)
    if not m:
        raise ValueError("Data de formação inválida. Use MM/AAAA, por exemplo 12/2027.")
    mes, ano = m.group(1), m.group(2)
    return f"{ano}-{mes}"


def _iso_to_mmaaaa(iso: str | None) -> str:
    """"AAAA-MM" -> "MM/AAAA". None/vazio/inesperado -> ""."""
    if not iso or len(iso) != 7 or iso[4] != "-":
        return ""
    ano, mes = iso[:4], iso[5:]
    return f"{mes}/{ano}"


class PerfilDialog(MessageBoxBase):
    """Formulário completo de perfil dentro de um MessageBoxBase scrollável."""

    def __init__(self, perfil: dict, parent=None) -> None:
        super().__init__(parent)

        # --- container scrollável (é bastante campo) ---
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumSize(460, 520)
        # Plain QScrollArea/QWidget don't follow qfluentwidgets' theme (setTheme
        # only restyles registered Fluent widgets), so a plain container paints
        # a non-theme background — dark even in light mode. Make the scroll
        # area, its viewport and the form transparent so the MessageBoxBase's
        # own themed (white/dark) background shows through in BOTH themes.
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setStyleSheet("background: transparent;")

        form = QWidget()
        form.setStyleSheet("background: transparent;")
        col = QVBoxLayout(form)
        col.setContentsMargins(4, 4, 12, 4)
        col.setSpacing(8)

        _titulo = TitleLabel("Perfil", form)
        _titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(_titulo)

        _sub = BodyLabel("Quanto mais completo, melhores são as buscas.", form)
        _sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _sub.setWordWrap(True)
        col.addWidget(_sub)

        _nota = CaptionLabel(
            "Após preencher, na busca escreva só o que quer mudar — localização, "
            "cargo, região, órgão. O resto a IA usa do seu perfil.",
            form,
        )
        _nota.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _nota.setWordWrap(True)
        col.addWidget(_nota)

        # --- Formação (checkboxes cumulativos + campos "qual?") ---
        col.addWidget(StrongBodyLabel("Formação", form))
        self._checks: dict[str, CheckBox] = {}
        self._cursos: dict[str, LineEdit] = {}
        self._adjusting = False  # guarda contra reentrância de sinais

        for nivel, rotulo in _NIVEIS:
            check = CheckBox(rotulo, form)
            check.stateChanged.connect(
                lambda _state, n=nivel: self._on_nivel_toggled(n)
            )
            self._checks[nivel] = check
            col.addWidget(check)

            if nivel in _CURSO_FIELD:
                curso = LineEdit(form)
                curso.setPlaceholderText("Qual? (ex: Enfermagem)")
                curso.setEnabled(False)  # habilita quando o nível é marcado
                self._cursos[nivel] = curso
                col.addWidget(curso)

        # --- Formação futura / em andamento ---
        col.addWidget(StrongBodyLabel("Formação futura / em andamento", form))
        self._formacao_futura = LineEdit(form)
        self._formacao_futura.setPlaceholderText("ex: Mestrado em Saúde Coletiva")
        col.addWidget(self._formacao_futura)

        # Data de formação (v1.4.0) — gate do match futuro no backend.
        self._data_formacao_futura = LineEdit(form)
        self._data_formacao_futura.setPlaceholderText("MM/AAAA")
        col.addWidget(self._data_formacao_futura)
        _data_hint = CaptionLabel(
            "Data prevista de formação — usada pra te mostrar concursos que "
            "você poderá prestar quando se formar.",
            form,
        )
        _data_hint.setWordWrap(True)
        col.addWidget(_data_hint)

        # --- Localização (CEP com autopreenchimento) ---
        col.addWidget(StrongBodyLabel("Localização", form))
        cep_row = QHBoxLayout()
        cep_row.setContentsMargins(0, 0, 0, 0)
        self._cep = LineEdit(form)
        self._cep.setPlaceholderText("CEP")
        self._cep.setMaxLength(9)
        self._cep.editingFinished.connect(self._on_buscar_cep)
        cep_row.addWidget(self._cep, 1)
        self._cep_button = PushButton("Buscar", form)
        self._cep_button.clicked.connect(self._on_buscar_cep)
        cep_row.addWidget(self._cep_button)
        col.addLayout(cep_row)
        self._cep_status = CaptionLabel("", form)
        self._cep_status.setWordWrap(True)
        col.addWidget(self._cep_status)

        self._cidade = LineEdit(form)
        self._cidade.setPlaceholderText("Cidade")
        col.addWidget(self._cidade)
        self._uf = ComboBox(form)
        self._uf.setPlaceholderText("UF")
        self._uf.addItems(_UFS)
        self._uf.setCurrentIndex(-1)
        col.addWidget(self._uf)

        # --- Mobilidade ---
        col.addWidget(StrongBodyLabel("Disposição para mudar", form))
        self._mobilidade = ComboBox(form)
        self._mobilidade.addItems([rot for rot, _ in _MOBILIDADE])
        self._mobilidade.setCurrentIndex(0)
        col.addWidget(self._mobilidade)
        _mob_nota = BodyLabel(
            'Isto afeta a busca: com "Só na minha cidade" ou "No meu estado", '
            "quando você não digitar um local na pesquisa, o app mostra concursos "
            'do seu estado. Com "Qualquer lugar", busca no Brasil inteiro.',
            form,
        )
        _mob_nota.setWordWrap(True)
        col.addWidget(_mob_nota)

        # --- Áreas de interesse ---
        col.addWidget(StrongBodyLabel("Áreas de interesse", form))
        self._areas = LineEdit(form)
        self._areas.setPlaceholderText("ex: saúde, educação")
        col.addWidget(self._areas)

        # --- Currículo (colar texto OU anexar PDF/TXT) ---
        # Caminho do arquivo anexado NESTA sessão (para "Visualizar" abrir o PDF
        # de verdade). None quando o texto veio colado ou de um perfil salvo —
        # nesses casos "Visualizar" mostra o texto extraído.
        self._curriculo_path: str | None = None
        col.addWidget(StrongBodyLabel("Currículo", form))
        col.addWidget(
            BodyLabel(
                "Cole/escreva, ou anexe um arquivo (PDF/TXT). Um por conta.", form
            )
        )
        # Estado A (sem anexo): botão "Anexar" + campo de texto editável.
        self._anexar_button = PushButton("Anexar arquivo (PDF/TXT)", form)
        self._anexar_button.clicked.connect(self._on_anexar_curriculo)
        col.addWidget(self._anexar_button)

        # Estado B (anexado): as três ações no lugar do botão "Anexar".
        self._curriculo_actions = QWidget(form)
        self._curriculo_actions.setStyleSheet("background: transparent;")
        actions_row = QHBoxLayout(self._curriculo_actions)
        actions_row.setContentsMargins(0, 0, 0, 0)
        self._ver_button = PushButton("Visualizar currículo", self._curriculo_actions)
        self._ver_button.clicked.connect(self._on_ver_curriculo)
        self._alterar_button = PushButton("Alterar", self._curriculo_actions)
        self._alterar_button.clicked.connect(self._on_anexar_curriculo)
        self._excluir_button = PushButton("Excluir", self._curriculo_actions)
        self._excluir_button.clicked.connect(self._on_excluir_curriculo)
        actions_row.addWidget(self._ver_button)
        actions_row.addWidget(self._alterar_button)
        actions_row.addWidget(self._excluir_button)
        col.addWidget(self._curriculo_actions)

        self._curriculo = TextEdit(form)
        self._curriculo.setPlaceholderText("Cole ou escreva seu currículo aqui...")
        self._curriculo.setFixedHeight(120)
        col.addWidget(self._curriculo)

        col.addStretch(1)

        scroll.setWidget(form)
        self.viewLayout.addWidget(scroll)

        self.yesButton.setText("Salvar")
        self.cancelButton.setText("Cancelar")
        self.widget.setMinimumWidth(520)

        self._prepopular(perfil)

    # --- lógica cumulativa dos níveis ---------------------------------

    def _on_nivel_toggled(self, nivel: str) -> None:
        """Mantém o conjunto de níveis coerente (superior/tecnico/pos ⇒ medio ⇒
        fundamental) e habilita/desabilita o campo 'qual?' correspondente."""
        if self._adjusting:
            return
        self._adjusting = True
        try:
            marcado = self._checks[nivel].isChecked()

            if marcado:
                # marcar um nível alto implica os níveis-base
                if nivel in ("tecnico", "superior", "pos"):
                    self._checks["medio"].setChecked(True)
                if self._checks["medio"].isChecked():
                    self._checks["fundamental"].setChecked(True)
            else:
                # desmarcar um nível-base desmarca os que dependem dele
                if nivel == "fundamental":
                    for n in ("medio", "tecnico", "superior", "pos"):
                        self._checks[n].setChecked(False)
                elif nivel == "medio":
                    for n in ("tecnico", "superior", "pos"):
                        self._checks[n].setChecked(False)

            # habilita cada campo "qual?" conforme seu checkbox
            for n, edit in self._cursos.items():
                enabled = self._checks[n].isChecked()
                edit.setEnabled(enabled)
                if not enabled:
                    edit.clear()
        finally:
            self._adjusting = False

    # --- pré-popular / coletar ----------------------------------------

    def _prepopular(self, perfil: dict) -> None:
        # escolaridade csv -> checkboxes (aciona a lógica cumulativa)
        escolaridade = perfil.get("escolaridade") or ""
        niveis = {tok.strip() for tok in escolaridade.split(",") if tok.strip()}
        for nivel in niveis:
            if nivel in self._checks:
                self._checks[nivel].setChecked(True)

        # cursos "qual?" (só têm efeito visível se o nível estiver marcado)
        for nivel, field in _CURSO_FIELD.items():
            valor = perfil.get(field)
            if valor and nivel in self._cursos:
                self._cursos[nivel].setText(valor)
                self._cursos[nivel].setEnabled(self._checks[nivel].isChecked())

        self._formacao_futura.setText(perfil.get("formacao_futura") or "")
        self._data_formacao_futura.setText(
            _iso_to_mmaaaa(perfil.get("data_formacao_futura"))
        )
        self._cep.setText(perfil.get("cep") or "")
        self._cidade.setText(perfil.get("cidade") or "")

        uf = perfil.get("uf")
        if uf in _UFS:
            self._uf.setCurrentIndex(_UFS.index(uf))

        mob = perfil.get("mobilidade")
        for i, (_rot, valor) in enumerate(_MOBILIDADE):
            if valor == mob:
                self._mobilidade.setCurrentIndex(i)
                break

        self._areas.setText(perfil.get("areas_interesse") or "")
        curriculo_texto = perfil.get("curriculo") or ""
        self._curriculo.setPlainText(curriculo_texto)
        # Já tem currículo salvo -> começa no estado "anexado" (ações compactas).
        self._set_curriculo_anexado(bool(curriculo_texto))

    # --- CEP (autopreenchimento) --------------------------------------

    def _on_buscar_cep(self) -> None:
        """Consulta o CEP no backend (off-thread) e preenche cidade/UF. Guarda
        contra chamadas duplas (editingFinished + clique) via botão desabilitado."""
        if not self._cep_button.isEnabled():
            return
        cep = "".join(c for c in self._cep.text() if c.isdigit())
        if len(cep) != 8:
            if cep:
                self._cep_status.setText("Informe um CEP com 8 dígitos.")
            return
        self._cep_status.setText("Buscando CEP...")
        self._cep_button.setEnabled(False)
        run_in_background(
            lambda: api_client.lookup_cep(cep),
            self._on_cep_ok,
            self._on_cep_err,
        )

    def _on_cep_ok(self, data: dict) -> None:
        self._cep_button.setEnabled(True)
        cidade = data.get("cidade")
        uf = data.get("uf")
        if cidade:
            self._cidade.setText(cidade)
        if uf in _UFS:
            self._uf.setCurrentIndex(_UFS.index(uf))
        self._cep_status.setText("")  # sucesso é silencioso (cidade/UF já preenchem)

    def _on_cep_err(self, exc: Exception) -> None:
        self._cep_button.setEnabled(True)
        self._cep_status.setText(
            getattr(exc, "detail", "Não foi possível consultar o CEP.")
        )

    # --- Currículo (anexar / visualizar / alterar / excluir) ----------

    def _set_curriculo_anexado(self, anexado: bool) -> None:
        """Estado A (sem anexo): botão "Anexar" + campo de texto visível para
        colar/escrever. Estado B (anexado): as três ações (Visualizar/Alterar/
        Excluir), com o texto oculto — "Visualizar" mostra."""
        self._curriculo_anexado = anexado
        self._anexar_button.setVisible(not anexado)
        self._curriculo_actions.setVisible(anexado)
        self._curriculo.setVisible(not anexado)

    def _on_anexar_curriculo(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Escolha seu currículo", "", "Currículo (*.pdf *.txt)"
        )
        if not caminho:
            return
        try:
            texto = curriculo.extrair_texto(caminho)
        except curriculo.CurriculoError as exc:
            InfoBar.error(
                title="",
                content=str(exc),
                duration=5000,
                position=InfoBarPosition.TOP,
                parent=self,
            )
            return
        self._curriculo_path = caminho
        self._curriculo.setPlainText(texto)
        self._set_curriculo_anexado(True)

    def _on_ver_curriculo(self) -> None:
        # Se há um arquivo anexado nesta sessão, abre o PDF/arquivo COMO ELE É
        # no visualizador padrão do sistema. Sem arquivo (texto colado ou perfil
        # salvo), cai no fallback de mostrar/ocultar o texto extraído.
        if self._curriculo_path and Path(self._curriculo_path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._curriculo_path))
        else:
            self._curriculo.setVisible(not self._curriculo.isVisible())

    def _on_excluir_curriculo(self) -> None:
        self._curriculo_path = None
        self._curriculo.clear()
        self._set_curriculo_anexado(False)

    def validate(self) -> bool:
        """Hook do MessageBoxBase: o Salvar só fecha o diálogo se retornar
        True. Barra a data de formação em formato inválido com erro leigo."""
        try:
            _mmaaaa_to_iso(self._data_formacao_futura.text())
        except ValueError as exc:
            InfoBar.error(
                title="",
                content=str(exc),
                duration=5000,
                position=InfoBarPosition.TOP,
                parent=self,
            )
            return False
        return True

    def coletar(self) -> dict:
        """Monta o dict de campos para o PUT /profile. Campos em branco viram
        None; escolaridade é o csv dos níveis marcados."""
        niveis_marcados = [n for n, _r in _NIVEIS if self._checks[n].isChecked()]

        cursos = {"tecnico": None, "graduacao": None, "pos_graduacao": None}
        for nivel, field in _CURSO_FIELD.items():
            if self._checks[nivel].isChecked():
                cursos[field] = _none_if_blank(self._cursos[nivel].text())

        uf_idx = self._uf.currentIndex()
        uf = _UFS[uf_idx] if uf_idx >= 0 else None

        try:
            data_formacao = _mmaaaa_to_iso(self._data_formacao_futura.text())
        except ValueError:
            # validate() barra o salvar antes; aqui é só rede de segurança.
            data_formacao = None

        return {
            "graduacao": cursos["graduacao"],
            "tecnico": cursos["tecnico"],
            "pos_graduacao": cursos["pos_graduacao"],
            "escolaridade": ",".join(niveis_marcados) or None,
            "formacao_futura": _none_if_blank(self._formacao_futura.text()),
            "data_formacao_futura": data_formacao,
            "cep": _none_if_blank(self._cep.text()),
            "uf": uf,
            "cidade": _none_if_blank(self._cidade.text()),
            "mobilidade": _MOBILIDADE[self._mobilidade.currentIndex()][1],
            "areas_interesse": _none_if_blank(self._areas.text()),
            "curriculo": _none_if_blank(self._curriculo.toPlainText()),
        }
