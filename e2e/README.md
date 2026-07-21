# Suite E2E (Playwright + pytest) — IAprovale

Testes de ponta a ponta rodando um Chromium real contra a **producao real**
(`https://jonasaaugusto.github.io/IAprovale/Login/` e `/App/`, backend real no
Render, mesmo banco de dados). Nao existe staging: `BASE_URL` e hardcoded em
`web-app/shared/js/api.js` sem toggle, entao rodar contra producao real com
uma conta admin dedicada e isenta de cota da uma fidelidade maxima ao que o
usuario real recebe, sem precisar patchear nada nem subir infraestrutura de
teste separada.

## Instalacao

```bash
cd e2e
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Conta de teste dedicada (obrigatoria antes de rodar qualquer teste)

A suite precisa de uma conta **admin** dedicada de teste (admin porque o
backend isenta contas admin do limite diario de buscas —
`app/search/quota.py` — o que evita estourar cota rodando a suite varias
vezes). **Nunca use a conta real "jonas"** pra isso.

Provisionamento (uma unica vez, no repo privado `iaprovalebackend`):

```bash
cd D:\Projects\iaprovalebackend
python -m scripts.create_admin test_e2e_admin
```

O script recusa se o nome ja existir e imprime a senha gerada **uma unica
vez** no stdout — copie imediatamente pro seu `e2e/.env` local (nunca vai
aparecer de novo). Copie `.env.example` para `.env` (dentro de `e2e/`) e
preencha:

```
E2E_ADMIN_USERNAME=test_e2e_admin
E2E_ADMIN_PASSWORD=<senha impressa pelo script>
```

O `.env` real nunca e commitado (`.gitignore` da raiz ja cobre qualquer
`.env` em qualquer pasta).

## Rodando os testes

Suite rapida (login/perfil/admin — sem custo de IA, seguro rodar a qualquer
hora):

```bash
pytest -m "not costly" -v
```

Suite completa (inclui busca e PDF, que exercitam o pipeline real do
DeepSeek — reservado pra checagem pre-release, ver `PARIDADE.md` na raiz do
repo):

```bash
pytest --headed --browser chromium -v
```

`--headed` deixa o navegador visivel — util pra um dev solo acompanhar
visualmente a suite antes de um release; remova a flag pra rodar mais rapido
em modo headless depois que a suite ja estiver validada.
