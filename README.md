# IAprovale (Concurso Finder)

Buscador de concursos públicos privado e por convite, com IA. O usuário descreve em linguagem natural o que procura (ex: *"concurso na área de saúde com graduação em enfermagem"*) e o sistema filtra automaticamente apenas os concursos com inscrições abertas que aceitam a formação informada, a pesquisa também é alimentada por um sistema de Formulário na aba de Perfil.

**Versões:** desktop **v2.0.1** (Windows) · web app **v2.0** (GitHub Pages) — funcionalidades completas, aguardando checkpoint final de E2E antes do release

## Sumário

- [Como funciona](#como-funciona)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Arquitetura compartilhada (backend único)](#arquitetura-compartilhada-backend-único) · o que é comum aos dois apps: login, busca, perfil, administração
- [App Desktop (Windows)](#app-desktop-windows) · o que é exclusivo do desktop
- [App Web (GitHub Pages)](#app-web-github-pages) · o que é exclusivo do web
- [Decisões de design](#decisões-de-design)
- [Segurança](#segurança)
- [Funcionalidades](#funcionalidades)
- [Rodando localmente](#rodando-localmente)
- [Status e licença](#status-e-licença)

## Como funciona

1. Login em uma conta previamente criada por um administrador (sem autocadastro público).
2. A pessoa descreve o que procura em português natural, ou busca direto com o perfil salvo.
3. O backend traduz a busca com IA, consulta a fonte oficial de concursos (MCP da PCI Concursos) e filtra pelos resultados com inscrições abertas compatíveis com a formação.
4. Os resultados aparecem em cards com localização, cargos compatíveis e prazo. Concursos ainda não vistos ganham o badge **NOVO**; os já vistos continuam aparecendo sempre.
5. É possível gerar um PDF com o mesmo padrão visual dos cards, no desktop ou no navegador.

## Estrutura do repositório

```
desktop/    Cliente desktop (Windows): login, busca, resultados, perfil e administração
web-app/    Homepage institucional + web app (rotas /Login e /App)
e2e/        Suíte Playwright (Python) de ponta-a-ponta contra o backend real
```

O backend (FastAPI) vive em um repositório privado separado e é deployado numa VPS própria (https://api.iaprovale.augustusai.com.br). Este repositório público contém apenas os clientes.

## Arquitetura compartilhada (backend único)

Os dois apps são clientes do **mesmo backend**: mesma conta, mesmo perfil, mesma busca. Tudo nesta seção vale simultaneamente para desktop e web.

Antes de cada release, o checklist em [PARIDADE.md](PARIDADE.md) é conferido pra garantir que toda mudança saiu igual nos dois clientes.

### Backend (repositório privado)

API REST assíncrona em **FastAPI + Uvicorn**, organizada em módulos independentes:

| Módulo | Responsabilidade |
|--------|------------------|
| `auth` | Login/logout, sessões e administração de usuários (criar, renomear, ativar/desativar, excluir) |
| `profile` | Perfil de formação do usuário (escolaridade, formações, mobilidade, currículo) |
| `search` | Pipeline da busca: IA traduz a frase → consulta ao MCP da PCI Concursos → filtros de compatibilidade → marcação de já vistos, com limite de uso por usuário |
| `cep` | Consulta de CEP para preencher cidade/UF no perfil |
| `core` / `db` | Configuração, dependências de autenticação e modelos de dados (SQLModel + Postgres local da VPS) |

Tecnologias do backend: **DeepSeek** (via SDK OpenAI-compatível) para estruturar a busca, **MCP oficial da PCI Concursos** (JSON-RPC via httpx, sem scraping) como fonte de dados, **SQLModel/SQLAlchemy + Postgres** para persistência, **VPS própria com Caddy** (HTTPS Let's Encrypt automático) para hospedagem.

### Fluxos idênticos nos dois clientes

- **Login e sessão**: as mesmas contas funcionam no desktop e no navegador; a sessão é encerrada no servidor ao sair.
- **Busca em linguagem natural**: a IA entende formação, cargo, cidade/estado/região e busca para terceiros ("concurso para minha esposa, que é engenheira").
- **Busca com perfil**: um clique busca "na minha área" usando a formação salva.
- **Dedup sem esconder nada**: concursos já vistos são apenas marcados (badge NOVO nos inéditos); a busca sempre retorna novos e antigos.
- **Conexão tratada**: os dois clientes mostram "Conectando ao servidor..." durante o login e reconectam sozinhos se a rede cair; o backend na VPS responde em menos de 1 s.
- **Administração**: gestão de usuários exclusiva de contas admin, com revalidação de permissão no servidor a cada operação.

## App Desktop (Windows)

Cliente nativo empacotado em `.exe` standalone. É a versão completa e estável (v2.0.1).

- **Python 3 + PySide6 (Qt 6)** com **PySide6-Fluent-Widgets**: visual Fluent Design, tema claro/escuro ao vivo.
- **Exportação em PDF local** (fpdf2, 100% Python): mesmo padrão visual dos cards, com Visualizar / Salvar / Apagar.
- **Currículo no perfil**: anexo PDF/TXT com extração de texto local (pypdf), sem custo de IA; com um toggle, a IA usa o currículo para enriquecer a busca.
- **Formação futura**: graduação em andamento com data de formatura conta como formação compatível quando o prazo do concurso alcança a data.
- **Sessão persistida com auto-login** resiliente a quedas de rede.
- **Auto-update nível 1**: o app avisa quando existe versão nova no GitHub (sem substituir o binário sozinho).
- **Popup de divulgação do web app**: mostrado uma vez por instalação, convida a experimentar a versão web sem forçar a troca.
- **UI nunca trava**: chamadas de rede rodam fora da thread da interface; buscas longas não congelam a janela.
- **PyInstaller** para o executável, imports pesados carregados sob demanda para startup rápido.
- Quase 200 testes automatizados cobrindo login, busca, perfil, PDF e admin.

## App Web (GitHub Pages)

Web app (milestone v2.0) que reusa o mesmo backend do desktop, acessível de qualquer navegador sem instalar nada. Todas as funcionalidades principais já estão ligadas ao backend real — falta só o checkpoint final de testes ponta-a-ponta antes do release.

- **Site 100% estático, sem build step**: HTML + CSS puro + JavaScript vanilla, publicado no GitHub Pages por workflow do GitHub Actions.
- **Alpine.js (build CSP)** para reatividade das telas, carregado de CDN com verificação de integridade.
- **Design system próprio** (tokens de cor/tipografia, tema claro/escuro persistente) com paridade visual ao desktop: verde no claro, dourado no escuro, fontes Inter/Fraunces.
- **Rotas**: homepage institucional na raiz, `/Login` e `/App` (abas Busca e Admin, modal de Perfil).
- **Sessão só no navegador**: o login vale para a aba atual e expira sozinho após um período de inatividade; fechar o navegador encerra a sessão. Sem "continuar logado" automático, por decisão de design.
- **Busca real** em linguagem natural, com os mesmos cards ricos e seguros do desktop (XSS-safe, nunca via HTML dinâmico).
- **Perfil e currículo reais**: formulário completo com round-trip no backend; extração local de PDF/TXT direto no navegador (pdfjs-dist), sem custo de IA.
- **Exportação em PDF no navegador**: baixa ou visualiza em nova aba, com o mesmo layout do PDF gerado no desktop.
- **Administração real**: CRUD completo de usuários pela aba Admin, com a mesma paridade do desktop e reforço de autorização no servidor.
- **Suíte Playwright de ponta-a-ponta** (`e2e/`) cobrindo login, busca, perfil, PDF e admin contra o backend real — separada por marker em subset barato (`-m "not costly"`: login, perfil, admin) e subset caro (`@pytest.mark.costly`: busca e PDF, os únicos que gastam tokens de IA de verdade), pra rodar o barato à vontade e reservar o caro pra checagem pré-release.

## Decisões de design

- **Backend client-agnóstico**: toda a lógica pesada (IA, MCP, filtros, dedup) vive na API; qualquer cliente novo consome os mesmos endpoints sem retrabalho.
- **Fonte oficial, sem scraping**: os dados vêm do servidor MCP da própria PCI Concursos, estruturados.
- **Acesso privado por convite**: sem autocadastro; só o admin cria e gerencia contas.
- **Web sem framework nem bundler**: menos superfície de ataque, deploy trivial em hospedagem estática gratuita e compatibilidade com política de segurança de conteúdo rígida.
- **Paridade visual entre clientes**: cards, badges, textos de ajuda e mensagens de erro seguem o mesmo padrão no desktop e no web.
- **Migração do Render para a VPS própria (24/10/2026)**: a API saiu do Render (free tier) e dos dados no Supabase e passou a rodar em https://api.iaprovale.augustusai.com.br.
  - **Por quê**: (1) custo, pois a VPS já existe e hospeda os outros projetos, sem plano pago do Render; (2) sem cold start, já que o free tier hibernava após inatividade e o primeiro acesso levava de 30 a 90 s, por isso o aviso de 1 minuto saiu dos textos do desktop e do web; (3) tudo no backup, porque o banco passa a entrar no backup diário restic da VPS (dump do banco + pasta do projeto), o que o Supabase fora do backup não garantia; (4) bancos internos na VPS, sem Supabase, para ter controle e um único lugar de operação.
  - **Como ficou**: o uvicorn roda como serviço **systemd** (`Restart=on-failure`), escutando só em `127.0.0.1`, com usuário Linux próprio e `.env` com permissão restrita. O **Caddy** é o proxy na frente, com HTTPS automático (Let's Encrypt) e cabeçalhos de segurança; só as portas 80/443 foram abertas e o Postgres escuta apenas em loopback. Os dados do Supabase (schema `public`) foram restaurados com `pg_dump`/`pg_restore` no **Postgres local** da VPS, com contagem de linhas conferida.
  - **Clientes**: o web (GitHub Pages) e o desktop (v2.0.1) apontam para a nova API (no desktop continua configurável por `CONCURSO_FINDER_BACKEND_URL`), e o webhook do Mercado Pago foi reapontado para `/webhooks/mercadopago` no novo domínio. O Render e o Supabase ficam como reserva por alguns dias antes de serem desligados.
  - Buscas mantêm timeout de 90 s (IA + MCP) e a API responde em menos de 1 s.
- **Testes como guarda de regressão**: suíte do desktop roda como gate antes de fechar cada fase de desenvolvimento.

## Segurança

Postura em camadas, descrita em alto nível:

- **A chave da API de IA nunca chega a nenhum cliente**: toda chamada de IA passa pelo backend.
- **Senhas com hash forte** (Argon2id) e senhas iniciais geradas pelo servidor.
- **Sessões revogáveis no servidor**: sair de fato encerra a sessão no backend, não só no dispositivo.
- **CORS restrito**: o backend só aceita requisições de navegador vindas do domínio oficial do web app.
- **Endurecimento do front web**: política de segurança de conteúdo (CSP), verificação de integridade de scripts de CDN (SRI), proteção contra enquadramento por outros sites e renderização à prova de XSS (nunca HTML dinâmico com dados vindos da API).
- **Fronteira contra prompt injection no backend**: allowlist fixa de ferramentas e validação de schema; o cliente envia o texto cru, sem pré-filtragem que enfraqueceria essa fronteira.
- **Limite de uso por usuário na busca**, aplicado no servidor.
- **Repositório público sem segredos**: backend, credenciais e artefatos de planejamento ficam fora deste repo.

## Funcionalidades

- **Busca em linguagem natural** com entendimento de formação, cargo, localização e busca para terceiros.
- **Busca com perfil** em um clique, com a IA completando o contexto a partir da formação salva.
- **Perfil completo**: escolaridade cumulativa, formações, mobilidade, formação futura e currículo.
- **Resultados em cards**: título, localização (UF · região), cargos compatíveis em chips, prazo de inscrição, link da notícia com botão copiar e badge NOVO.
- **Exportação em PDF** (desktop e web) com o mesmo padrão visual dos cards.
- **Tema claro/escuro** com alternância ao vivo nos dois clientes.
- **Tutorial embutido** ("Como pesquisar") idêntico no desktop e no web.
- **Administração de usuários**: criar conta com senha forte gerada, copiar senha, renomear, reativar e excluir, com proteções contra o admin se trancar fora da própria conta.

## Rodando localmente

### Desktop

```bash
cd desktop
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

### Web app

O site publicado é montado pelo workflow em `.github/workflows/pages.yml`. Para pré-visualizar localmente, monte a mesma estrutura (homepage na raiz + `/Login` + `/App` + `/shared`) e sirva com qualquer servidor estático, por exemplo `python -m http.server`.

Ambos os clientes se conectam a uma instância do backend (repositório privado).

### Suíte E2E

```bash
cd e2e
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest -m "not costly"   # subset barato: login, perfil, admin
pytest                    # suíte completa, inclui busca real e PDF (custa tokens de IA)
```

Requer `.env` com credenciais de uma conta de teste dedicada — veja `e2e/.env.example` e `e2e/README.md`.

## Status e licença

Projeto em desenvolvimento ativo. Acesso restrito a convite.

Licenciado sob [PolyForm Noncommercial 1.0.0](LICENSE) — uso não comercial permitido.
