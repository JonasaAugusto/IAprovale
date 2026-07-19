/* ==========================================================================
   IAprovale — /App Admin tab store (Alpine.js CSP build)
   Registered on alpine:init so the component exists before Alpine scans the
   DOM. Fully mocked (zero network calls): reproduces desktop/app/ui/admin_tab.py
   anatomy, including add-user row, accent/case-insensitive "Procurar usuário"
   filter, per-row CRUD actions (Editar nome / Gerar nova senha / Desativar|Reativar /
   Excluir, hidden on the acting admin's own row), and the three mock modals
   (password reveal, rename, destructive/state-changing confirms). Real
   backend wiring (GET/POST/PATCH/DELETE /auth/users) is Phase 7/11; this
   tab's own visibility here is also mock-only (T-06-10 in the plan's threat
   model; real server-side require_admin re-verification is out of scope).
   ========================================================================== */

"use strict";

document.addEventListener("alpine:init", () => {
  // "jonas" é o admin logado nesta sessão mock; Excluir fica oculto na
  // própria linha dele, espelhando `user["user_id"] != self._session.user_id`.
  const ACTING_ADMIN_ID = 1;

  const MOCK_USERS = [
    { user_id: 1, username: "jonas", is_admin: true, is_active: true },
    { user_id: 2, username: "Márcia Nogueira", is_admin: false, is_active: true },
    { user_id: 3, username: "João Silva", is_admin: false, is_active: true },
    { user_id: 4, username: "Ana Paula", is_admin: false, is_active: false },
    { user_id: 5, username: "roberto", is_admin: false, is_active: true },
  ];

  // Senha "gerada" fixa pro mock de revelação (Adicionar usuário / Gerar
  // nova senha), sem chamada de rede nesta fase.
  const MOCK_PASSWORD = "Xk7-Trovao-42Q";

  Alpine.data("adminTab", () => ({
    users: MOCK_USERS.map((u) => ({ ...u })),
    filtro: "",
    erro: "",

    novoUsername: "",
    novoIsAdmin: false,

    // Modal: revelar senha gerada.
    revealOpen: false,
    revealUsername: "",
    revealPassword: "",
    revealCopiado: false,

    // Modal: editar nome (Editar nome).
    renameOpen: false,
    renameUser: null,
    renameValue: "",
    renameErro: "",

    // Modal: confirmação (Desativar/Reativar/Excluir/Gerar nova senha).
    confirmOpen: false,
    confirmTitulo: "",
    confirmCorpo: "",
    confirmTextoBotao: "",
    confirmDestrutivo: false,
    confirmAction: null,

    // --- foco acessível dos modais (contrato em js/app.js) -----------------

    _modalTrigger: null, // gatilho original (foco volta nele ao fechar tudo)

    // Registra o elemento que abriu o modal. Em cadeias de modais
    // (confirmação -> revelar senha), o activeElement no segundo open é um
    // botão DENTRO do modal anterior — nesse caso mantém o gatilho original
    // (o botão da linha do usuário), pra onde o foco deve voltar no fim.
    _registrarTrigger() {
      const el = document.activeElement;
      if (el && typeof el.closest === "function" && el.closest(".modal-backdrop")) return;
      this._modalTrigger = el && typeof el.focus === "function" ? el : null;
    },

    _aoAbrirModal(dialogId) {
      this.$nextTick(() => window.cfModalAberto(dialogId));
    },

    _aoFecharModal() {
      const trigger = this._modalTrigger;
      // cfModalFechado só restaura o foco (e limpa o lock de scroll) quando
      // nenhum outro modal segue visível — cadeias ficam corretas de graça.
      this.$nextTick(() => window.cfModalFechado(trigger));
    },

    // Normaliza pra comparação de filtro: sem acentos, caixa ignorada
    // ("MÁRCOS" -> "marcos"). Espelha _normalizar() em admin_tab.py (que usa
    // unicodedata.normalize("NFKD", ...) + strip de combining marks +
    // casefold()). \p{M} (Unicode property escape, flag "u") casa toda
    // marca de combinação restante após NFKD, evitando listar manualmente
    // o range de code points U+0300-U+036F.
    normalizar(s) {
      return (s || "")
        .normalize("NFKD")
        .replace(/\p{M}/gu, "")
        .toLocaleLowerCase();
    },

    get filtrados() {
      const termo = this.normalizar(this.filtro);
      if (!termo) return this.users;
      return this.users.filter((u) => this.normalizar(u.username).includes(termo));
    },

    isSelf(u) {
      return u.user_id === ACTING_ADMIN_ID;
    },

    // Guard do botão Desativar: mesmo critério do Excluir (oculto na própria
    // linha do admin logado) — sem isso o único admin de um sistema
    // invite-only consegue revogar o próprio acesso (self-lockout). A regra
    // real é reforçada server-side na Fase 7 (PATCH /auth/users).
    podeDesativar(u) {
      return u.is_active && !this.isSelf(u);
    },

    mostrarErro(msg) {
      this.erro = msg;
    },

    limparErro() {
      this.erro = "";
    },

    // --- adicionar usuário ------------------------------------------------

    adicionar() {
      const username = this.novoUsername.trim();
      if (!username) {
        this.mostrarErro("Informe um nome de usuário.");
        return;
      }
      this.limparErro();
      this.users.push({
        user_id: Date.now(),
        username,
        is_admin: this.novoIsAdmin,
        is_active: true,
      });
      this.novoUsername = "";
      this.novoIsAdmin = false;
      this._revelarSenha(username, MOCK_PASSWORD);
    },

    // --- revelar senha gerada ----------------------------------------------

    _revelarSenha(username, senha) {
      this._registrarTrigger();
      this.revealUsername = username;
      this.revealPassword = senha;
      this.revealCopiado = false;
      this.revealOpen = true;
      this._aoAbrirModal("reveal-dialog");
    },

    // writeText() como primeira instrução síncrona do handler (Pitfall 11);
    // "Copiado!" só aparece se a Promise resolver — dizer ao admin que a
    // senha foi copiada quando não foi seria um falso sucesso perigoso.
    copiarSenha() {
      navigator.clipboard.writeText(this.revealPassword).then(() => {
        this.revealCopiado = true;
      }).catch(() => {
        /* cópia falhou: mantém "Copiar senha" (sem falso "Copiado!") */
      });
    },

    fecharReveal() {
      if (!this.revealOpen) return; // escape.window dispara mesmo fechado
      this.revealOpen = false;
      this._aoFecharModal();
    },

    // --- editar nome ---------------------------------------------------------

    abrirRenomear(u) {
      this._registrarTrigger();
      this.renameUser = u;
      this.renameValue = u.username;
      this.renameErro = "";
      this.renameOpen = true;
      this._aoAbrirModal("rename-dialog");
    },

    confirmarRenomear() {
      const novo = this.renameValue.trim();
      if (!novo) {
        this.renameErro = "Informe um nome de usuário.";
        return;
      }
      this.renameUser.username = novo;
      this.renameOpen = false;
      this._aoFecharModal();
    },

    cancelarRenomear() {
      if (!this.renameOpen) return; // escape.window dispara mesmo fechado
      this.renameOpen = false;
      this._aoFecharModal();
    },

    // --- ações com confirmação (mock) --------------------------------------

    gerarSenha(u) {
      this._abrirConfirmacao(
        "Gerar nova senha",
        `Uma nova senha será gerada para ${u.username} e a senha atual deixará de funcionar. Deseja continuar?`,
        "Gerar nova senha",
        false,
        () => this._revelarSenha(u.username, MOCK_PASSWORD)
      );
    },

    desativar(u) {
      // Defesa em profundidade além do x-show="podeDesativar(u)" no HTML:
      // bloqueia a auto-desativação mesmo se o método for alcançado por
      // outro caminho (espelha a regra que o backend imporá na Fase 7).
      if (this.isSelf(u)) {
        this.mostrarErro("Você não pode desativar a sua própria conta.");
        return;
      }
      this._abrirConfirmacao(
        "Desativar usuário",
        `Tem certeza que deseja desativar ${u.username}? O acesso será revogado imediatamente e a sessão ativa dele será encerrada.`,
        "Desativar",
        true,
        () => {
          u.is_active = false;
        }
      );
    },

    reativar(u) {
      this._abrirConfirmacao(
        "Reativar usuário",
        `Tem certeza que deseja reativar ${u.username}? O acesso será restaurado e ele(a) poderá fazer login novamente com a senha atual (ou a última gerada em um reset).`,
        "Reativar",
        false,
        () => {
          u.is_active = true;
        }
      );
    },

    excluir(u) {
      this._abrirConfirmacao(
        "Excluir usuário",
        `Esta ação é PERMANENTE e não pode ser desfeita. Excluir o usuário '${u.username}' e todo o seu histórico de buscas?`,
        "Excluir",
        true,
        () => {
          this.users = this.users.filter((x) => x.user_id !== u.user_id);
        }
      );
    },

    _abrirConfirmacao(titulo, corpo, textoBotao, destrutivo, action) {
      this._registrarTrigger();
      this.confirmTitulo = titulo;
      this.confirmCorpo = corpo;
      this.confirmTextoBotao = textoBotao;
      this.confirmDestrutivo = destrutivo;
      this.confirmAction = action;
      this.confirmOpen = true;
      this._aoAbrirModal("confirm-dialog");
    },

    confirmarAcao() {
      // A action pode abrir OUTRO modal (Gerar nova senha -> revelar senha):
      // ela roda antes do fechamento, e cfModalFechado detecta o modal
      // encadeado ainda visível e mantém lock/foco lá dentro.
      if (this.confirmAction) this.confirmAction();
      this.confirmOpen = false;
      this.confirmAction = null;
      this._aoFecharModal();
    },

    cancelarConfirmacao() {
      if (!this.confirmOpen) return; // escape.window dispara mesmo fechado
      this.confirmOpen = false;
      this.confirmAction = null;
      this._aoFecharModal();
    },
  }));
});
