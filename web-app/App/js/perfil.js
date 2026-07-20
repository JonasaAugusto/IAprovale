"use strict";

document.addEventListener("alpine:init", () => {
  const PERFIL_MOCK_KEY = "cf-perfil-mock";

  const UFS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
  ];

  const MOBILIDADE = [
    { label: "Não informado", value: "" },
    { label: "Só na minha cidade", value: "local" },
    { label: "No meu estado", value: "estado" },
    { label: "Qualquer lugar", value: "qualquer" },
  ];

  const MOCK_CEPS = {
    "36301000": { cidade: "São João del-Rei", uf: "MG" },
    "01310100": { cidade: "São Paulo", uf: "SP" },
    "40010000": { cidade: "Salvador", uf: "BA" },
    "60010000": { cidade: "Fortaleza", uf: "CE" },
    "70040010": { cidade: "Brasília", uf: "DF" },
  };

  Alpine.data("perfilForm", () => ({
    ufs: UFS,
    mobilidadeOptions: MOBILIDADE,
    mobilidade: "",

    niveis: {
      fundamental: false,
      medio: false,
      tecnico: false,
      superior: false,
      pos: false,
    },
    cursos: {
      tecnico: "",
      superior: "",
      pos: "",
    },

    formacaoFutura: "",
    dataFutura: "",

    cep: "",
    cepStatus: "",
    cidade: "",
    uf: "",

    areasInteresse: "",

    curriculoNomeArquivo: "",
    curriculoTexto: "",

    salvoFeedback: false,

    _adjusting: false,

    init() {
      this.$nextTick(() => this._rehidratar());
    },

    onNivelToggled(nivel) {
      if (this._adjusting) return;
      this._adjusting = true;
      try {
        const marcado = this.niveis[nivel];

        if (marcado) {
          if (nivel === "tecnico" || nivel === "superior" || nivel === "pos") {
            this.niveis.medio = true;
          }
          if (this.niveis.medio) {
            this.niveis.fundamental = true;
          }
        } else {
          if (nivel === "fundamental") {
            this.niveis.medio = false;
            this.niveis.tecnico = false;
            this.niveis.superior = false;
            this.niveis.pos = false;
          } else if (nivel === "medio") {
            this.niveis.tecnico = false;
            this.niveis.superior = false;
            this.niveis.pos = false;
          }
        }

        for (const n of ["tecnico", "superior", "pos"]) {
          if (!this.niveis[n]) {
            this.cursos[n] = "";
          }
        }
      } finally {
        this._adjusting = false;
      }
    },

    maskData(event) {
      const digitos = (event.target.value.match(/\d/g) || []).join("").slice(0, 6);
      this.dataFutura = digitos.length < 2 ? digitos : `${digitos.slice(0, 2)}/${digitos.slice(2)}`;
      event.target.value = this.dataFutura;
    },

    buscarCep() {
      const digitos = (this.cep.match(/\d/g) || []).join("");
      if (digitos.length !== 8) {
        this.cepStatus = "Informe um CEP com 8 dígitos.";
        return;
      }
      const achado = MOCK_CEPS[digitos];
      if (achado) {
        this.cidade = achado.cidade;
        this.uf = achado.uf;
        this.cepStatus = "";
      } else {
        this.cepStatus = "CEP não encontrado (mock).";
      }
    },

    anexarCurriculo(event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      this.curriculoNomeArquivo = file.name;
    },

    _coletar() {
      return {
        niveis: { ...this.niveis },
        cursos: { ...this.cursos },
        formacaoFutura: this.formacaoFutura,
        dataFutura: this.dataFutura,
        cep: this.cep,
        cidade: this.cidade,
        uf: this.uf,
        mobilidade: this.mobilidade,
        areasInteresse: this.areasInteresse,
        curriculoNomeArquivo: this.curriculoNomeArquivo,
        curriculoTexto: this.curriculoTexto,
      };
    },

    _rehidratar() {
      let salvo = null;
      try {
        const raw = localStorage.getItem(PERFIL_MOCK_KEY);
        if (raw) salvo = JSON.parse(raw);
      } catch (e) {
        salvo = null;
      }
      if (!salvo) return;
      this.niveis = { ...this.niveis, ...(salvo.niveis || {}) };
      this.cursos = { ...this.cursos, ...(salvo.cursos || {}) };
      this.formacaoFutura = salvo.formacaoFutura || "";
      this.dataFutura = salvo.dataFutura || "";
      this.cep = salvo.cep || "";
      this.cidade = salvo.cidade || "";
      this.uf = salvo.uf || "";
      this.mobilidade = salvo.mobilidade || "";
      this.areasInteresse = salvo.areasInteresse || "";
      this.curriculoNomeArquivo = salvo.curriculoNomeArquivo || "";
      this.curriculoTexto = salvo.curriculoTexto || "";
    },

    salvar() {
      try {
        localStorage.setItem(PERFIL_MOCK_KEY, JSON.stringify(this._coletar()));
      } catch (e) {
      }
      this.salvoFeedback = true;
      setTimeout(() => {
        this.salvoFeedback = false;
      }, 2000);
    },
  }));
});
