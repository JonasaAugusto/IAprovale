/* ==========================================================================
   IAprovale — /App Busca tab store (Alpine.js CSP build)
   Registered on alpine:init so the component exists before Alpine scans the
   DOM. Fully mocked (zero network calls): a static results array + local
   formatters mirroring the desktop's ConcursoCard/BuscaTab formatters
   (desktop/app/ui/concurso_card.py, desktop/app/ui/busca_tab.py) so the
   web card anatomy has parity with the desktop app.
   ========================================================================== */

"use strict";

document.addEventListener("alpine:init", () => {
  // Tutorial "Como pesquisar" (WBUSCA-04) — copy reproduced VERBATIM from
  // desktop/app/ui/busca_tab.py::_AJUDA_SECTIONS (v1.5.2 modernized text,
  // the parity reference for the web).
  const AJUDA_SECTIONS = [
    {
      heading: null,
      body:
        'Escreva do seu jeito, como se estivesse pedindo pra um amigo. Exemplos: ' +
        '"concurso de enfermagem em SP", "vaga de professor de matemática", ' +
        '"técnico em informática perto de mim".',
    },
    {
      heading: "FORMAÇÃO OU CARGO",
      body:
        'Diga o cargo ou a área — "enfermagem", "técnico em edificações", ' +
        '"analista de sistemas". Não citou nada? O sistema usa a formação salva no seu perfil.',
    },
    {
      heading: "ONDE BUSCAR",
      body:
        '- Brasil todo: não cite local.\n' +
        '- Um estado: "em SP", "na Bahia".\n' +
        '- Uma cidade: "em Campinas, SP".\n' +
        '- Uma região: "no Nordeste", "no Sul do país".',
    },
    {
      heading: "BUSCANDO PARA OUTRA PESSOA",
      body:
        'Só diga quem é: "concurso para minha esposa, que é engenheira", ' +
        '"meu amigo é professor, tem vaga pra ele?". A formação citada é da outra ' +
        'pessoa — seu perfil salvo não muda.',
    },
    {
      heading: "CONCURSOS DE PROFESSOR",
      body: 'Cite "professor" ou "docente" pra focar em vagas de magistério.',
    },
    {
      heading: "COMBINE TUDO",
      body:
        'Junte formação + local numa frase só: "vaga de enfermeiro em Recife", ' +
        '"técnico em edificações no Paraná", "concursos de saúde no Nordeste". ' +
        'Frases naturais e específicas dão os melhores resultados — o sistema já ' +
        'filtra só o que tem inscrições abertas e aceita a sua formação.',
    },
  ];

  // Mock concursos (pt-BR, realistic) — demonstrates every card feature:
  // NOVO badge, localização, chips com "+N outros", nota de formação futura,
  // prazo DD/MM/AAAA, prazo não-ISO passando intacto, e copiar link.
  const MOCK_RESULTS = [
    {
      titulo: "Prefeitura de São João del-Rei — Concurso Público 2026",
      is_new: true,
      uf: "MG",
      regiao: "sudeste",
      cargos_compativeis: [
        "Enfermeiro",
        "Técnico de Enfermagem",
        "Médico",
        "Agente Comunitário de Saúde",
        "Fisioterapeuta",
        "Nutricionista",
        "Farmacêutico",
      ],
      futuro_match: true,
      data_formacao_futura: "2027-12",
      datas: { fim: "2026-08-15" },
      noticia: { link: "https://www.pciconcursos.com.br/concurso/prefeitura-de-sao-joao-del-rei-mg-2026/" },
      expanded: false,
      copied: false,
    },
    {
      titulo: "Tribunal Regional Federal da 1ª Região — Analista Judiciário",
      is_new: false,
      uf: "BA",
      regiao: "nordeste",
      cargos: [
        "Analista Judiciário — Área Judiciária",
        "Analista Judiciário — Área Administrativa",
        "Técnico Judiciário",
      ],
      futuro_match: false,
      data_formacao_futura: null,
      datas: { fim: "2026-09-01" },
      noticia: { link: "https://www.pciconcursos.com.br/concurso/trf-1a-regiao-analista-judiciario-2026/" },
      expanded: false,
      copied: false,
    },
    {
      titulo: "Secretaria de Educação de Fortaleza — Professor",
      is_new: true,
      uf: "CE",
      regiao: "nordeste",
      cargos: ["Professor de Matemática", "Professor de Português"],
      futuro_match: false,
      data_formacao_futura: null,
      datas: { fim: "não informado" },
      noticia: { link: "https://www.pciconcursos.com.br/concurso/secretaria-educacao-fortaleza-professor-2026/" },
      expanded: false,
      copied: false,
    },
  ];

  Alpine.data("buscaTab", () => ({
    query: "",
    loading: false,
    isEmpty: false,
    tutorialOpen: false,
    ajudaSections: AJUDA_SECTIONS,
    results: MOCK_RESULTS,

    // Mock search dispatch — no network call, just demonstrates the
    // skeleton loading state for ~900ms before re-showing the same mock
    // results (this plan is fully mocked; real wiring lands in Phase 7+).
    buscar() {
      this._simular();
    },

    buscarComPerfil() {
      this._simular();
    },

    _simular() {
      this.loading = true;
      setTimeout(() => {
        this.loading = false;
      }, 900);
    },

    // "AAAA-MM-DD" -> "DD/MM/AAAA"; qualquer outro formato passa intacto.
    // Espelha _fmt_prazo em concurso_card.py.
    prazoBR(iso) {
      const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
      if (!m) return iso;
      const [, ano, mes, dia] = m;
      return `${dia}/${mes}/${ano}`;
    },

    // "AAAA-MM" -> "MM/AAAA". Espelha _fmt_data_futura em concurso_card.py.
    dataFuturaBR(iso) {
      if (!iso || iso.length !== 7 || iso[4] !== "-") return "";
      return `${iso.slice(5)}/${iso.slice(0, 4)}`;
    },

    // uf.toUpperCase() + " · " + Título-case regiao. Espelha _fmt_localizacao.
    localizacao(c) {
      const uf = (c.uf || "").trim().toUpperCase();
      const regiaoRaw = (c.regiao || "").trim();
      const regiao = regiaoRaw ? regiaoRaw.charAt(0).toUpperCase() + regiaoRaw.slice(1).toLowerCase() : "";
      if (uf && regiao) return `${uf} · ${regiao}`;
      return uf || regiao || "";
    },

    cargos(c) {
      return c.cargos_compativeis || c.cargos || [];
    },

    cargosLabel(c) {
      return c.cargos_compativeis ? "Cargos compatíveis:" : "Cargos:";
    },

    cargosVisiveis(c) {
      const all = this.cargos(c);
      return c.expanded || all.length <= 5 ? all : all.slice(0, 5);
    },

    overflow(c) {
      return this.cargos(c).length - 5;
    },

    toggleCargos(c) {
      c.expanded = !c.expanded;
    },

    textoFuturo(c) {
      const base = "Aberto para formação futura — quando você se formar";
      const data = this.dataFuturaBR(c.data_formacao_futura);
      return data ? `${base} (${data})` : base;
    },

    // PITFALLS.md Pitfall 11: writeText() must be the FIRST synchronous
    // statement in the click handler, before any await, or the browser can
    // lose the "user gesture" context and silently reject the call.
    copiar(c) {
      navigator.clipboard.writeText(c.noticia.link);
      c.copied = true;
      setTimeout(() => {
        c.copied = false;
      }, 1500);
    },
  }));
});
