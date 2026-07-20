"use strict";

document.addEventListener("alpine:init", () => {
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

  Alpine.data("buscaTab", () => ({
    query: "",
    loading: false,
    isEmpty: false,
    tutorialOpen: false,
    ajudaSections: AJUDA_SECTIONS,
    results: [],

    usarCurriculo: false,
    curriculoDisponivel: true,
    erro: "",
    emptyMessage: "",
    _PERFIL_QUERY: "concursos na minha área",

    _tutorialTrigger: null,

    init() {
      window.cfApi.getProfile().then((profile) => {
        this.curriculoDisponivel = !!(profile && profile.curriculo && profile.curriculo.trim());
      }).catch(() => {
      });
    },

    abrirTutorial() {
      const el = document.activeElement;
      this._tutorialTrigger = el && typeof el.focus === "function" ? el : null;
      this.tutorialOpen = true;
      this.$nextTick(() => window.cfModalAberto("tutorial-dialog"));
    },

    fecharTutorial() {
      if (!this.tutorialOpen) return;
      this.tutorialOpen = false;
      const trigger = this._tutorialTrigger;
      this._tutorialTrigger = null;
      this.$nextTick(() => window.cfModalFechado(trigger));
    },

    buscar() {
      this._dispatch(this.query);
    },

    buscarComPerfil() {
      const q = (this.query || "").trim() || this._PERFIL_QUERY;
      this._dispatch(q);
    },

    async _dispatch(query) {
      this.erro = "";
      this.isEmpty = false;
      this.loading = true;
      try {
        const resp = await window.cfApi.search(query, this.usarCurriculo);
        this.results = resp.results || [];
        this.isEmpty = !!resp.is_empty;
        this.emptyMessage = resp.message || "";
      } catch (err) {
        this.erro = (err && err.detail) || "Não foi possível completar a busca. Tente novamente.";
      } finally {
        this.loading = false;
      }
    },

    prazoBR(iso) {
      const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
      if (!m) return iso;
      const [, ano, mes, dia] = m;
      return `${dia}/${mes}/${ano}`;
    },

    dataFuturaBR(iso) {
      if (!iso || iso.length !== 7 || iso[4] !== "-") return "";
      return `${iso.slice(5)}/${iso.slice(0, 4)}`;
    },

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

    linkSeguro(c) {
      const link = c?.noticia?.link || "";
      return /^https?:\/\//i.test(link) ? link : "";
    },

    copiar(c) {
      navigator.clipboard.writeText(c.noticia.link).then(() => {
        c.copied = true;
        setTimeout(() => {
          c.copied = false;
        }, 1500);
      }).catch(() => {
      });
    },
  }));
});
