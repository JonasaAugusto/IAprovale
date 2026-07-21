# Checklist de Paridade — IAprovale

Regra permanente do projeto: **toda mudança futura sai simultânea e igual em web e desktop.** Os dois clientes falam com o mesmo backend (mesma conta, mesmo perfil, mesma busca) — ver README.md §["Arquitetura compartilhada (backend único)"](README.md#arquitetura-compartilhada-backend-único) para o que é compartilhado por design. Este arquivo existe pra que essa disciplina, que já funcionou nas Fases 6-11 por memória do dev, não dependa só de memória: é o gate consultado antes de qualquer release.

Não é burocracia — é a única coisa que garante que quem usa o desktop e quem usa o web tenham a mesma experiência, sempre.

## Checklist de Paridade

| Área | Desktop | Web | Última verificação |
|------|---------|-----|---------------------|
| Login e sessão | ok | ok | WAUTH-01/02/03/04/05 |
| Busca em linguagem natural | ok | ok | WBUSCA-01 |
| Busca com perfil | ok | ok | WBUSCA-01 |
| Cards de resultado (badge NOVO, chips "+N outros", localização UF·região, prazo BR MM/AAAA, link copiar) | ok | ok | v1.5.2 (WBUSCA-02) |
| Tutorial "Como pesquisar" | ok | ok | v1.5.2 (WBUSCA-04) |
| Perfil completo (escolaridade cumulativa, formação futura MM/AAAA, CEP, mobilidade, áreas) | ok | ok | WPERFIL-01 |
| Currículo (anexar PDF/TXT, extração local, sem custo de IA) | ok | ok | WPERFIL-02 |
| PDF (POST /pdf, template fpdf2 idêntico) | ok | ok | WPDF-01/02 |
| Admin CRUD | ok | ok | WADMIN-01 |
| Tema claro/escuro | ok | ok | WEB-06 |
| Cold start tratado ("Conectando ao servidor...") | ok | ok | WAUTH-04 |
| Popup de divulgação da web (desktop only, by design) | v1.5.2 | N/A | DPOP-01, commit 18e83d0 |

**Legenda:** "ok" = comportamento entregue e íntegro no cliente na última verificação registrada; "—" (se aparecer) = ainda não verificado explicitamente; "N/A" = área que não se aplica a este cliente por decisão de design explícita (ex.: o popup de divulgação da web só faz sentido dentro do próprio app desktop).

## Antes de publicar um release

1. Rodar a suíte E2E completa: `cd e2e && pytest --headed --browser chromium -v` (ver [e2e/README.md](e2e/README.md) para setup e credenciais da conta de teste dedicada).
2. Atualizar a coluna "Última verificação" acima com a versão/commit que confirmou cada área (mesmo micro-formato já usado em REQUIREMENTS.md, ex.: `v1.5.3 (commit abcdef1)`).
3. Só então publicar o draft no release list (fluxo já usado em v1.4.0/v1.5.x — draft pinado, Jonas publica quando quiser que os usuários vejam).

Se qualquer linha da tabela não puder ser marcada "ok" nos dois clientes ao mesmo tempo, o release espera até que possa — paridade não é opcional, é a razão de existir de dois clientes pro mesmo backend.
