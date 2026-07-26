"""Post-login screen: `Pivot` + `QStackedWidget` with Busca always + Admin
conditionally (PySide6/qfluentwidgets rewrite of `main_frame.py`, D-02).

`visible_tab_labels(session)` is a pure, Qt-free helper isolating the
tab-visibility decision (["Busca"] + ["Admin"] iff `session.is_admin`) so it
can be unit-tested without a `QApplication`.

`MainWindow(session, on_logout, on_toggle_theme)` builds the container: a
header row (right-aligned) with a theme-toggle `TransparentToolButton` and
a "Sair" `PushButton` (wired to the injected `on_logout` callback, per
05-UI-SPEC.md's Copywriting Contract — no confirmation dialog), plus a
`Pivot` + `QStackedWidget` with `BuscaTab` added unconditionally and
`AdminTab` added only inside an `if session.is_admin` branch — never
toggled at runtime via `.hide()`/`.show()`, since `is_admin` is immutable
within a session (same rule as the Tkinter analog).

Admin-tab visibility here is UX only (T-05-ADMINGATE) — the backend's
`require_admin` dependency remains the actual authorization boundary.
"""

from __future__ import annotations

import json

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    Pivot,
    PrimaryPushButton,
    PushButton,
    TitleLabel,
    TransparentToolButton,
)

from app import api_client
from app.async_helpers import run_in_background
from app.config import APP_DIR
from app.ui import styles
from app.ui.admin_tab import AdminTab
from app.ui.busca_tab import BuscaTab
from app.ui.perfil_dialog import PerfilDialog
from app.updater import check_for_update

_BUSCA_ROUTE = "Busca"
_ADMIN_ROUTE = "Admin"

# Popup de anúncio do app web (v1.5.2) — mostrado uma vez por instalação,
# gated pela flag persistida em APP_DIR/web_promo.json (T-sp8-01).
_WEB_PROMO_FLAG_NAME = "web_promo.json"
_WEB_PROMO_URL = "https://jonasaaugusto.github.io/IAprovale/"
_WEB_PROMO_TITLE = "IAprovale na web!"
_WEB_PROMO_TEXT = (
    "Agora você pode acessar o IAprovale direto do navegador, sem instalar "
    "nada. Quer experimentar?"
)


class _WebPromoOverlay(QWidget):
    """Overlay embutido (filho de `MainWindow`) para o popup de anúncio da
    versão web (v1.5.2/260724-so6).

    Deliberadamente um `QWidget` filho em coordenadas locais — NUNCA um
    `QDialog`/janela top-level. Os fixes anteriores 260724-m4k
    (`box.move(self.window().pos())`) e 260724-mo5
    (`QTimer.singleShot(0, ...)`) tentaram sincronizar um
    `qfluentwidgets.MessageBox` (que herda de `MaskDialogBase`, sempre uma
    janela top-level `FramelessWindowHint` do SO) contra a janela pai usando
    coordenadas ABSOLUTAS de tela — e produziram geometria matematicamente
    correta em repro offscreen, mas o popup continuou renderizando pequeno,
    deslocado e cortado na máquina real do usuário (DPI scaling, timing do
    window manager, multi-monitor). Um widget filho com
    `setGeometry(parent.rect())` elimina essa classe inteira de bug: nunca
    depende de coordenadas de tela nem do SO, só do próprio layout do pai.
    """

    def __init__(self, parent: QWidget, on_close) -> None:
        super().__init__(parent)
        self._on_close = on_close

        self.setObjectName("WebPromoOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # Regra escopada por seletor de ID (#WebPromoOverlay), NUNCA
        # declaração nua: uma regra não-escopada cascateia pra todo
        # descendente QWidget-puro e produz a regressão "caixas dentro de
        # caixas" documentada em styles.py::ROOT_WINDOW_OBJECT_NAME. Cor de
        # scrim deliberadamente independente de tema (isDarkTheme() NÃO é
        # consultado): um véu preto translúcido funciona nos dois temas, o
        # overlay não precisa participar de refresh_theme().
        self.setStyleSheet(
            "#WebPromoOverlay { background-color: rgba(0, 0, 0, 0.45); }"
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = CardWidget(self)
        card.setMaximumWidth(420)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(
            styles.SPACING_XL,
            styles.SPACING_XL,
            styles.SPACING_XL,
            styles.SPACING_XL,
        )

        self.title_label = TitleLabel(_WEB_PROMO_TITLE, card)
        card_layout.addWidget(self.title_label)
        card_layout.addSpacing(styles.SPACING_MD)

        self.body_label = BodyLabel(_WEB_PROMO_TEXT, card)
        self.body_label.setWordWrap(True)
        card_layout.addWidget(self.body_label)
        card_layout.addSpacing(styles.SPACING_LG)

        buttons = QHBoxLayout()
        buttons.setSpacing(styles.SPACING_SM)
        buttons.addStretch(1)
        self.depois_button = PushButton("Prefiro continuar aqui", card)
        self.sim_button = PrimaryPushButton("Sim", card)
        buttons.addWidget(self.depois_button)
        buttons.addWidget(self.sim_button)
        card_layout.addLayout(buttons)

        outer.addWidget(card)

        self.sim_button.clicked.connect(lambda: self._on_close(True))
        self.depois_button.clicked.connect(lambda: self._on_close(False))

        # Esc == recusar, sem abrir URL — preserva o comportamento do
        # MessageBox anterior (QDialog fecha com reject() no Esc).
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def mousePressEvent(self, event) -> None:
        """Bloqueia cliques de vazarem pro conteúdo das abas por baixo
        (T-so6-03) — o overlay cobre `MainWindow.rect()` inteiro e fica no
        topo do z-order (`raise_()`), mas sem isso um QWidget puro deixaria
        o clique atravessar pra widgets sobrepostos."""
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._on_close(False)
            return
        super().keyPressEvent(event)


def visible_tab_labels(session) -> list[str]:
    """Return the tab labels that should be visible for `session`.

    Pure function, no QApplication required — isolates the tab-visibility
    decision for a Qt-free unit test.
    """
    labels = ["Busca"]
    if session.is_admin:
        labels.append("Admin")
    return labels


class MainWindow(QWidget):
    """Post-login container: header (theme toggle + Sair) + Pivot tabs."""

    def __init__(self, session, on_logout, on_toggle_theme, parent=None) -> None:
        super().__init__(parent)
        self._session = session
        # Inicializado ANTES de qualquer construção de filho: resizeEvent/
        # showEvent podem disparar durante o build do layout abaixo e
        # consultam este atributo via _sync_web_overlay_geometry.
        self._web_overlay: _WebPromoOverlay | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(
            styles.SPACING_MD, styles.SPACING_SM, styles.SPACING_MD, styles.SPACING_SM
        )
        header.setSpacing(styles.SPACING_SM)
        header.addStretch(1)

        self._theme_button = TransparentToolButton(FIF.CONSTRACT, self)
        self._theme_button.setToolTip("Alternar tema claro/escuro")
        self._theme_button.clicked.connect(on_toggle_theme)
        header.addWidget(self._theme_button)

        # "Perfil" — disponível para QUALQUER usuário logado (não admin-only).
        self._perfil_button = PushButton("Perfil", self)
        self._perfil_button.clicked.connect(self._on_perfil_click)
        header.addWidget(self._perfil_button)

        self._sair_button = PushButton("Sair", self)
        self._sair_button.clicked.connect(on_logout)
        header.addWidget(self._sair_button)

        layout.addLayout(header)

        self._pivot = Pivot(self)
        self._stack = QStackedWidget(self)

        self._busca_tab = BuscaTab(session, self._stack)
        self._stack.addWidget(self._busca_tab)
        self._pivot.addItem(
            routeKey=_BUSCA_ROUTE,
            text=_BUSCA_ROUTE,
            onClick=lambda: self._stack.setCurrentWidget(self._busca_tab),
        )

        # Admin tab decided ONCE here, at build time — session.is_admin is
        # immutable for the lifetime of a session, never re-checked/toggled.
        self._admin_tab: AdminTab | None = None
        if session.is_admin:
            self._admin_tab = AdminTab(session, self._stack)
            self._stack.addWidget(self._admin_tab)
            self._pivot.addItem(
                routeKey=_ADMIN_ROUTE,
                text=_ADMIN_ROUTE,
                onClick=lambda: self._stack.setCurrentWidget(self._admin_tab),
            )

        layout.addWidget(self._pivot)
        layout.addWidget(self._stack, 1)

        self._pivot.setCurrentItem(_BUSCA_ROUTE)

        # Auto-update Nível 1 (U-3): check off-thread, never block/delay the
        # window; a failed/absent-update check is deliberately silent.
        run_in_background(check_for_update, self._on_update_check, lambda _exc: None)

        # Popup de anúncio do app web (v1.5.2) — depois do update-check pra
        # não competir com a InfoBar dele; só na primeira construção. Chamada
        # direta (não mais adiada via QTimer): o overlay embutido usa
        # self.rect() em coordenadas locais, e a corretude da geometria vem
        # de resizeEvent/showEvent — não do instante da construção — então
        # o deferral do fix 260724-mo5 deixou de ser necessário.
        self._mostrar_popup_web()

    # --- Popup do app web (uma vez por instalação, v1.5.2) --------------

    def _mostrar_popup_web(self) -> None:
        """Mostra o popup de anúncio da versão web, gated pela flag
        persistida em `APP_DIR/web_promo.json`. Fatorado num método próprio
        (padrão `_mostrar_popup_pdf_gerado` do busca_tab) para que os testes
        possam monkeypatchá-lo. O popup em si é um `_WebPromoOverlay`
        (widget filho embutido, ver docstring da classe) construído
        sincronamente aqui — nada de `.exec()` bloqueante como no antigo
        `MessageBox`. IO da flag é tolerante a falha (T-sp8-01): erro de
        leitura trata como "não mostrado ainda"; erro de escrita é
        silencioso — nunca crasha o app. Escrita da flag acontece só na
        dispensa (`_on_popup_web_close`), espelhando o comportamento
        anterior em que a flag só era gravada depois do usuário fechar o
        diálogo bloqueante."""
        if self._web_overlay is not None:
            return

        flag_path = APP_DIR / _WEB_PROMO_FLAG_NAME

        try:
            ja_mostrado = json.loads(flag_path.read_text(encoding="utf-8")).get("shown", False)
        except Exception:
            ja_mostrado = False
        if ja_mostrado:
            return

        self._web_overlay = _WebPromoOverlay(self, self._on_popup_web_close)
        self._sync_web_overlay_geometry()
        self._web_overlay.raise_()
        self._web_overlay.show()
        self._web_overlay.setFocus()

    def _on_popup_web_close(self, abrir_web: bool) -> None:
        """Dispensa o popup web (clique em qualquer botão, ou Esc). Se
        `abrir_web`, abre `_WEB_PROMO_URL` via QDesktopServices antes de
        persistir a flag (mesmo bloco tolerante a falha de sempre, T-sp8-01).
        `self._web_overlay` é zerado ANTES de qualquer retorno — permite
        aos testes assertar `is None` sem depender do event loop processar
        o `deleteLater`."""
        overlay = self._web_overlay
        if overlay is None:
            return

        if abrir_web:
            QDesktopServices.openUrl(QUrl(_WEB_PROMO_URL))

        flag_path = APP_DIR / _WEB_PROMO_FLAG_NAME
        try:
            flag_path.parent.mkdir(parents=True, exist_ok=True)
            flag_path.write_text(json.dumps({"shown": True}), encoding="utf-8")
        except Exception:
            pass

        overlay.hide()
        overlay.deleteLater()
        self._web_overlay = None

    def _sync_web_overlay_geometry(self) -> None:
        """Ressincroniza a geometria do overlay com `self.rect()` (mesma
        coordenada local sempre, nunca absoluta de tela). Chamado na
        criação, em `resizeEvent` e em `showEvent`."""
        if self._web_overlay is not None:
            self._web_overlay.setGeometry(self.rect())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_web_overlay_geometry()

    def showEvent(self, event) -> None:
        # MainWindow é adicionada a um QStackedWidget já visível em
        # main.py::_RootWindow._swap(), o que dispara resize + show depois
        # do __init__ — é aí que a geometria real (≈900x650) chega. Sem
        # showEvent, uma MainWindow reaproveitada (troca de tema não a
        # reconstrói) que ainda não tinha overlay quando o show original
        # ocorreu não teria chance de ressincronizar depois.
        super().showEvent(event)
        self._sync_web_overlay_geometry()

    # --- Auto-update (Nível 1: check + notify, never self-replace) ------

    def _on_update_check(self, info: dict | None) -> None:
        if not info:
            return
        bar = InfoBar.success(
            title=f"Nova versão disponível (v{info['version']})",
            content="",
            duration=-1,
            position=InfoBarPosition.TOP,
            parent=self,
        )
        button = PushButton("Baixar", self)
        button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(info["url"])))
        bar.addWidget(button)

    # --- Perfil (botão no header) ---------------------------------------

    def _on_perfil_click(self) -> None:
        """Busca o perfil atual (off-thread) e então abre o diálogo. Desabilita
        o botão enquanto carrega para evitar diálogos duplicados."""
        self._perfil_button.setEnabled(False)
        run_in_background(
            lambda: api_client.get_profile(),
            self._open_perfil_dialog,
            self._on_perfil_error,
        )

    def _open_perfil_dialog(self, perfil: dict) -> None:
        self._perfil_button.setEnabled(True)
        dialog = PerfilDialog(perfil, parent=self.window())
        if not dialog.exec():
            return
        campos = dialog.coletar()
        run_in_background(
            lambda: api_client.update_profile(campos),
            self._on_perfil_saved,
            self._on_perfil_error,
        )

    def _on_perfil_saved(self, _perfil: dict) -> None:
        InfoBar.success(
            title="",
            content="Perfil salvo.",
            duration=3000,
            position=InfoBarPosition.TOP,
            parent=self,
        )

    def _on_perfil_error(self, exc: Exception) -> None:
        self._perfil_button.setEnabled(True)
        InfoBar.error(
            title="",
            content=getattr(exc, "detail", str(exc)),
            duration=-1,
            position=InfoBarPosition.TOP,
            parent=self,
        )

    def refresh_theme(self) -> None:
        """Re-style child widgets that don't auto-update via qfluentwidgets'
        `setTheme()` after a live theme toggle (modo-noturno-bugado).

        Called by `main.py::_RootWindow._toggle_theme()` on the EXISTING
        `MainWindow` instance, instead of the old approach of discarding
        it and building a fresh one — that used to also discard in-memory
        search state (query text, rendered results) on every toggle.
        Registered qfluentwidgets components (`PushButton`, `CardWidget`,
        `Pivot`, `SearchLineEdit`, etc.) already re-style themselves
        reactively via the library's own theme-change mechanism and need
        no help here; only the few widgets with manually-built,
        construction-time QSS do.
        """
        self._busca_tab.refresh_theme()
        if self._admin_tab is not None:
            self._admin_tab.refresh_theme()
