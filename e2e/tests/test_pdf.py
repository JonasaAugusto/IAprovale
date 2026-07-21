"""Teste E2E caro: geracao/download real de PDF via UI, com asserção de
magic-bytes (mesmo check do backend, agora via page.expect_download()).

Precisa de uma busca previa pra popular `results` (o botao "Gerar PDF"
fica x-bind:disabled quando results.length === 0). Marcado
@pytest.mark.costly pelo mesmo motivo de test_busca.py: a busca que
precede o download gasta token de IA (T-12-02) - no maximo uma busca
por teste.

Nao roda no subset diario `pytest -m "not costly"` - so no gate
pre-release do checkpoint 12-04.
"""

import pytest

BASE_URL = "https://jonasaaugusto.github.io/IAprovale"

QUERY_AMPLA = "concurso na área de saúde"


@pytest.mark.costly
def test_gerar_pdf_produces_valid_pdf(authenticated_page, tmp_path):
    page = authenticated_page
    page.goto(f"{BASE_URL}/App/")

    page.fill(".busca-input", QUERY_AMPLA)
    page.click(".busca-btn-buscar")
    page.wait_for_selector(".busca-results .concurso-card", timeout=90_000)

    with page.expect_download() as download_info:
        page.click(".busca-btn-pdf")
    download = download_info.value

    dest = tmp_path / "concursos.pdf"
    download.save_as(dest)

    # Mesma asseracao de magic-bytes do backend (test_pdf.py privado):
    # nao parseamos conteudo do PDF - a corretude do template fpdf2 ja e
    # coberta pelos testes de desktop/backend (12-RESEARCH.md Don't
    # Hand-Roll). Aqui provamos so o round-trip real de download.
    assert dest.read_bytes()[:4] == b"%PDF"
