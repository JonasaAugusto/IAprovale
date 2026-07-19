# App Web — scaffolding mockado (Fase 6)

Shell do app web do IAprovale: abas **Busca** e **Admin** mais a view de
**Perfil**, construídas com Alpine.js (build CSP) sobre o design system
compartilhado em `../shared/`.

Nesta fase tudo é **mock — zero chamadas de rede**: os resultados de busca, a
lista de usuários do Admin e o salvamento do Perfil (localStorage) são
simulações locais que estabelecem a anatomia da UI. A integração real com o
backend (login, busca via IA, administração de usuários) chega nas próximas
fases.

Estrutura:

- `index.html` — shell (header, abas, painéis e modais)
- `js/` — stores Alpine (`app.js`, `busca.js`, `perfil.js`, `admin.js`)
- `css/` — estilos por área (`app.css`, `busca.css`, `perfil.css`, `admin.css`)

A UI admin segue o mesmo ciclo de vida completo do cliente desktop: criar /
listar / desativar ↔ reativar (toggle suave, sem exclusão acidental) mais a
revelação de senha gerada com botão de copiar para a área de transferência.

Observação: arquivos `README.md` são removidos do artefato publicado no
GitHub Pages (ver `.github/workflows/pages.yml`) — este documento existe só
no repositório.
