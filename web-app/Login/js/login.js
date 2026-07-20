/* ==========================================================================
   IAprovale — /Login submit handler
   Login real: chama window.cfApi.login, persiste a sessão no sessionStorage,
   mostra estado "Conectando ao servidor..." com retry limitado (só em falha
   de conexão/timeout, nunca em resposta HTTP recebida) e exibe erros do
   backend de forma XSS-safe (sempre via textContent, sem markup bruto).
   ========================================================================== */

"use strict";

(function () {
  var form = document.getElementById("login-form");
  var usernameInput = document.getElementById("login-username");
  var passwordInput = document.getElementById("login-password");
  var errorEl = document.getElementById("login-error");
  var button = form.querySelector("button[type=\"submit\"]");

  var ENTRAR_TEXT = button.textContent;
  var CONNECTING_TEXT = "Conectando ao servidor...";
  var MAX_TENTATIVAS_CONEXAO = 2; // tentativas EXTRAS além da primeira (3 no total)

  function isConnectionFailure(err) {
    return err && (err.name === "TypeError" || err.name === "AbortError");
  }

  function showError(message) {
    errorEl.textContent = message;
    errorEl.hidden = false;
  }

  function clearError() {
    errorEl.textContent = "";
    errorEl.hidden = true;
  }

  function setConnecting() {
    button.disabled = true;
    button.textContent = CONNECTING_TEXT;
  }

  function resetButton() {
    button.disabled = false;
    button.textContent = ENTRAR_TEXT;
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();

    var username = usernameInput.value;
    var password = passwordInput.value;

    clearError();
    setConnecting();

    (async function attemptLogin() {
      var tentativasConexao = 0;
      var result = null;
      var lastError = null;

      while (true) {
        try {
          result = await window.cfApi.login(username, password);
          lastError = null;
          break;
        } catch (err) {
          lastError = err;
          if (isConnectionFailure(err) && tentativasConexao < MAX_TENTATIVAS_CONEXAO) {
            tentativasConexao += 1;
            // Mantém "Conectando ao servidor..." — feedback contínuo entre tentativas.
            continue;
          }
          break;
        }
      }

      if (lastError) {
        resetButton();
        showError(lastError.detail || "Erro desconhecido");
        return;
      }

      try {
        sessionStorage.setItem("cf-token", result.token);
        sessionStorage.setItem(
          "cf-user",
          JSON.stringify({
            user_id: result.user_id,
            username: result.username,
            is_admin: result.is_admin,
          })
        );
        sessionStorage.setItem("cf-last-activity", String(Date.now()));
      } catch (e) {
        /* sessionStorage indisponível (ex.: modo privado) — segue mesmo assim */
      }

      window.location.href = "../App/";
    })();
  });
})();
