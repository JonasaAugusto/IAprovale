/* ==========================================================================
   IAprovale — /App Perfil form store (Alpine.js CSP build)
   Registered on alpine:init so the component exists before Alpine scans the
   DOM. Fully mocked (zero network calls): reproduces the desktop's
   PerfilDialog anatomy (desktop/app/ui/perfil_dialog.py) — cumulative
   escolaridade checkboxes, MM/AAAA live mask, mock CEP fill, mobilidade,
   áreas de interesse and currículo attach. Salvar is a no-op close (real
   persistence lands in Phase 7+).

   Opening: this component lives in its own x-data scope (#perfil-modal),
   separate from appShell's x-data. The header's "Perfil" button dispatches
   a window CustomEvent ($dispatch('open-perfil')) that this component
   listens for (x-on:open-perfil.window) — the only way two sibling Alpine
   CSP components can talk to each other without a shared store.
   ========================================================================== */

"use strict";

document.addEventListener("alpine:init", () => {
  const UFS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
  ];

  // (rótulo, valor) — valor "" ao invés de null (mock/HTML <select> friendly;
  // espelha o índice 0 = "não informado" de _MOBILIDADE).
  const MOBILIDADE = [
    { label: "Não informado", value: "" },
    { label: "Só na minha cidade", value: "local" },
    { label: "No meu estado", value: "estado" },
    { label: "Qualquer lugar", value: "qualquer" },
  ];

  // Mock CEP -> {cidade, uf} (sem rede — fase totalmente mockada).
  const MOCK_CEPS = {
    "36301000": { cidade: "São João del-Rei", uf: "MG" },
    "01310100": { cidade: "São Paulo", uf: "SP" },
    "40010000": { cidade: "Salvador", uf: "BA" },
    "60010000": { cidade: "Fortaleza", uf: "CE" },
    "70040010": { cidade: "Brasília", uf: "DF" },
  };

  Alpine.data("perfilForm", () => ({
    open: false,

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

    _adjusting: false, // guarda contra reentrância, espelha self._adjusting

    // Mantém o conjunto de níveis coerente (superior/tecnico/pos -> medio ->
    // fundamental) e habilita/desabilita o campo "qual?" correspondente.
    // Espelha _on_nivel_toggled em perfil_dialog.py.
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

    // Máscara de digitação MM/AAAA (v1.5.2 do desktop): filtra não-dígitos,
    // limita a 6 dígitos, insere "/" após os 2 primeiros. Espelha
    // _aplicar_mascara_data em perfil_dialog.py. Ligado ao evento `input`
    // do campo de data de formação.
    maskData(event) {
      const digitos = (event.target.value.match(/\d/g) || []).join("").slice(0, 6);
      this.dataFutura = digitos.length < 2 ? digitos : `${digitos.slice(0, 2)}/${digitos.slice(2)}`;
    },

    // Mock: preenche cidade/UF a partir de um mapa fixo de CEPs conhecidos —
    // sem chamada de rede nesta fase (o backend real de CEP é Fase 7+).
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

    // Mock: apenas mostra o nome do arquivo escolhido — extração real de
    // texto (pdfjs) é Fase 9.
    anexarCurriculo(event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      this.curriculoNomeArquivo = file.name;
    },

    salvar() {
      // Mock: fecha sem persistir — a chamada real a PUT /profile é Fase 7+.
      this.open = false;
    },

    cancelar() {
      this.open = false;
    },
  }));
});
