"""Teste E2E barato: round-trip real do Perfil (PUT /profile -> GET /profile).

Preenche um campo estável do perfil, salva, deixa o modal fechar sozinho
(callback `handlePerfilSalvo()` do próprio app.js), recarrega a página
(`perfilForm.init()` só roda uma vez por carga de página - reabrir o modal
via x-show NÃO refaz o GET, então só um reload real força um GET /profile
novo) e reabre o modal, confirmando que o valor persistiu no backend - não
só que o form aceita input local.

Roda no subset barato (sem marker de custo de IA): salvar perfil não dispara IA nem MCP.
"""

import uuid

from playwright.sync_api import expect

BASE_URL = "https://jonasaaugusto.github.io/IAprovale"


def test_perfil_save_persists_after_reopen(authenticated_page):
    page = authenticated_page
    page.goto(f"{BASE_URL}/App/")

    valor_teste = f"e2e-teste-{uuid.uuid4().hex[:8]}"
    campo_areas = page.locator(
        "#perfil-dialog input[placeholder='ex: saúde, educação']"
    )

    page.click("button:has-text('Perfil')")
    page.wait_for_selector("#perfil-dialog", state="visible")

    campo_areas.fill(valor_teste)
    page.click("#perfil-dialog button:has-text('Salvar')")

    # salvar() dispara o evento "cf-perfil-salvo" ~1.2s depois do PUT
    # bem-sucedido, que fecha o modal e volta pra aba Busca
    # (app.js handlePerfilSalvo) - esperar o modal sumir prova que o PUT
    # terminou sem erro (salvarErro teria mantido o modal aberto).
    page.wait_for_selector("#perfil-dialog", state="hidden")

    page.reload()
    page.wait_for_selector("#panel-busca", state="visible")

    page.click("button:has-text('Perfil')")
    page.wait_for_selector("#perfil-dialog", state="visible")

    expect(campo_areas).to_have_value(valor_teste)
