"""Unit tests for pdf_export.gerar_pdf() — ENTREGA-01 (TDD RED phase).

These tests are purely unit-level: no Tk instance required, no filesystem
writes — gerar_pdf() returns bytes that are validated in-memory.
"""

import re
import zlib

from app.pdf_export import _fmt_prazo, _ordenar_novos_primeiro, gerar_pdf


def _decoded_content_streams(pdf_bytes: bytes) -> bytes:
    """fpdf2 FlateDecode-compresses page content streams by default, so
    visible text (drawn via Tj/TJ operators) isn't found via a plain
    substring search on the raw bytes — decompress every `stream`...
    `endstream` block and concatenate the ones that inflate cleanly
    (skips binary streams like fonts/images that aren't zlib-compressed
    text)."""
    decoded = bytearray()
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", pdf_bytes, re.DOTALL):
        raw = match.group(1)
        try:
            decoded += zlib.decompress(raw)
        except zlib.error:
            continue
    return bytes(decoded)


def test_ordenar_novos_primeiro_estavel():
    """NOVO/is_new concursos vem primeiro, preservando ordem relativa dentro
    de cada grupo (sort estável) — mesmo quando um não-novo vem antes."""
    resultados = [
        {"titulo": "Antigo A", "is_new": False},
        {"titulo": "Novo A", "is_new": True},
        {"titulo": "Antigo B", "is_new": False},
        {"titulo": "Novo B", "is_new": True},
    ]
    ordenado = _ordenar_novos_primeiro(resultados)
    assert [c["titulo"] for c in ordenado] == ["Novo A", "Novo B", "Antigo A", "Antigo B"]


def test_gerar_pdf_ordena_novos_primeiro():
    """O PDF renderizado lista NOVO antes do não-novo, mesmo com a entrada
    na ordem inversa (verificado via posição do título no texto extraído)."""
    resultado = [
        {
            "titulo": "Antigo",
            "cargos": [],
            "datas": {"fim": "sem data"},
            "noticia": {"link": ""},
            "is_new": False,
        },
        {
            "titulo": "Novo",
            "cargos": [],
            "datas": {"fim": "sem data"},
            "noticia": {"link": ""},
            "is_new": True,
        },
    ]
    decoded = _decoded_content_streams(gerar_pdf(resultado, ""))
    # A ordem impressa é "1. Novo" antes de "2. Antigo".
    assert b"1. Novo" in decoded
    assert decoded.index(b"1. Novo") < decoded.index(b"2. Antigo")


def test_gerar_pdf_mostra_ia_entendeu_quando_summary_presente():
    """Quando extracted_summary é fornecido, o cabeçalho mostra o rótulo
    'A IA entendeu:' — quando ausente, o rótulo não aparece."""
    resultado = [
        {
            "titulo": "Concurso X",
            "cargos": [],
            "datas": {"fim": "sem data"},
            "noticia": {"link": ""},
            "is_new": False,
        }
    ]
    com_summary = _decoded_content_streams(
        gerar_pdf(resultado, "busca", "Pesquisa por 'enfermagem' em SP")
    )
    assert b"A IA entendeu" in com_summary

    sem_summary = _decoded_content_streams(gerar_pdf(resultado, "busca"))
    assert b"A IA entendeu" not in sem_summary


def test_gerar_pdf_link_nao_expoe_url_crua():
    """O link é impresso como um rótulo curto e clicável, nunca a URL crua
    (evita overflow da margem no PDF)."""
    url = "https://www.pciconcursos.com.br/noticias/algum-concurso-bem-especifico-aqui-2026"
    resultado = [
        {
            "titulo": "Concurso Y",
            "cargos": [],
            "datas": {"fim": "sem data"},
            "noticia": {"link": url},
            "is_new": False,
        }
    ]
    # The raw URL legitimately appears once in the PDF's link ANNOTATION
    # (the /URI action needed for the link to be clickable) — but the
    # VISIBLE TEXT (content stream) must show only the short label, never
    # the raw URL overflowing the margin.
    decoded = _decoded_content_streams(gerar_pdf(resultado, ""))
    assert url.encode() not in decoded
    assert "Ver notícia completa".encode("windows-1252") in decoded


def test_gerar_pdf_signature_aceita_extracted_summary_opcional():
    """A nova assinatura mantém extracted_summary opcional — chamadas
    existentes com 2 argumentos posicionais continuam funcionando."""
    result = gerar_pdf([], "busca")
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_gerar_pdf_retorna_bytes():
    """gerar_pdf com resultado básico retorna bytes > 0 começando com %PDF."""
    resultado = [
        {
            "titulo": "Cargo A",
            "cargos": ["Engenheiro"],
            "datas": {"fim": "31/12/2026"},
            "noticia": {"link": "https://exemplo.com"},
            "is_new": False,
        }
    ]
    result = gerar_pdf(resultado, "busca teste")
    assert isinstance(result, bytes)
    assert len(result) > 0
    assert result[:4] == b"%PDF"


def test_gerar_pdf_lista_vazia():
    """gerar_pdf com lista vazia retorna bytes PDF válidos sem levantar exceção."""
    result = gerar_pdf([], "")
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_gerar_pdf_query_e_summary_longos_nao_estouram(monkeypatch):
    """T-07: uma query e um resumo muito longos devem quebrar em várias linhas
    (multi_cell), não estourar a margem — antes usavam cell() e saíam da
    página. Gerar não pode levantar exceção com texto longo."""
    query_longa = "concurso " * 60  # ~480 chars, bem além da largura da página
    summary_longo = "Pesquisa por 'engenharia de software e áreas correlatas' " * 5
    resultado = [
        {
            "titulo": "Concurso Z",
            "cargos": [],
            "datas": {"fim": "sem data"},
            "noticia": {"link": ""},
            "is_new": False,
        }
    ]
    result = gerar_pdf(resultado, query_longa, summary_longo)
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_gerar_pdf_mostra_localizacao_quando_uf_e_regiao():
    """Quando uf e regiao existem, o PDF mostra 'Localização: UF · Região'
    logo após o título."""
    resultado = [
        {
            "titulo": "Concurso Localizado",
            "cargos": [],
            "datas": {"fim": "sem data"},
            "noticia": {"link": ""},
            "is_new": False,
            "uf": "MG",
            "regiao": "Sudeste",
        }
    ]
    decoded = _decoded_content_streams(gerar_pdf(resultado, ""))
    assert "Localização: MG · Sudeste".encode("windows-1252") in decoded


def test_gerar_pdf_omite_localizacao_sem_uf_e_regiao():
    """Quando uf e regiao estão ambos vazios/ausentes, a linha 'Localização:'
    não aparece no PDF."""
    resultado = [
        {
            "titulo": "Concurso Sem Localização",
            "cargos": [],
            "datas": {"fim": "sem data"},
            "noticia": {"link": ""},
            "is_new": False,
        }
    ]
    decoded = _decoded_content_streams(gerar_pdf(resultado, ""))
    assert "Localização:".encode("windows-1252") not in decoded


def test_gerar_pdf_prioriza_cargos_compativeis():
    """Quando cargos_compativeis está presente, o PDF usa essa lista com o
    rótulo 'Cargos compatíveis:', ignorando cargos completo."""
    resultado = [
        {
            "titulo": "Concurso Filtrado",
            "cargos_compativeis": ["Enfermeiro"],
            "cargos": ["Enfermeiro", "Médico", "Outro"],
            "datas": {"fim": "sem data"},
            "noticia": {"link": ""},
            "is_new": False,
        }
    ]
    decoded = _decoded_content_streams(gerar_pdf(resultado, ""))
    assert "Cargos compatíveis:".encode("windows-1252") in decoded
    assert "Enfermeiro".encode("windows-1252") in decoded


def test_gerar_pdf_fallback_cargos_sem_compativeis():
    """Quando cargos_compativeis está ausente, o PDF cai para cargos com o
    rótulo 'Cargos:' (não 'Cargos compatíveis:')."""
    resultado = [
        {
            "titulo": "Concurso Sem Filtro",
            "cargos": ["Analista"],
            "datas": {"fim": "sem data"},
            "noticia": {"link": ""},
            "is_new": False,
        }
    ]
    decoded = _decoded_content_streams(gerar_pdf(resultado, ""))
    assert "Cargos:".encode("windows-1252") in decoded
    assert "Analista".encode("windows-1252") in decoded
    assert "Cargos compatíveis:".encode("windows-1252") not in decoded


def test_gerar_pdf_ptbr_chars():
    """gerar_pdf com caracteres PT-BR não levanta UnicodeEncodeError."""
    resultado = [
        {
            "titulo": "Secretário de Saúde — Ação Municipal",
            "cargos": ["Técnico em Enfermagem"],
            "datas": {"fim": "não informado"},
            "noticia": {"link": ""},
            "is_new": True,
        }
    ]
    # Deve completar sem levantar UnicodeEncodeError
    result = gerar_pdf(resultado, "saúde com graduação")
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


# --- nota de formação futura (v1.4.0, paridade com o card) ---------------


def _concurso_futuro(**overrides) -> dict:
    concurso = {
        "titulo": "Concurso Futuro",
        "cargos": ["Enfermeiro"],
        "datas": {"fim": "31/12/2027"},
        "noticia": {"link": ""},
        "is_new": False,
    }
    concurso.update(overrides)
    return concurso


def _pdf_escape(texto: str) -> bytes:
    # No content stream do PDF, "(" e ")" aparecem escapados: \( e \).
    return (
        texto.encode("windows-1252").replace(b"(", rb"\(").replace(b")", rb"\)")
    )


def test_pdf_futuro_match_com_data_mostra_nota_com_mmaaaa():
    decoded = _decoded_content_streams(
        gerar_pdf([_concurso_futuro(futuro_match=True, data_formacao_futura="2027-12")], "")
    )
    nota = "Aberto para formação futura — quando você se formar (12/2027)"
    assert _pdf_escape(nota) in decoded


def test_pdf_futuro_match_sem_data_mostra_nota_sem_parenteses():
    decoded = _decoded_content_streams(
        gerar_pdf([_concurso_futuro(futuro_match=True)], "")
    )
    base = "Aberto para formação futura — quando você se formar"
    assert base.encode("windows-1252") in decoded
    assert _pdf_escape("(12/2027)") not in decoded


def test_pdf_sem_futuro_match_nao_mostra_nota():
    decoded = _decoded_content_streams(gerar_pdf([_concurso_futuro()], ""))
    assert "Aberto para formação futura".encode("windows-1252") not in decoded


# --- formatação BR do prazo (v1.5.2) --------------------------------------


def test_fmt_prazo_iso_para_br():
    assert _fmt_prazo("2026-12-14") == "14/12/2026"


def test_fmt_prazo_ja_br_passa_intacto():
    assert _fmt_prazo("31/12/2026") == "31/12/2026"


def test_fmt_prazo_sem_data_passa_intacto():
    assert _fmt_prazo("sem data") == "sem data"


def test_fmt_prazo_nao_informado_passa_intacto():
    assert _fmt_prazo("não informado") == "não informado"


def test_gerar_pdf_mostra_prazo_iso_formatado_br():
    resultado = [
        {
            "titulo": "Concurso Prazo ISO",
            "cargos": [],
            "datas": {"fim": "2026-12-14"},
            "noticia": {"link": ""},
            "is_new": False,
        }
    ]
    decoded = _decoded_content_streams(gerar_pdf(resultado, ""))
    assert "Inscrições até: 14/12/2026".encode("windows-1252") in decoded
