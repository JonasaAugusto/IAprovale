# IAprovale (Concurso Finder)

Buscador de concursos públicos privado e por convite, com IA. O usuário descreve em linguagem natural o que procura (ex: *"concurso na área de saúde com graduação em enfermagem"*) e o sistema filtra automaticamente apenas os concursos com inscrições abertas que aceitam a formação informada.

**Versões:** desktop **v1.5.1** (Windows) · web app **v2.0 em desenvolvimento** (GitHub Pages)

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
5. No desktop, é possível gerar um PDF com o mesmo padrão visual dos cards.

## Estrutura do repositório

```
desktop/    Cliente desktop (Windows): login, busca, resultados, perfil e administração
web-app/    Homepage institucional + web app (rotas /Login e /App)
```

O backend (FastAPI) vive em um repositório privado separado e é deployado no Render. Este repositório público contém apenas os clientes.

## Arquitetura compartilhada (backend único)

Os dois apps são clientes do **mesmo backend**: mesma conta, mesmo perfil, mesma busca. Tudo nesta seção vale simultaneamente para desktop e web.

### Backend (repositório privado)

API REST assíncrona em **FastAPI + Uvicorn**, organizada em módulos independentes:

| Módulo | Responsabilidade |
|--------|------------------|
| `auth` | Login/logout, sessões e administração de usuários (criar, renomear, ativar/desativar, excluir) |
| `profile` | Perfil de formação do usuário (escolaridade, formações, mobilidade, currículo) |
| `search` | Pipeline da busca: IA traduz a frase → consulta ao MCP da PCI Concursos → filtros de compatibilidade → marcação de já vistos, com limite de uso por usuário |
| `cep` | Consulta de CEP para preencher cidade/UF no perfil |
| `core` / `db` | Configuração, dependências de autenticação e modelos de dados (SQLModel + Postgres/Neon) |

Tecnologias do backend: **DeepSeek** (via SDK OpenAI-compatível) para estruturar a busca, **MCP oficial da PCI Concursos** (JSON-RPC via httpx, sem scraping) como fonte de dados, **SQLModel/SQLAlchemy + Postgres (Neon)** para persistência, **Render.com** para hospedagem.

### Fluxos idênticos nos dois clientes

- **Login e sessão**: as mesmas contas funcionam no desktop e no navegador; a sessão é encerrada no servidor ao sair.
- **Busca em linguagem natural**: a IA entende formação, cargo, cidade/estado/região e busca para terceiros ("concurso para minha esposa, que é engenheira").
- **Busca com perfil**: um clique busca "na minha área" usando a formação salva.
- **Dedup sem esconder nada**: concursos já vistos são apenas marcados (badge NOVO nos inéditos); a busca sempre retorna novos e antigos.
- **Cold start tratado**: o backend no free tier hiberna após inatividade; os dois clientes mostram "Conectando ao servidor..." em vez de uma tela parecendo quebrada.
- **Administração**: gestão de usuários exclusiva de contas admin, com revalidação de permissão no servidor a cada operação.

## App Desktop (Windows)

Cliente nativo empacotado em `.exe` standalone. É a versão completa e estável (v1.5.1).

- **Python 3 + PySide6 (Qt 6)** com **PySide6-Fluent-Widgets**: visual Fluent Design, tema claro/escuro ao vivo.
- **Exportação em PDF local** (fpdf2, 100% Python): mesmo padrão visual dos cards, com Visualizar / Salvar / Apagar.
- **Currículo no perfil**: anexo PDF/TXT com extração de texto local (pypdf), sem custo de IA; com um toggle, a IA usa o currículo para enriquecer a busca.
- **Formação futura**: graduação em andamento com data de formatura conta como formação compatível quando o prazo do concurso alcança a data.
- **Sessão persistida com auto-login** resiliente a quedas de rede.
- **Auto-update nível 1**: o app avisa quando existe versão nova no GitHub (sem substituir o binário sozinho).
- **UI nunca trava**: chamadas de rede rodam fora da thread da interface; buscas longas não congelam a janela.
- **PyInstaller** para o executável, imports pesados carregados sob demanda para startup rápido.
- Quase 200 testes automatizados cobrindo login, busca, perfil, PDF e admin.

## App Web (GitHub Pages)

Web app em construção (milestone v2.0) que reusa o mesmo backend do desktop, acessível de qualquer navegador sem instalar nada.

- **Site 100% estático, sem build step**: HTML + CSS puro + JavaScript vanilla, publicado no GitHub Pages por workflow do GitHub Actions.
- **Alpine.js (build CSP)** para reatividade das telas, carregado de CDN com verificação de integridade.
- **Design system próprio** (tokens de cor/tipografia, tema claro/escuro persistente) com paridade visual ao desktop: verde no claro, dourado no escuro, fontes Inter/Fraunces.
- **Rotas**: homepage institucional na raiz, `/Login` e `/App` (abas Busca, Admin e tela de Perfil).
- **Sessão só no navegador**: o login vale para a aba atual e expira sozinho após um período de inatividade; fechar o navegador encerra a sessão. Sem "continuar logado" automático, por decisão de design.
- **Estado atual**: login real contra o backend concluído; as telas de Busca, Perfil e Admin já existem com dados de demonstração e serão ligadas ao backend nas próximas fases (busca real, perfil real, PDF no navegador, admin real).

## Decisões de design

- **Backend client-agnóstico**: toda a lógica pesada (IA, MCP, filtros, dedup) vive na API; qualquer cliente novo consome os mesmos endpoints sem retrabalho.
- **Fonte oficial, sem scraping**: os dados vêm do servidor MCP da própria PCI Concursos, estruturados.
- **Acesso privado por convite**: sem autocadastro; só o admin cria e gerencia contas.
- **Web sem framework nem bundler**: menos superfície de ataque, deploy trivial em hospedagem estática gratuita e compatibilidade com política de segurança de conteúdo rígida.
- **Paridade visual entre clientes**: cards, badges, textos de ajuda e mensagens de erro seguem o mesmo padrão no desktop e no web.
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
- **Exportação em PDF** (desktop) com o mesmo padrão visual dos cards.
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

## Status e licença

Projeto em desenvolvimento ativo. Acesso restrito a convite.

Licenciado sob [PolyForm Noncommercial 1.0.0](LICENSE) — uso não comercial permitido.
