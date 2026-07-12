"""Search screen: query box + Buscar button + progress indicator + results (BUSCA-06/D-02/D-03/D-04).

`BuscaTab` is the primary user-facing screen: it lets the user type a free-text
description of what they're looking for, dispatches `api_client.search()`
off the main thread via `async_helpers.run_in_background` (Pitfall 1 — a
direct call inside the button's `command=` handler would freeze the UI for
the full 30-90s round-trip), and renders one `ConcursoCard` per result into
a hand-built scrollable list (Canvas + Scrollbar + inner Frame — 03-UI-SPEC.md
Window & Layout, no third-party scrollable-frame package).

Click-handling is factored into `_start_search()` so tests can call it
directly (no real Tk mainloop needed) and assert the button/progress/label
state flips synchronously, BEFORE `run_in_background` (referenced as a
module-level name, monkeypatchable) actually dispatches anything.

Error handling follows 03-UI-SPEC.md's Error Display Contract: failures are
shown in an inline `Banner.TLabel` placed directly below the query `Entry`
(never a modal dialog), displaying the backend's `exc.detail` string
verbatim (Pitfall 4) — never a generic/rephrased message. Empty results
show the backend's `message` verbatim, falling back to the UI-SPEC copy
only when `message` is `None`.

The query is sent as raw free text with zero client-side validation/cleaning
(V5, T-03-INJECT) — the backend's fixed tool-allowlist + schema validation
is the actual prompt-injection boundary; client-side pre-filtering could
weaken it.

PDF export (ENTREGA-01): `_btn_gerar_pdf` is enabled after a successful
non-empty search.  `_gerar_pdf()` calls `pdf_export.gerar_pdf()` and writes
the bytes to `APP_DIR/resultados.pdf`.  All PDF-related imports (`os`,
`shutil`, `tkinter.filedialog`, `app.pdf_export`, `app.config`) are lazy
imports inside the methods that use them — reduces surface area for
ImportError in the frozen `.exe` and keeps startup fast.
"""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk

from app import api_client
from app.async_helpers import run_in_background
from app.ui import styles
from app.ui.concurso_card import ConcursoCard

_QUERY_PLACEHOLDER = "Ex: concurso de saúde com graduação em enfermagem"
_PLACEHOLDER_FG = "#6c757d"


class BuscaTab(ttk.Frame):
    LOADING_TEXT = "Buscando concursos... isso pode levar até 90s"
    EMPTY_FALLBACK = (
        "Nenhum concurso encontrado com esses critérios. "
        "Tente ajustar sua busca ou sua formação salva."
    )

    def __init__(self, parent, session):
        super().__init__(parent, style="Root.TFrame", padding=24)
        self._session = session

        # PDF state — tracked here so all _*_pdf methods share state cleanly
        self._pdf_path: Path | None = None
        self._resultados: list[dict] = []
        self._query_str: str = ""

        query_row = ttk.Frame(self, style="Root.TFrame")
        query_row.pack(fill="x")

        ttk.Label(
            query_row, text="🔍", background=styles.COLOR_DOMINANT
        ).pack(side="left", padx=(0, 6))

        self._query_entry = ttk.Entry(query_row)
        self._query_entry.pack(side="left", fill="x", expand=True)
        self._query_entry.bind("<Return>", self._start_search)
        self._query_entry.bind("<FocusIn>", self._on_query_focus_in)
        self._query_entry.bind("<FocusOut>", self._on_query_focus_out)
        self._query_entry.insert(0, _QUERY_PLACEHOLDER)
        self._query_entry.config(foreground=_PLACEHOLDER_FG)

        self._buscar_button = ttk.Button(
            query_row,
            text="Buscar",
            style="Accent.TButton",
            command=self._start_search,
        )
        self._buscar_button.pack(side="left", padx=(8, 0))

        self._btn_gerar_pdf = ttk.Button(
            query_row,
            text="Gerar PDF",
            command=self._gerar_pdf,
            state="disabled",
        )
        self._btn_gerar_pdf.pack(side="left", padx=(8, 0))

        self._help_button = ttk.Button(
            query_row, text="?", width=3, command=self._mostrar_ajuda
        )
        self._help_button.pack(side="right")

        # Always-packed anchor: everything conditionally shown below the
        # query row (banner / progress / status / pdf_row) is packed with
        # `before=self._anchor` so it stays directly under the query Entry
        # regardless of pack/pack_forget cycles (pack_forget followed by a
        # bare pack() re-appends at the END of the packing list otherwise).
        self._anchor = ttk.Frame(self, height=0, style="Root.TFrame")
        self._anchor.pack(fill="x")

        # PDF action row — hidden until first PDF is generated
        self._pdf_row = ttk.Frame(self, style="Root.TFrame")
        # Not packed yet; shown via pack() inside _gerar_pdf()

        self._btn_visualizar = ttk.Button(
            self._pdf_row, text="Visualizar", command=self._visualizar_pdf
        )
        self._btn_visualizar.pack(side="left", padx=(0, 8))

        self._btn_salvar = ttk.Button(
            self._pdf_row, text="Salvar", command=self._salvar_pdf
        )
        self._btn_salvar.pack(side="left", padx=(0, 8))

        self._btn_apagar = ttk.Button(
            self._pdf_row, text="Apagar", command=self._apagar_pdf
        )
        self._btn_apagar.pack(side="left", padx=(0, 8))

        self._banner = ttk.Label(self, text="", style="Banner.TLabel", wraplength=800)
        # Hidden until an error occurs (Error Display Contract: directly
        # below the query Entry).

        self._progress = ttk.Progressbar(
            self,
            mode="indeterminate",
            style="Accent.Horizontal.TProgressbar",
            length=280,
        )
        # Hidden until a search is in flight.

        self._status_label = ttk.Label(self, text="", background=styles.COLOR_DOMINANT)
        self._status_label.pack(anchor="w", pady=(16, 0), before=self._anchor)

        results_container = ttk.Frame(self, style="Root.TFrame")
        results_container.pack(fill="both", expand=True, pady=(24, 0))

        self._canvas = tk.Canvas(
            results_container, background=styles.COLOR_DOMINANT, highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(
            results_container, orient="vertical", command=self._canvas.yview
        )
        self._results_frame = ttk.Frame(self._canvas, style="Root.TFrame")

        self._results_frame.bind(
            "<Configure>",
            lambda _e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._canvas.create_window((0, 0), window=self._results_frame, anchor="nw")
        self._canvas.configure(yscrollcommand=scrollbar.set)

        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._canvas.bind(
            "<Enter>",
            lambda _e: self._canvas.bind_all("<MouseWheel>", self._on_mousewheel),
        )
        self._canvas.bind("<Leave>", lambda _e: self._canvas.unbind_all("<MouseWheel>"))

    def _on_mousewheel(self, event) -> None:
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_query_focus_in(self, _event=None) -> None:
        if self._query_entry.get() == _QUERY_PLACEHOLDER:
            self._query_entry.delete(0, "end")
            self._query_entry.config(foreground=styles.COLOR_TEXT)

    def _on_query_focus_out(self, _event=None) -> None:
        if not self._query_entry.get():
            self._query_entry.insert(0, _QUERY_PLACEHOLDER)
            self._query_entry.config(foreground=_PLACEHOLDER_FG)

    def _start_search(self, _event=None) -> None:
        query = self._query_entry.get()
        if query == _QUERY_PLACEHOLDER:
            query = ""

        self._clear_banner()
        self._clear_cards()
        self._status_label.config(text="")

        self._buscar_button.config(state="disabled")
        self._progress.pack(pady=(16, 0), before=self._anchor)
        self._progress.start(10)
        self._status_label.config(text=self.LOADING_TEXT)
        self._status_label.pack(anchor="w", pady=(8, 0), before=self._anchor)

        run_in_background(
            self.winfo_toplevel(),
            lambda: api_client.search(query),
            self._on_success,
            self._on_error,
        )

    def _on_success(self, response: dict) -> None:
        self._stop_progress()
        self._buscar_button.config(state="normal")
        self._clear_cards()

        self._resultados = response.get("results", [])
        self._query_str = self._query_entry.get()

        # Enable/disable Gerar PDF based on whether there are results
        if self._resultados:
            self._btn_gerar_pdf.config(state="normal")
        else:
            self._btn_gerar_pdf.config(state="disabled")

        for concurso in self._resultados:
            ConcursoCard(self._results_frame, concurso).pack(fill="x", pady=(0, 8))

        if response.get("is_empty"):
            message = response.get("message")
            self._status_label.config(
                text=message if message is not None else self.EMPTY_FALLBACK
            )
            self._status_label.pack(anchor="w", pady=(8, 0), before=self._anchor)
        else:
            self._status_label.config(text="")
            self._status_label.pack_forget()

    def _on_error(self, exc: Exception) -> None:
        self._stop_progress()
        self._buscar_button.config(state="normal")
        self._status_label.config(text="")
        self._status_label.pack_forget()
        self._show_banner(getattr(exc, "detail", str(exc)))

    def _stop_progress(self) -> None:
        self._progress.stop()
        self._progress.pack_forget()

    def _clear_cards(self) -> None:
        for child in self._results_frame.winfo_children():
            child.destroy()

    def _show_banner(self, text: str) -> None:
        self._banner.config(text=text)
        self._banner.pack(fill="x", pady=(8, 0), before=self._anchor)

    def _clear_banner(self) -> None:
        self._banner.config(text="")
        self._banner.pack_forget()

    # ------------------------------------------------------------------
    # Tutorial modal — "?" button next to the query row
    # ------------------------------------------------------------------

    def _mostrar_ajuda(self) -> None:
        """Abre um modal read-only explicando como formular buscas.

        Reusa o idioma de Toplevel centrado já estabelecido em
        admin_tab.py's `_reveal_password`/`_on_rename_click`.
        """
        toplevel = tk.Toplevel(self)
        toplevel.title("Como pesquisar")
        toplevel.resizable(False, False)
        toplevel.transient(self.winfo_toplevel())

        container = ttk.Frame(toplevel, style="Root.TFrame", padding=16)
        container.pack(fill="both", expand=True)

        text_widget = tk.Text(
            container,
            wrap="word",
            height=22,
            width=58,
            fg=styles.COLOR_TEXT,
            bg=styles.COLOR_SECONDARY,
            font=styles.FONT_BODY,
            relief="flat",
            borderwidth=0,
        )
        text_widget.pack(fill="both", expand=True)
        text_widget.tag_configure("heading", font=styles.FONT_HEADING)

        sections: list[tuple[str | None, str]] = [
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

        for index, (heading, body) in enumerate(sections):
            if index > 0:
                text_widget.insert("end", "\n\n")
            if heading is not None:
                text_widget.insert("end", heading, "heading")
                text_widget.insert("end", "\n")
            text_widget.insert("end", body)

        text_widget.config(state="disabled")

        ttk.Button(container, text="Fechar", command=toplevel.destroy).pack(
            pady=(12, 0)
        )

        toplevel.update_idletasks()
        parent = self.winfo_toplevel()
        width = toplevel.winfo_reqwidth()
        height = toplevel.winfo_reqheight()
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        toplevel.geometry(f"+{x}+{y}")

        toplevel.grab_set()

    # ------------------------------------------------------------------
    # PDF export — ENTREGA-01
    # All imports below are lazy (inside each method) to reduce frozen
    # .exe ImportError surface and keep startup time minimal.
    # ------------------------------------------------------------------

    def _gerar_pdf(self) -> None:
        """Gera o PDF com os resultados atuais e o salva em APP_DIR."""
        from app.pdf_export import gerar_pdf
        from app.config import APP_DIR

        pdf_bytes = gerar_pdf(self._resultados, self._query_str)
        APP_DIR.mkdir(parents=True, exist_ok=True)
        pdf_path = APP_DIR / "resultados.pdf"
        pdf_path.write_bytes(pdf_bytes)
        self._pdf_path = pdf_path

        # Show the pdf_row (Visualizar / Salvar / Apagar) below query row
        self._pdf_row.pack(fill="x", pady=(8, 0), before=self._anchor)

    def _visualizar_pdf(self) -> None:
        """Abre o PDF gerado no visualizador padrão do Windows."""
        import os

        if self._pdf_path and self._pdf_path.exists():
            os.startfile(str(self._pdf_path))

    def _salvar_pdf(self) -> None:
        """Abre file dialog para o usuário escolher onde salvar uma cópia."""
        if not self._pdf_path or not self._pdf_path.exists():
            return
        from tkinter import filedialog
        import shutil

        dest = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Arquivo PDF", "*.pdf")],
            initialfile="concursos.pdf",
            title="Salvar resultados como...",
        )
        if dest:
            shutil.copy2(self._pdf_path, dest)

    def _apagar_pdf(self) -> None:
        """Remove o arquivo PDF temporário e esconde o pdf_row."""
        if self._pdf_path:
            self._pdf_path.unlink(missing_ok=True)
            self._pdf_path = None
        self._pdf_row.pack_forget()
