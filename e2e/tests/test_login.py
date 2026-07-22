"""Teste E2E barato: login (sucesso + falha segura).

Teste 1 reusa `authenticated_page` (session-scoped, já loga uma única vez
via /Login real) só pra confirmar que o login válido redireciona pro
/App e o shell logado aparece - sem repetir o login.

Teste 2 usa uma CONTEXT/PAGE NOVA (não a `authenticated_page`
compartilhada) com um username claramente INEXISTENTE, numa única
tentativa: o backend tem lockout de 5 falhas por conta
(app/auth/service.py) - jamais repetir essa tentativa em loop nem usar a
conta E2E real aqui (T-12-04 do 12-02-PLAN.md).

Roda no subset barato (sem marker de custo de IA): login não dispara IA/MCP.
"""

import uuid

from playwright.sync_api import expect

BASE_URL = "https://jonasaaugusto.github.io/IAprovale"


def test_login_valid_credentials_redirects_to_app(authenticated_page):
    page = authenticated_page
    assert "/App" in page.url
    expect(page.locator("button:has-text('Perfil')")).to_be_visible()


def test_login_invalid_credentials_shows_error(browser):
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(90_000)
    try:
        page.goto(f"{BASE_URL}/Login/")

        username_inexistente = f"nao_existe_{uuid.uuid4().hex[:8]}"
        page.fill("#login-username", username_inexistente)
        page.fill("#login-password", "senha-qualquer-123")
        page.click("#login-form button[type=submit]")

        expect(page.locator("#login-error")).to_be_visible()
    finally:
        context.close()
