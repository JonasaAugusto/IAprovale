"""Testes do extrator de currículo (app.curriculo) — v1.1.0.

TXT e PDF (o PDF é gerado com fpdf2 e relido com pypdf, validando o caminho
que roda dentro do .exe). Sem Qt, sem rede.
"""

import pytest

from app import curriculo


def test_extrair_txt(tmp_path):
    p = tmp_path / "cv.txt"
    p.write_text("Nome: Ana\n\nExperiência: Enfermeira em UBS", encoding="utf-8")
    texto = curriculo.extrair_texto(str(p))
    assert "Ana" in texto
    assert "Enfermeira" in texto


def test_extrair_txt_vazio_levanta_vazio(tmp_path):
    p = tmp_path / "vazio.txt"
    p.write_text("   \n  \n", encoding="utf-8")
    with pytest.raises(curriculo.CurriculoVazioError):
        curriculo.extrair_texto(str(p))


def test_formato_nao_suportado_levanta_erro(tmp_path):
    p = tmp_path / "cv.docx"
    p.write_text("qualquer coisa", encoding="utf-8")
    with pytest.raises(curriculo.CurriculoError):
        curriculo.extrair_texto(str(p))


def test_nao_trunca_curriculo_grande(tmp_path):
    # Sem limite por decisão de produto: currículos reais passam de 5000 chars.
    p = tmp_path / "big.txt"
    p.write_text("a" * 20_000, encoding="utf-8")
    texto = curriculo.extrair_texto(str(p))
    assert len(texto) == 20_000


def test_extrair_pdf(tmp_path):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Curriculo de Teste Enfermeira")
    caminho = tmp_path / "cv.pdf"
    pdf.output(str(caminho))

    texto = curriculo.extrair_texto(str(caminho))
    assert "Enfermeira" in texto
