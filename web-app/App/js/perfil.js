"use strict";

document.addEventListener("alpine:init", () => {
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

  const MMAAAA_RE = /^(0[1-9]|1[0-2])\/(\d{4})$/;

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
    curriculoStatus: "",

    salvoFeedback: false,

    carregando: false,
    salvando: false,
    carregarErro: "",
    salvarErro: "",
    dataFuturaErro: "",

    _adjusting: false,

    async init() {
      this.carregando = true;
      try {
        const perfil = await window.cfApi.getProfile();
        this._deBackend(perfil);
      } catch (err) {
        this.carregarErro = (err && err.detail) || "Não foi possível carregar o perfil.";
      } finally {
        this.carregando = false;
      }
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

    async buscarCep() {
      const digitos = (this.cep.match(/\d/g) || []).join("");
      if (digitos.length !== 8) {
        this.cepStatus = "Informe um CEP com 8 dígitos.";
        return;
      }
      this.cepStatus = "Buscando CEP...";
      try {
        const data = await window.cfApi.lookupCep(digitos);
        this.cidade = data.cidade || this.cidade;
        this.uf = data.uf || this.uf;
        this.cepStatus = "";
      } catch (err) {
        this.cepStatus = (err && err.detail) || "Não foi possível consultar o CEP.";
      }
    },

    async anexarCurriculo(event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      const ext = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
      this.curriculoStatus = "Extraindo texto...";
      try {
        let texto;
        if (ext === ".txt") {
          texto = await file.text();
        } else if (ext === ".pdf") {
          const buf = await file.arrayBuffer();
          texto = await window.cfPdfJs.extrairTexto(buf);
        } else {
          this.curriculoStatus = "Formato não suportado. Envie um PDF ou um TXT.";
          return;
        }
        texto = this._normalizarCurriculo(texto);
        if (!texto) {
          this.curriculoStatus = ext === ".pdf"
            ? "Não encontrei texto nesse PDF (parece ser digitalizado/imagem). Cole o texto do currículo manualmente."
            : "O arquivo está vazio.";
          return;
        }
        this.curriculoTexto = texto;
        this.curriculoNomeArquivo = file.name;
        this.curriculoStatus = "";
      } catch (e) {
        this.curriculoStatus = "Não consegui ler esse arquivo. Tente outro ou cole o texto.";
      }
    },

    _normalizarCurriculo(texto) {
      return texto.split(/\r?\n/).map((l) => l.trim()).filter(Boolean).join("\n").trim();
    },

    _mmaaaaParaIso(texto) {
      const t = (texto || "").trim();
      if (!t) return null;
      const m = MMAAAA_RE.exec(t);
      if (!m) {
        throw new Error("Data de formação inválida. Use MM/AAAA, por exemplo 12/2027.");
      }
      return `${m[2]}-${m[1]}`;
    },

    _isoParaMmaaaa(iso) {
      if (!iso || iso.length !== 7 || iso[4] !== "-") return "";
      return `${iso.slice(5)}/${iso.slice(0, 4)}`;
    },

    _paraBackend() {
      return {
        graduacao: this.niveis.superior ? (this.cursos.superior || null) : null,
        tecnico: this.niveis.tecnico ? (this.cursos.tecnico || null) : null,
        pos_graduacao: this.niveis.pos ? (this.cursos.pos || null) : null,
        escolaridade: ["fundamental", "medio", "tecnico", "superior", "pos"]
          .filter((n) => this.niveis[n]).join(",") || null,
        formacao_futura: this.formacaoFutura || null,
        data_formacao_futura: this._mmaaaaParaIso(this.dataFutura),
        cep: this.cep || null,
        uf: this.uf || null,
        cidade: this.cidade || null,
        mobilidade: this.mobilidade || null,
        areas_interesse: this.areasInteresse || null,
        curriculo: this.curriculoTexto || null,
      };
    },

    _deBackend(perfil) {
      const niveis = new Set((perfil.escolaridade || "").split(",").map((s) => s.trim()).filter(Boolean));
      this.niveis = {
        fundamental: niveis.has("fundamental"),
        medio: niveis.has("medio"),
        tecnico: niveis.has("tecnico"),
        superior: niveis.has("superior"),
        pos: niveis.has("pos"),
      };
      this.cursos = {
        tecnico: perfil.tecnico || "",
        superior: perfil.graduacao || "",
        pos: perfil.pos_graduacao || "",
      };
      this.formacaoFutura = perfil.formacao_futura || "";
      this.dataFutura = this._isoParaMmaaaa(perfil.data_formacao_futura);
      this.cep = perfil.cep || "";
      this.cidade = perfil.cidade || "";
      this.uf = perfil.uf || "";
      this.mobilidade = perfil.mobilidade || "";
      this.areasInteresse = perfil.areas_interesse || "";
      this.curriculoTexto = perfil.curriculo || "";
      this.curriculoNomeArquivo = this.curriculoTexto ? "Currículo salvo" : "";
    },

    async salvar() {
      this.dataFuturaErro = "";
      this.salvarErro = "";
      let payload;
      try {
        payload = this._paraBackend();
      } catch (e) {
        this.dataFuturaErro = e.message;
        return;
      }
      this.salvando = true;
      try {
        const salvo = await window.cfApi.updateProfile(payload);
        this._deBackend(salvo);
        this.salvoFeedback = true;
        setTimeout(() => {
          this.salvoFeedback = false;
          window.dispatchEvent(new CustomEvent("cf-perfil-salvo"));
        }, 1200);
      } catch (err) {
        this.salvarErro = (err && err.detail) || "Não foi possível salvar o perfil. Tente novamente.";
      } finally {
        this.salvando = false;
      }
    },
  }));
});
