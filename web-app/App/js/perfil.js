/* ==========================================================================
   IAprovale — /App Perfil form store (Alpine.js CSP build)
   Registered on alpine:init so the component exists before Alpine scans the
   DOM. Fully mocked (zero network calls): reproduces the desktop's
   PerfilDialog anatomy (desktop/app/ui/perfil_dialog.py), including
   cumulative escolaridade checkboxes, MM/AAAA live mask, mock CEP fill,
   mobilidade, áreas de interesse and currículo attach. Salvar persists the
   form to localStorage (mock save, see PERFIL_MOCK_KEY below); real
   persistence via PUT /profile lands in Phase 7+.

   View, not modal: #panel-perfil is a main-view panel, same pattern as
   #panel-busca/#panel-admin (x-show="tab === 'perfil'", toggled by the
   header's "Perfil" button via appShell.openPerfil()). This component's
   x-data is nested inside appShell's scope (no shared store needed); Alpine
   resolves `tab`/`voltarDoPerfil()` from the parent scope for any property
   not defined here, the same mechanism buscaTab/adminTab already rely on.
   ========================================================================== */

"use strict";

document.addEventListener("alpine:init", () => {
  // Chave de localStorage do salvamento MOCK do perfil (v1 desta fase). A
  // persistência REAL (PUT /profile no backend) é Fase 7+ - isto só
  // sobrevive a reload/navegação NESTE navegador, sem rede.
  const PERFIL_MOCK_KEY = "cf-perfil-mock";

  const UFS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
  ];

  // (rótulo, valor), valor "" ao invés de null (mock/HTML <select> friendly;
  // espelha o índice 0 = "não informado" de _MOBILIDADE).
  const MOBILIDADE = [
    { label: "Não informado", value: "" },
    { label: "Só na minha cidade", value: "local" },
    { label: "No meu estado", value: "estado" },
    { label: "Qualquer lugar", value: "qualquer" },
  ];

  // Mock CEP -> {cidade, uf} (sem rede, fase totalmente mockada).
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

    salvoFeedback: false, // mostra "Perfil salvo" por um tempo após salvar()

    _adjusting: false, // guarda contra reentrância, espelha self._adjusting

    // Alpine chama init() automaticamente quando o componente é montado (uma
    // vez, no carregamento da página) - re-hidrata o form a partir do último
    // salvamento mock em localStorage, se houver. Como #panel-perfil usa
    // x-show (não é desmontado ao trocar de aba), isto cobre "reidrata ao
    // abrir o Perfil": os dados já estão carregados antes do usuário navegar
    // até lá.
    init() {
      this._rehidratar();
    },

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
      // Escreve o valor mascarado no DOM de forma síncrona: se o novo valor
      // normalizado for IGUAL ao estado atual (ex: backspace de "12/" pra
      // "12", ambos normalizam pra "12/"), a atribuição acima é no-op pra
      // reatividade do Alpine e o efeito do x-bind:value nunca re-executa —
      // o DOM ficaria mostrando "12" com o estado em "12/". Mantém input e
      // estado em lockstep mesmo quando o estado não muda.
      event.target.value = this.dataFutura;
    },

    // Mock: preenche cidade/UF a partir de um mapa fixo de CEPs conhecidos,
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

    // Mock: apenas mostra o nome do arquivo escolhido. A extração real de
    // texto (pdfjs) é Fase 9.
    anexarCurriculo(event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      this.curriculoNomeArquivo = file.name;
    },

    // Serializa os campos do form pra um objeto plano, usado tanto por
    // salvar() (persistência mock) quanto por _rehidratar() (leitura).
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

    // Re-hidrata o form a partir do salvamento mock em localStorage. Chamada
    // por init() ao carregar a página; sem efeito se nunca houve um Salvar
    // anterior neste navegador.
    _rehidratar() {
      let salvo = null;
      try {
        const raw = localStorage.getItem(PERFIL_MOCK_KEY);
        if (raw) salvo = JSON.parse(raw);
      } catch (e) {
        salvo = null; // localStorage indisponível/corrompido: mock ignora
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
      // Mock: persiste o form em localStorage (chave "cf-perfil-mock") e
      // mostra feedback de sucesso ("Perfil salvo."). A persistência REAL via
      // PUT /profile (backend, com validação server-side) fica pra Fase 7+ -
      // trocar o corpo do try abaixo por uma chamada httpx/fetch é a única
      // mudança esperada nesse ponto.
      try {
        localStorage.setItem(PERFIL_MOCK_KEY, JSON.stringify(this._coletar()));
      } catch (e) {
        // localStorage indisponível (ex: modo privado bloqueando): mock não
        // persiste, sem impacto de segurança/rede - mostra o feedback mesmo assim.
      }
      this.salvoFeedback = true;
      setTimeout(() => {
        this.salvoFeedback = false;
      }, 2000);
    },
  }));
});
