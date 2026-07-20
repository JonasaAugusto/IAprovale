"use strict";

document.addEventListener("alpine:init", () => {
  const ACTING_ADMIN_ID = 1;

  const MOCK_USERS = [
    { user_id: 1, username: "jonas", is_admin: true, is_active: true },
    { user_id: 2, username: "Márcia Nogueira", is_admin: false, is_active: true },
    { user_id: 3, username: "João Silva", is_admin: false, is_active: true },
    { user_id: 4, username: "Ana Paula", is_admin: false, is_active: false },
    { user_id: 5, username: "roberto", is_admin: false, is_active: true },
  ];

  const MOCK_PASSWORD = "Xk7-Trovao-42Q";

  Alpine.data("adminTab", () => ({
    users: MOCK_USERS.map((u) => ({ ...u })),
    filtro: "",
    erro: "",

    novoUsername: "",
    novoIsAdmin: false,

    revealOpen: false,
    revealUsername: "",
    revealPassword: "",
    revealCopiado: false,

    renameOpen: false,
    renameUser: null,
    renameValue: "",
    renameErro: "",

    confirmOpen: false,
    confirmTitulo: "",
    confirmCorpo: "",
    confirmTextoBotao: "",
    confirmDestrutivo: false,
    confirmAction: null,

    _modalTrigger: null,

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
      this.$nextTick(() => window.cfModalFechado(trigger));
    },

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

    podeDesativar(u) {
      return u.is_active && !this.isSelf(u);
    },

    mostrarErro(msg) {
      this.erro = msg;
    },

    limparErro() {
      this.erro = "";
    },

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

    _revelarSenha(username, senha) {
      this._registrarTrigger();
      this.revealUsername = username;
      this.revealPassword = senha;
      this.revealCopiado = false;
      this.revealOpen = true;
      this._aoAbrirModal("reveal-dialog");
    },

    copiarSenha() {
      navigator.clipboard.writeText(this.revealPassword).then(() => {
        this.revealCopiado = true;
      }).catch(() => {
      });
    },

    fecharReveal() {
      if (!this.revealOpen) return;
      this.revealOpen = false;
      this._aoFecharModal();
    },

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
      if (!this.renameOpen) return;
      this.renameOpen = false;
      this._aoFecharModal();
    },

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
      if (this.confirmAction) this.confirmAction();
      this.confirmOpen = false;
      this.confirmAction = null;
      this._aoFecharModal();
    },

    cancelarConfirmacao() {
      if (!this.confirmOpen) return;
      this.confirmOpen = false;
      this.confirmAction = null;
      this._aoFecharModal();
    },
  }));
});
