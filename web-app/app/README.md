# App Web (reservado — v2)

Esta pasta está reservada para o futuro app web real do projeto (login + busca via navegador,
direto no site — sem precisar instalar o app desktop).

Corresponde aos requisitos **WEB-01** e **WEB-02** do milestone v2 (ver `.planning/REQUIREMENTS.md`),
hoje reconhecidos mas adiados — não fazem parte do roadmap atual (que é focado no app desktop, v1).

Quando esse trabalho começar, ele vai reusar o mesmo backend FastAPI já construído em `../../backend/`.

Ainda sem código aqui — só o caminho preparado.

Quando essa UI admin web for construída, ela deve seguir o mesmo princípio de ciclo de vida
completo já estabelecido no cliente desktop: criar / listar / desativar ↔ reativar
(deactivate/reactivate — toggle suave, sem exclusão definitiva) mais uma revelação de senha
com botão de copiar para a área de transferência.
