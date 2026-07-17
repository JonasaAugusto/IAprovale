"""PDF export module for Concurso Finder — ENTREGA-01.

`gerar_pdf` is a pure function: it receives a list of concurso dicts and
an optional query string, builds a formatted PDF using fpdf2, and returns
the raw bytes.  No filesystem writes happen here — the caller (BuscaTab)
is responsible for persisting the bytes to APP_DIR/resultados.pdf.

Encoding: `set_doc_option("core_fonts_encoding", "windows-1252")` with
Helvetica (a PDF core font, zero TTF bundle) covers all PT-BR characters
(áéíóúâêîôûãõàç and common separators like em-dash U+2014).  No
output_intent / PDF/A mode is used — that would require bundling an ICC
profile file which is unnecessary for this app.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fpdf import FPDF

# Accent color (matches desktop/app/ui/styles.ACCENT = "#0078D4").
_ACCENT_RGB = (0, 120, 212)

_ASSETS_DIR = Path(__file__).parent / "assets"
_LOGO_PATH = _ASSETS_DIR / "logo.png"


def _ordenar_novos_primeiro(resultados: list[dict]) -> list[dict]:
    """Retorna resultados reordenados com is_new=True primeiro, preservando
    a ordem relativa dentro de cada grupo (sort estável)."""
    return sorted(resultados, key=lambda c: not c.get("is_new"))


def _fmt_localizacao(concurso: dict) -> str:
    """UF + região do concurso -> "MG · Sudeste" (ou só o que existir). Vazio
    se o MCP não trouxer nenhum dos dois. Espelha
    app/ui/concurso_card.py::_fmt_localizacao para manter PDF e card
    consistentes (não alterar concurso_card.py — apenas espelhar aqui)."""
    uf = (concurso.get("uf") or "").strip().upper()
    regiao = (concurso.get("regiao") or "").strip().title()
    if uf and regiao:
        return f"{uf} · {regiao}"
    return uf or regiao or ""


def gerar_pdf(
    resultados: list[dict], query: str = "", extracted_summary: str | None = None
) -> bytes:
    """Gera PDF dos resultados de busca. Retorna bytes prontos para gravar em arquivo.

    Args:
        resultados:        Lista de dicts de concurso no formato do backend.
        query:              String de busca original do usuário (aparece no cabeçalho).
        extracted_summary: O que a IA entendeu da busca (opcional, aparece no cabeçalho).

    Returns:
        Bytes do PDF gerado (começa com b"%PDF").
    """
    pdf = FPDF()
    # set_doc_option("core_fonts_encoding") was deprecated in fpdf2 2.4.0;
    # use the property directly instead (avoids DeprecationWarning).
    pdf.core_fonts_encoding = "windows-1252"
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    # Barra de destaque (cor de acento) no topo do cabeçalho.
    pdf.set_fill_color(*_ACCENT_RGB)
    pdf.rect(0, 0, 210, 6, style="F")
    pdf.set_y(12)

    # Logo opcional — desenhada apenas se o arquivo existir; ausência nunca levanta erro.
    if _LOGO_PATH.exists():
        pdf.image(str(_LOGO_PATH), x=15, y=pdf.get_y(), h=12)
        pdf.set_xy(32, pdf.get_y())
    else:
        pdf.set_x(15)

    # Cabeçalho
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(text="IAprovale — Resultados da Busca", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # multi_cell (not cell) so a long query/summary wraps instead of running
    # off the right margin (same overflow class as the raw-URL bug fixed earlier).
    if query:
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, f"Busca: {query}", new_x="LMARGIN", new_y="NEXT")

    if extracted_summary:
        pdf.set_font("Helvetica", "I", 10)
        pdf.multi_cell(
            0, 5, f"A IA entendeu: {extracted_summary}", new_x="LMARGIN", new_y="NEXT"
        )
        pdf.set_font("Helvetica", "", 10)

    pdf.cell(
        text=f"Gerado em: {date.today().strftime('%d/%m/%Y')}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(5)

    # Linha divisória cinza
    pdf.set_draw_color(180, 180, 180)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)

    for i, c in enumerate(_ordenar_novos_primeiro(resultados), 1):
        titulo = c.get("titulo", "Sem título")
        # Prioriza os cargos compatíveis anotados pelo backend; fallback para
        # a lista completa quando ausente — mesma prioridade do ConcursoCard.
        cargos_list = c.get("cargos_compativeis") or c.get("cargos", [])
        cargos_filtrados = bool(c.get("cargos_compativeis"))
        localizacao = _fmt_localizacao(c)
        prazo = c.get("datas", {}).get("fim", "não informado")
        link = c.get("noticia", {}).get("link", "")

        # Início do card: registrar posição para desenhar a borda depois
        # (fpdf2 não tem borda automática multi-elemento — o padrão é
        # registrar y0, imprimir o conteúdo, e desenhar um rect ao final).
        x0 = pdf.get_x()
        y0 = pdf.get_y()

        # Badge NOVO — retângulo preenchido âmbar (cores do Badge.TLabel do app)
        if c.get("is_new"):
            pdf.set_fill_color(255, 193, 7)  # COLOR_BADGE_BG #ffc107
            pdf.set_text_color(58, 46, 0)  # COLOR_BADGE_FG #3a2e00
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(18, 5, text="NOVO", fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)

        # Título
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 6, f"{i}. {titulo}", new_x="LMARGIN", new_y="NEXT")

        # Localização (uf · região) — só quando o MCP traz o dado, logo após o título.
        if localizacao:
            pdf.set_text_color(90, 90, 90)
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(
                0, 5, f"Localização: {localizacao}", new_x="LMARGIN", new_y="NEXT"
            )
            pdf.set_text_color(0, 0, 0)

        # Cargos — truncados em 6 itens para evitar parede de texto. Rótulo
        # reflete a prioridade cargos_compativeis -> cargos (mesma do card).
        if cargos_list:
            if len(cargos_list) > 6:
                cargos_display = ", ".join(cargos_list[:6]) + f" (+{len(cargos_list) - 6} outros)"
            else:
                cargos_display = ", ".join(cargos_list)
            rotulo = "Cargos compatíveis:" if cargos_filtrados else "Cargos:"
            pdf.set_text_color(90, 90, 90)
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, f"{rotulo} {cargos_display}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)

        # Prazo
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(
            text=f"Inscrições até: {prazo}",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        # Borda do card (agora que a altura final é conhecida)
        y1 = pdf.get_y()
        pdf.set_draw_color(210, 210, 210)
        pdf.rect(x0, y0 - 1, 180, y1 - y0 + 2, style="D")

        pdf.ln(2)

        # Link como linha secundária/meta abaixo do card — rótulo curto e
        # clicável, nunca a URL crua (evita overflow da margem, ENTREGA-01).
        if link:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(0, 0, 200)
            pdf.cell(text="Ver notícia completa ->", link=link, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)

        pdf.ln(5)

    return bytes(pdf.output())
