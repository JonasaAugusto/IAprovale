"""Fixtures compartilhadas da suite E2E (Playwright + pytest) do IAprovale.

A suite roda contra a producao real (GitHub Pages + Render), nao ha app
first-party pra importar aqui — so stdlib (os, uuid) e pytest. As fixtures
`browser`/`page`/`context` sao auto-injetadas pelo plugin pytest-playwright.

Nao ha try/except decorativo em volta do login: um `TimeoutError` do
Playwright e o sinal natural de falha (ex.: cold start do Render, credenciais
erradas, selector mudou) — deixamos ele estourar.
"""

import os
import uuid

import pytest

BASE_URL = "https://jonasaaugusto.github.io/IAprovale"


@pytest.fixture(scope="session")
def authenticated_page(browser):
    """Loga uma unica vez por sessao de testes via o /Login real.

    Le as credenciais da conta admin dedicada de teste em
    E2E_ADMIN_USERNAME/E2E_ADMIN_PASSWORD (nunca hardcoded — T-12-01).
    O timeout default e elevado pra 90s antes da primeira navegacao pra
    tolerar o cold start do Render free tier (Pitfall 4 do 12-RESEARCH.md).
    """
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(90_000)

    page.goto(f"{BASE_URL}/Login/")
    page.fill("#login-username", os.environ["E2E_ADMIN_USERNAME"])
    page.fill("#login-password", os.environ["E2E_ADMIN_PASSWORD"])
    page.click("#login-form button[type=submit]")
    page.wait_for_url(f"{BASE_URL}/App/**")

    yield page

    context.close()


@pytest.fixture
def disposable_admin_user(authenticated_page):
    """Factory fixture: cria sub-usuarios test_e2e_<uuid> pela UI da aba Admin
    e SEMPRE tenta excluir cada um no teardown, mesmo se o teste falhar no
    meio (T-12-03 — Repudiation/hygiene). Nunca opera sobre a conta admin
    compartilhada (authenticated_page) em si, so sobre sub-usuarios criados
    por ela.
    """
    page = authenticated_page
    created_usernames: list[str] = []

    def _criar_usuario() -> str:
        username = f"test_e2e_{uuid.uuid4().hex[:8]}"

        page.click("button:has-text('Admin')")
        page.wait_for_selector("#panel-admin", state="visible")
        page.fill(".admin-add-input", username)
        page.click("button:has-text('Adicionar usuário')")

        # A senha gerada aparece uma unica vez no #reveal-dialog.
        page.wait_for_selector("#reveal-dialog", state="visible")
        page.click("#reveal-dialog .modal-close")

        created_usernames.append(username)
        return username

    yield _criar_usuario

    for username in created_usernames:
        try:
            page.click("button:has-text('Admin')")
            page.wait_for_selector("#panel-admin", state="visible")
            row = page.locator(".admin-user-row", has=page.locator(
                f".admin-user-username:text-is('{username}')"
            ))
            row.get_by_role("button", name="Excluir").click()
            page.wait_for_selector("#confirm-dialog", state="visible")
            # Escopado por texto (nao por classe CSS): quando
            # confirmDestrutivo=true (excluir/desativar), admin.js
            # (x-bind:class="confirmDestrutivo ? 'btn-ghost admin-action-destructive' : ...")
            # faz o Alpine mesclar "btn-ghost" no PROPRIO botao de acao,
            # deixando-o com a MESMA classe do botao Cancelar - portanto
            # "button.btn:not(.btn-ghost)" nao selecionava nada nesse caso.
            page.locator("#confirm-dialog").get_by_role("button", name="Excluir").click()
        except Exception:
            # Cleanup best-effort: uma asseracao falha no meio do teste nao
            # pode impedir a tentativa de limpeza dos demais usuarios criados.
            pass


@pytest.fixture(autouse=True)
def _reset_estado_app(authenticated_page):
    """Reseta o estado do shell Alpine antes de CADA teste.

    `authenticated_page` e session-scoped (uma unica aba compartilhada por
    toda a suite, pra evitar relogar a cada teste) — isso significa que o
    estado do shell (aba ativa `tab`, modais abertos como #reveal-dialog/
    #rename-dialog/#confirm-dialog/#perfil-dialog) VAZA de um arquivo de
    teste pro proximo. Ex.: test_admin.py deixa `tab === 'admin'`; se
    test_busca.py rodar em seguida (ordem alfabetica padrao do pytest),
    #panel-busca continua com display:none e .busca-input nunca fica
    visivel, estourando timeout.

    Roda ANTES de cada funcao de teste, independente da ordem de execucao
    ou do que o teste anterior deixou pra tras: fecha qualquer modal
    remanescente (Escape), clica na aba Busca, e espera #panel-busca ficar
    visivel — garante que todo teste comeca num estado conhecido.
    """
    page = authenticated_page
    page.keyboard.press("Escape")
    page.click("button:has-text('Busca')")
    page.wait_for_selector("#panel-busca", state="visible")
