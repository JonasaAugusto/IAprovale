"""Teste E2E barato: CRUD completo de administração contra um sub-usuário
DESCARTÁVEL (test_e2e_<uuid>), nunca a conta admin da sessão.

Fluxo: cria via a factory `disposable_admin_user` (12-01) -> renomeia e
volta ao nome original (pra não quebrar a busca por username do teardown
da própria factory, que localiza o usuário a excluir pelo nome original)
-> gera nova senha (reset) -> desativa -> reativa. A exclusão final é
responsabilidade do teardown da factory (T-12-03), garantida mesmo se uma
asserção deste teste falhar no meio - por isso o corpo do teste nunca
chama a ação "Excluir" diretamente.

Roda no subset barato (sem marker de custo de IA): CRUD de admin não dispara IA/MCP.
"""

from playwright.sync_api import expect

BASE_URL = "https://jonasaaugusto.github.io/IAprovale"


def _linha_usuario(page, username):
    return page.locator(
        ".admin-user-row",
        has=page.locator(f".admin-user-username:text-is('{username}')"),
    )


def _renomear(page, row, novo_nome):
    row.get_by_role("button", name="Editar nome").click()
    page.wait_for_selector("#rename-dialog", state="visible")
    page.fill("#rename-dialog input", novo_nome)
    page.click("#rename-dialog button:has-text('Salvar')")
    page.wait_for_selector("#rename-dialog", state="hidden")


def _confirmar(page, texto_botao):
    # Todas as ações de admin (gerar senha/desativar/reativar/excluir)
    # passam por #confirm-dialog antes de executar - o botão de ação usa
    # o mesmo texto que disparou a ação na linha (confirmTextoBotao em
    # admin.js), escopado ao dialog pra não colidir com o botão homônimo
    # da própria linha do usuário (ainda visível atrás do modal).
    page.wait_for_selector("#confirm-dialog", state="visible")
    page.locator("#confirm-dialog").get_by_role("button", name=texto_botao).click()
    page.wait_for_selector("#confirm-dialog", state="hidden")


def test_admin_crud_disposable_user(authenticated_page, disposable_admin_user):
    page = authenticated_page
    username = disposable_admin_user()

    row = _linha_usuario(page, username)
    expect(row).to_be_visible()

    # Renomear (via #rename-dialog) e devolver ao nome original.
    novo_nome = f"{username}_renomeado"
    _renomear(page, row, novo_nome)
    row = _linha_usuario(page, novo_nome)
    expect(row).to_be_visible()
    _renomear(page, row, username)
    row = _linha_usuario(page, username)
    expect(row).to_be_visible()

    # Gerar nova senha / reset (via #confirm-dialog -> #reveal-dialog).
    row.get_by_role("button", name="Gerar nova senha").click()
    _confirmar(page, "Gerar nova senha")
    page.wait_for_selector("#reveal-dialog", state="visible")
    page.click("#reveal-dialog .modal-close")
    page.wait_for_selector("#reveal-dialog", state="hidden")

    # Desativar (via #confirm-dialog).
    row.get_by_role("button", name="Desativar").click()
    _confirmar(page, "Desativar")
    expect(row.locator(".admin-tag-inativo")).to_be_visible()

    # Reativar (via #confirm-dialog).
    row.get_by_role("button", name="Reativar").click()
    _confirmar(page, "Reativar")
    expect(row.locator(".admin-tag-inativo")).to_be_hidden()

    # A conta da sessão (authenticated_page / E2E_ADMIN_USERNAME) nunca é
    # alvo de nenhuma ação acima - todas operam sobre `row`, localizado
    # exclusivamente pelo username descartável test_e2e_<uuid> criado por
    # disposable_admin_user.
