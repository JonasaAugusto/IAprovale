"use strict";

document.addEventListener("alpine:init", () => {
  Alpine.data("adminTab", () => ({
    users: [],
    filtro: "",
    erro: "",
    carregando: false,
    adicionando: false,

    novoUsername: "",
    novoIsAdmin: false,

    revealOpen: false,
    revealUsername: "",
    revealPassword: "",
    revealCopiado: false,

    verInfoOpen: false,
    verInfoUser: null,
    verInfoData: null,
    verInfoErro: "",
    verInfoCarregando: false,

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
    _actingAdminId: "",

    async init() {
      try {
        const user = JSON.parse(sessionStorage.getItem("cf-user"));
        this._actingAdminId = (user && user.user_id) || "";
      } catch (e) {
      }
      this.carregando = true;
      try {
        this.users = await window.cfApi.listUsers();
      } catch (err) {
        this.erro = (err && err.detail) || "Não foi possível carregar os usuários.";
      } finally {
        this.carregando = false;
      }
    },

    async carregarUsuarios() {
      try {
        this.users = await window.cfApi.listUsers();
      } catch (err) {
        this.mostrarErro((err && err.detail) || "Não foi possível atualizar a lista de usuários.");
      }
    },

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
      return !!this._actingAdminId && u.user_id === this._actingAdminId;
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

    async adicionar() {
      const username = this.novoUsername.trim();
      if (!username) {
        this.mostrarErro("Informe um nome de usuário.");
        return;
      }
      this.limparErro();
      if (this.adicionando) return;
      this.adicionando = true;
      try {
        const resp = await window.cfApi.createUser(username, this.novoIsAdmin);
        this.novoUsername = "";
        this.novoIsAdmin = false;
        this._revelarSenha(resp.username, resp.generated_password);
        await this.carregarUsuarios();
      } catch (err) {
        this.mostrarErro((err && err.detail) || "Não foi possível criar o usuário.");
      } finally {
        this.adicionando = false;
      }
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

    async abrirVerInfo(u) {
      this._registrarTrigger();
      this.verInfoUser = u;
      this.verInfoData = null;
      this.verInfoErro = "";
      this.verInfoOpen = true;
      this._aoAbrirModal("ver-info-dialog");
      this.verInfoCarregando = true;
      try {
        this.verInfoData = await window.cfApi.getUserUsage(u.user_id);
      } catch (err) {
        this.verInfoErro = (err && err.detail) || "Não foi possível carregar as informações.";
      } finally {
        this.verInfoCarregando = false;
      }
    },

    fecharVerInfo() {
      if (!this.verInfoOpen) return;
      this.verInfoOpen = false;
      this._aoFecharModal();
    },

    verInfoCards() {
      if (!this.verInfoData) return [];
      const d = this.verInfoData;
      return [
        { numero: String(d.normal_count), rotulo: "Pesquisas normais" },
        { numero: String(d.curriculo_count), rotulo: "Pesquisas com currículo" },
        { numero: "US$ " + Number(d.token_cost_usd || 0).toFixed(4), rotulo: "Gasto em IA" },
        { numero: String(d.resultados_count), rotulo: "Concursos retornados" },
        { numero: this._formatarData(d.ultima_busca), rotulo: "Última busca" },
        { numero: this._formatarDataHora(d.last_login_at), rotulo: "Último login" },
      ];
    },

    _formatarData(iso) {
      if (!iso) return "nunca";
      const partes = iso.split("-");
      if (partes.length !== 3) return "nunca";
      return partes[2] + "/" + partes[1] + "/" + partes[0];
    },

    _formatarDataHora(iso) {
      if (!iso) return "nunca";
      const d = new Date(iso);
      if (isNaN(d.getTime())) return "nunca";
      const pad = (n) => String(n).padStart(2, "0");
      return (
        pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + d.getFullYear() +
        " " + pad(d.getHours()) + ":" + pad(d.getMinutes())
      );
    },

    abrirRenomear(u) {
      this._registrarTrigger();
      this.renameUser = u;
      this.renameValue = u.username;
      this.renameErro = "";
      this.renameOpen = true;
      this._aoAbrirModal("rename-dialog");
    },

    async confirmarRenomear() {
      const novo = this.renameValue.trim();
      if (!novo) {
        this.renameErro = "Informe um nome de usuário.";
        return;
      }
      try {
        await window.cfApi.renameUser(this.renameUser.user_id, novo);
        this.renameOpen = false;
        this._aoFecharModal();
        await this.carregarUsuarios();
      } catch (err) {
        this.renameErro = (err && err.detail) || "Não foi possível renomear.";
      }
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
        async () => {
          try {
            const resp = await window.cfApi.resetPassword(u.user_id);
            this._revelarSenha(u.username, resp.generated_password);
            await this.carregarUsuarios();
          } catch (err) {
            this.mostrarErro((err && err.detail) || "Não foi possível gerar nova senha.");
          }
        }
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
        async () => {
          try {
            await window.cfApi.deactivateUser(u.user_id);
            await this.carregarUsuarios();
          } catch (err) {
            this.mostrarErro((err && err.detail) || "Não foi possível desativar o usuário.");
          }
        }
      );
    },

    reativar(u) {
      this._abrirConfirmacao(
        "Reativar usuário",
        `Tem certeza que deseja reativar ${u.username}? O acesso será restaurado e ele(a) poderá fazer login novamente com a senha atual (ou a última gerada em um reset).`,
        "Reativar",
        false,
        async () => {
          try {
            await window.cfApi.reactivateUser(u.user_id);
            await this.carregarUsuarios();
          } catch (err) {
            this.mostrarErro((err && err.detail) || "Não foi possível reativar o usuário.");
          }
        }
      );
    },

    excluir(u) {
      this._abrirConfirmacao(
        "Excluir usuário",
        `Esta ação é PERMANENTE e não pode ser desfeita. Excluir o usuário '${u.username}' e todo o seu histórico de buscas?`,
        "Excluir",
        true,
        async () => {
          try {
            await window.cfApi.deleteUser(u.user_id);
            await this.carregarUsuarios();
          } catch (err) {
            this.mostrarErro((err && err.detail) || "Não foi possível excluir o usuário.");
          }
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
