"""Teste E2E caro: busca em linguagem natural via a UI real.

Dispara UMA busca em linguagem natural contra o pipeline completo
(DeepSeek -> MCP PCI Concursos -> backend Render -> DOM) e assere que
resultados renderizam. Marcado @pytest.mark.costly: a conta E2E e admin
(isenta de cota, app/search/quota.py), mas NAO e isenta do custo de IA
por chamada nem do anti-rajada de 10 buscas/60s (app/search/ratelimit.py)
- por isso, no maximo uma busca por teste (T-12-02).

Nao roda no subset diario `pytest -m "not costly"` - so no gate
pre-release do checkpoint 12-04.
"""

import pytest

BASE_URL = "https://jonasaaugusto.github.io/IAprovale"

# Frase ampla e determinística: o objetivo e provar que o pipeline
# responde e renderiza, nao validar precisao de filtro (ja coberto por
# unit/integration no backend/desktop - 12-RESEARCH.md Don't Hand-Roll).
QUERY_AMPLA = "concurso na área de saúde"


@pytest.mark.costly
def test_busca_natural_language_renders_result_cards(authenticated_page):
    page = authenticated_page
    page.goto(f"{BASE_URL}/App/")

    page.fill(".busca-input", QUERY_AMPLA)
    page.click(".busca-btn-buscar")

    # Escopo ".busca-results .concurso-card" (nao so ".concurso-card"):
    # o skeleton de loading (linhas 134-138 de App/index.html) tambem usa
    # a classe "concurso-card" nos placeholders visiveis enquanto
    # loading=true - sem esse escopo, o wait_for_selector destravaria no
    # skeleton, nao no resultado real. Busca leva 30-90s (WBUSCA-03) -
    # timeout explicito e generoso, sem sleep hand-rolled (auto-waiting
    # do Playwright faz o polling).
    page.wait_for_selector(".busca-results .concurso-card", timeout=90_000)

    cards = page.locator(".busca-results .concurso-card")
    assert cards.count() > 0

    primeiro_titulo = cards.first.locator(".concurso-card-titulo").inner_text()
    assert primeiro_titulo.strip() != ""
