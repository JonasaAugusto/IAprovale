# Concurso Finder

Buscador de concursos públicos privado e por convite. O usuário descreve em linguagem natural o que procura (ex: *"concurso na área de saúde com graduação em enfermagem"*) e o sistema filtra automaticamente apenas os concursos com inscrições abertas que aceitam a formação informada, entregando o resultado dentro do app.

## Como funciona

1. Login em uma conta previamente criada por um administrador (sem autocadastro público).
2. A pessoa descreve o que procura em português natural.
3. O backend traduz a busca, consulta a fonte de dados de concursos e filtra pelos resultados compatíveis com a formação salva no perfil.
4. Resultados novos (ainda não vistos) ficam destacados; é possível exportar em PDF ou copiar o link da notícia oficial.

## Estrutura do repositório

```
backend/    API (FastAPI) — autenticação, perfis, orquestração de busca e persistência
desktop/    Cliente desktop (Windows) — login, busca, resultados e administração de usuários
web-app/    Site institucional
```

## Cliente desktop

App desktop feito em Python/Tkinter. Login, busca e chamadas de rede rodam em background — a janela nunca trava enquanto uma busca está em andamento.

### Rodando localmente

```bash
cd desktop
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

O app se conecta a uma instância do backend (ver `desktop/app/config.py` para a URL configurada).

## Status

Projeto em desenvolvimento ativo. Acesso é restrito a convite.
