"""Reusable search-result card widget (D-03/D-04, ENTREGA-02).

`ConcursoCard` is purely presentational: it renders one concurso's title,
cargos, prazo de inscrição and link, and highlights `is_new` results with
the "NOVO" badge + `CardNew.TFrame` background (D-04). It never recomputes
`is_new` itself — that flag arrives pre-computed from the backend.

Field access uses the verified nested-dict shape (03-RESEARCH.md Pitfall 3):
`concurso["titulo"]`, `concurso.get("cargos", [])`, `concurso.get("datas",
{}).get("fim", ...)`, `concurso.get("noticia", {}).get("link", ...)` — never
flat `concurso["prazo"]`/`concurso["link"]`.

ENTREGA-02: when `noticia.link` is non-empty, a "Copiar link" button copies
the URL to the Windows clipboard and shows "Copiado!" feedback for 1.5s via
`root.after()`. Cards with no link omit the button entirely.
"""

from __future__ import annotations

from tkinter import ttk

from app.ui import styles


class ConcursoCard(ttk.Frame):
    def __init__(self, parent, concurso: dict):
        is_new = bool(concurso.get("is_new"))
        style_name = "CardNew.TFrame" if is_new else "Card.TFrame"
        background = styles.COLOR_NEW_BG if is_new else styles.COLOR_SECONDARY
        super().__init__(parent, style=style_name, padding=10)

        if is_new:
            ttk.Label(self, text="NOVO", style="Badge.TLabel").pack(anchor="ne")

        ttk.Label(
            self,
            text=concurso["titulo"],
            font=styles.FONT_HEADING,
            background=background,
            wraplength=500,
        ).pack(anchor="w", pady=(0, 8))

        cargos_line = "Cargo(s): " + ", ".join(concurso.get("cargos", []))
        ttk.Label(
            self,
            text=cargos_line,
            font=styles.FONT_BODY,
            background=background,
            wraplength=500,
        ).pack(anchor="w", pady=(0, 8))

        prazo = concurso.get("datas", {}).get("fim", "não informado")
        ttk.Label(
            self,
            text=f"Inscrições até: {prazo}",
            font=styles.FONT_BODY,
            background=background,
            wraplength=500,
        ).pack(anchor="w", pady=(0, 8))

        link = concurso.get("noticia", {}).get("link", "")

        link_frame = ttk.Frame(self, style=style_name)
        link_frame.pack(anchor="w", fill="x")

        ttk.Label(
            link_frame,
            text=link or "link não disponível",
            font=styles.FONT_BODY,
            background=background,
            foreground="blue" if link else None,
            wraplength=460,
        ).pack(side="left", anchor="w")

        if link:
            self._link = link
            self._feedback_label = ttk.Label(
                link_frame,
                text="",
                font=styles.FONT_SMALL,
                background=background,
            )
            self._feedback_label.pack(side="left", padx=(8, 0))

            def _copiar_link(lbl=self._feedback_label, url=link) -> None:
                root = lbl.winfo_toplevel()
                root.clipboard_clear()
                root.clipboard_append(url)
                lbl.config(text="Copiado!")
                root.after(1500, lambda: lbl.config(text=""))

            self._copiar_link = _copiar_link

            ttk.Button(
                link_frame,
                text="Copiar link",
                command=self._copiar_link,
            ).pack(side="left", padx=(8, 0))
