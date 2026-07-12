"""Unit tests for pdf_export.gerar_pdf() — ENTREGA-01 (TDD RED phase).

These tests are purely unit-level: no Tk instance required, no filesystem
writes — gerar_pdf() returns bytes that are validated in-memory.
"""

from app.pdf_export import gerar_pdf


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
