"""Teste E2E gratuito: renderizacao dos cards de busca via mock de rede.

Variante mockada e sempre-executavel de `test_busca.py`: reusa o login real
(fixture `authenticated_page`, session-scoped, sem custo de IA) mas
intercepta a chamada de rede do navegador `POST .../search` com
`page.route()` do Playwright, devolvendo um JSON fixo que segue o contrato
real da API. A requisicao NUNCA chega no backend real nem no DeepSeek -
roda no subset diario barato `pytest -m "not costly"` e serve de gate de
regressao pro template dos cards, complementando (nao substituindo)
`test_busca.py`, que segue como gate `@costly` de fidelidade maxima.
"""

import json

BASE_URL = "https://jonasaaugusto.github.io/IAprovale"

MOCK_RESPONSE = {
    "results": [
        {
            "titulo": "Concurso Mock A - Analista de Saude",
            "uf": "SP",
            "regiao": "sudeste",
            "cargos_compativeis": ["Analista de Saude", "Tecnico de Enfermagem"],
            "is_new": True,
            "data_formacao_futura": "2027-06",
            "prazo": "2026-12-31",
            "noticia": {"link": "https://www.pciconcursos.com.br/noticia/mock-a/"},
        },
        {
            "titulo": "Concurso Mock B - Tecnico Administrativo",
            "uf": "MG",
            "regiao": "sudeste",
            "cargos": ["Tecnico Administrativo"],
            "is_new": False,
            "noticia": {"link": "https://www.pciconcursos.com.br/noticia/mock-b/"},
        },
    ],
    "is_empty": False,
    "message": "",
}


def test_busca_mock_renders_result_cards(authenticated_page):
    page = authenticated_page

    def handler(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(MOCK_RESPONSE),
        )

    page.route("**/search", handler)

    try:
        page.fill(".busca-input", "qualquer frase — nao vai pro backend")
        page.click(".busca-btn-buscar")

        # Escopo ".busca-results .concurso-card" (nao so ".concurso-card"):
        # o skeleton de loading tambem usa a classe "concurso-card" nos
        # placeholders visiveis enquanto loading=true.
        page.wait_for_selector(".busca-results .concurso-card")

        cards = page.locator(".busca-results .concurso-card")
        assert cards.count() == len(MOCK_RESPONSE["results"])

        primeiro_titulo = cards.first.locator(".concurso-card-titulo").inner_text()
        assert primeiro_titulo.strip() == MOCK_RESPONSE["results"][0]["titulo"]
    finally:
        # Higiene: authenticated_page e session-scoped (page compartilhada),
        # entao a interceptacao nao pode vazar pro proximo teste (ex.:
        # test_busca.py real, se rodar na mesma invocacao do pytest).
        page.unroute("**/search")
