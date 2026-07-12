# Concurso Finder — Homepage

Página estática de apresentação do **Concurso Finder** — buscador privado de concursos públicos com busca em linguagem natural (IA), acesso por convite.

Sem build, sem frameworks, sem npm: apenas HTML, CSS e JavaScript puros. Única dependência externa: Google Fonts (via CDN).

## Estrutura

```
index.html      — página completa (hero, como funciona, quem sou eu, modais, footer)
css/style.css   — todo o estilo (temas claro/verde e escuro/dourado via CSS custom properties)
js/main.js      — tema com persistência, modais acessíveis, scroll-reveal, formulário
assets/         — reservado para imagens futuras (avatar real, favicon etc.)
```

## Como abrir localmente

Basta abrir o `index.html` no navegador (duplo clique ou arrastar para uma aba). Funciona direto via `file://`.

## Antes de publicar — pontos a editar

1. **Link de login** — em `js/main.js`, logo no topo, troque o valor de `LOGIN_REDIRECT_URL` (procure pelo comentário `// COLOQUE O CAMINHO OU LINK AQUI`).
2. **Bio** — em `index.html`, substitua o marcador `[ESCREVA AQUI SUA TRAJETÓRIA/BIO]` pelo seu texto.
3. **Links sociais** — em `index.html`, procure o comentário `<!-- LINKS REAIS: ... -->` e troque os `href="#"` de LinkedIn, GitHub e Portfólio.
4. **Formulário de contato** — já aponta para um endpoint real em produção (`submit-form.com`). Se quiser um formulário dedicado, troque a constante `CONTACT_FORM_ACTION` em `js/main.js`.

## Deploy no GitHub Pages

1. Crie um repositório no GitHub e envie estes arquivos para a raiz:
   ```bash
   git init
   git add .
   git commit -m "Homepage Concurso Finder"
   git branch -M main
   git remote add origin https://github.com/SEU-USUARIO/SEU-REPO.git
   git push -u origin main
   ```
2. No GitHub: **Settings → Pages → Build and deployment** → Source: *Deploy from a branch* → Branch: `main`, pasta `/ (root)` → **Save**.
3. Em ~1 minuto a página fica disponível em `https://SEU-USUARIO.github.io/SEU-REPO/`.
