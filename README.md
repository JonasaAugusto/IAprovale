# IAprovale (Concurso Finder)

Buscador de concursos públicos privado e por convite, com IA. O usuário descreve em linguagem natural o que procura (ex: *"concurso na área de saúde com graduação em enfermagem"*) e o sistema filtra automaticamente apenas os concursos com inscrições abertas que aceitam a formação informada, entregando o resultado dentro do app — com exportação em PDF.

**Versão atual:** v1.2.0 (app desktop Windows)

## Como funciona

1. Login em uma conta previamente criada por um administrador (sem autocadastro público).
2. A pessoa descreve o que procura em português natural — ou busca direto com o perfil salvo.
3. O backend traduz a busca com IA, consulta a fonte oficial de concursos (MCP da PCI Concursos) e filtra pelos resultados com inscrições abertas compatíveis com a formação.
4. Os resultados aparecem em cards com localização, cargos compatíveis e prazo. Concursos ainda não vistos ganham o badge **NOVO** — os já vistos continuam aparecendo sempre.
5. É possível gerar um PDF com o mesmo padrão visual dos cards, visualizar, salvar ou apagar.

## Estrutura do repositório

```
desktop/    Cliente desktop (Windows) — login, busca, resultados, perfil e administração
web-app/    Site institucional (homepage) e base do futuro web app
```

O backend (FastAPI) vive em um repositório privado separado e é deployado no Render — este repositório público contém apenas os clientes.

## Tecnologias

### Cliente desktop
- **Python 3** + **PySide6 (Qt 6)** — interface nativa Windows
- **PySide6-Fluent-Widgets** — componentes com visual Fluent Design (cards, InfoBar, tema claro/escuro)
- **fpdf2** — geração de PDF 100% Python (sem DLLs externas, empacota limpo no `.exe`)
- **pypdf** — extração local de texto de currículos em PDF
- **PyInstaller** — empacotamento em executável Windows standalone
- **pytest** — suíte de testes automatizados do cliente

### Backend (repositório privado)
- **FastAPI** + **Uvicorn** — API REST assíncrona
- **DeepSeek** (via SDK OpenAI-compatível) — tradução da busca em linguagem natural para parâmetros estruturados
- **MCP oficial da PCI Concursos** (JSON-RPC via httpx) — fonte de dados de concursos, sem scraping
- **SQLModel / SQLAlchemy** + **Postgres (Neon)** — persistência de usuários, perfis e concursos já vistos
- **PyJWT** + **pwdlib (Argon2id)** — sessões e hash de senhas
- **Render.com** — hospedagem do backend

## Estratégias de desenvolvimento

- **Backend client-agnóstico**: toda a lógica pesada (IA, MCP, filtros, dedup) vive na API — o desktop de hoje e o web app de amanhã consomem os mesmos endpoints.
- **Segurança em camadas**: a chave da API de IA nunca chega ao cliente; senhas com Argon2id; sessões via JWT; a fronteira contra prompt injection é o allowlist fixo de tools + validação de schema no backend (o cliente envia o texto cru, sem pré-filtragem que enfraqueceria essa fronteira).
- **Acesso privado por convite**: sem autocadastro — só o admin cria, renomeia, reativa e exclui contas.
- **Testes como guarda de regressão**: mais de 130 testes no cliente desktop cobrindo login, busca, perfil, PDF e admin.
- **Repositório público sem segredos**: o backend e os artefatos de planejamento ficam fora do repo público.

## Otimização

- **UI nunca trava**: login, busca e chamadas de rede rodam fora da thread da interface (`run_in_background`) — buscas de 30–90s não congelam a janela.
- **Cold start tratado**: o backend no free tier hiberna após inatividade; o app mostra "Conectando ao servidor..." e o auto-login preserva a sessão em queda de rede.
- **Startup rápido do `.exe`**: imports pesados (PDF, config) são lazy — carregam só quando usados.
- **Economia de tokens de IA**: a extração de texto do currículo é feita localmente com `pypdf`, sem gastar chamada de IA; o modelo usado é o não-thinking (mais barato e suficiente para estruturar a busca).
- **Dedup sem esconder nada**: concursos já vistos são apenas marcados (badge NOVO nos inéditos) — a busca sempre retorna novos **e** antigos.

## Funcionalidades

- **Busca em linguagem natural** — frases completas em português; a IA entende formação, cargo, cidade/estado/região e busca para terceiros ("concurso para minha esposa, que é engenheira").
- **Busca com perfil** — um clique busca "na minha área" usando a formação salva; digitou algo, a IA completa o resto com o perfil.
- **Perfil completo** — escolaridade, formações cumulativas, mobilidade e currículo (anexo PDF/TXT com extração automática de texto).
- **Resultados em cards** — título, localização (UF · região), cargos compatíveis em chips, prazo de inscrição, link da notícia com botão copiar e badge NOVO.
- **Exportação em PDF** — mesmo padrão visual dos cards (localização, cargos compatíveis, badge NOVO, novos primeiro), com popup de confirmação e ações Visualizar / Salvar / Apagar.
- **Tema claro/escuro** — alternância ao vivo, sem perder os resultados na tela.
- **Tutorial embutido** — botão "Como pesquisar" com guia de uso da busca.
- **Administração de usuários** — criar conta com senha forte gerada, copiar senha, renomear, reativar e excluir.
- **Auto-login resiliente** — sessão persistida com reconexão tolerante a falhas de rede.

## Futuras melhorias

### Web app
O site em GitHub Pages evoluirá de homepage institucional (já em `web-app/homepage/`) para um **web app completo**, reusando exatamente o mesmo backend do desktop — mesma conta, mesmo perfil, mesma busca, acessível de qualquer navegador sem instalar nada.

## Futuras versões

| Versão | Escopo |
|--------|--------|
| **v1.3.0** | Currículo na busca: com um toggle visível ("Usar meu currículo"), a IA lê o currículo salvo no perfil e extrai formações, experiências e áreas que somam na pesquisa — especialmente em buscas curtas ou só com localização. |
| **v1.4.0** | Formação futura: informe sua graduação em andamento e a data de formatura — concursos compatíveis com a formação futura aparecem com a nota "aberto para formação futura" (no app e no PDF), e só quando a data coincide com o prazo. |
| **v1.5.0** | Auto-update nível 1: o app consulta a API de releases do GitHub e avisa quando existe versão nova (sem substituir o binário automaticamente). |

## Rodando localmente

```bash
cd desktop
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

O app se conecta a uma instância do backend (ver `desktop/app/config.py` para a URL configurada).

## Status e licença

Projeto em desenvolvimento ativo. Acesso restrito a convite.

Licenciado sob [PolyForm Noncommercial 1.0.0](LICENSE) — uso não comercial permitido.
