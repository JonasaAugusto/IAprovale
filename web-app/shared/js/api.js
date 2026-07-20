/* ==========================================================================
   IAprovale — shared HTTP client (cfApi)
   Wrapper fetch centralizado: Bearer token, timeout de 90s (tolera cold
   start do Render), tratamento central de 401 (limpa sessão + redireciona),
   mensagens PT-BR verbatim. Porta desktop/app/api_client.py (_request /
   _raise_for_status) 1:1 para JS puro, sem dependências.
   Consumido por Login/js/login.js e App/js/app.js (Fase 7); Fases 8/9/11
   só adicionam métodos novos ao objeto retornado abaixo, sem reabrir este
   arquivo para resolver 401/timeout/mensagens de novo.
   ========================================================================== */

"use strict";

window.cfApi = (function () {
  var BASE_URL = "https://iaprovalebackend.onrender.com"; // mesmo default de produção de desktop/app/config.py
  var DEFAULT_TIMEOUT_MS = 90000; // casa com o timeout=90 já provado em produção no desktop

  function touchActivity() {
    try {
      sessionStorage.setItem("cf-last-activity", String(Date.now()));
    } catch (e) {
      /* sessionStorage indisponível (ex.: modo privado) — segue sem persistir */
    }
  }

  function clearSessionAndRedirect() {
    try {
      sessionStorage.removeItem("cf-token");
      sessionStorage.removeItem("cf-user");
      sessionStorage.removeItem("cf-last-activity");
    } catch (e) {
      /* ignore */
    }
    window.location.href = "../Login/";
  }

  function request(method, path, options) {
    options = options || {};
    var json = options.json;
    var auth = options.auth !== false;
    var timeoutMs = options.timeoutMs || DEFAULT_TIMEOUT_MS;
    var isLoginCall = options.isLoginCall === true;

    var controller = new AbortController();
    var timer = setTimeout(function () {
      controller.abort();
    }, timeoutMs);

    var headers = { "Content-Type": "application/json" };
    if (auth) {
      var token = null;
      try {
        token = sessionStorage.getItem("cf-token");
      } catch (e) {
        /* sessionStorage indisponível — segue sem Authorization */
      }
      if (token) headers["Authorization"] = "Bearer " + token;
    }

    return fetch(BASE_URL + path, {
      method: method,
      headers: headers,
      body: json !== undefined ? JSON.stringify(json) : undefined,
      signal: controller.signal,
    })
      .then(function (resp) {
        clearTimeout(timer);

        // 401 tem que ser checado ANTES do branch genérico de erro: dispara
        // o guard central (limpa sessão + redireciona) só quando NÃO é a
        // própria chamada de login (senha errada não pode disparar redirect).
        if (resp.status === 401 && !isLoginCall) {
          clearSessionAndRedirect();
          throw { detail: "Sessão expirada." };
        }

        if (!resp.ok) {
          return resp
            .json()
            .catch(function () {
              return null; // corpo HTML (ex.: Render 5xx cold-start/proxy) — sem JSON pra ler
            })
            .then(function (body) {
              var detail =
                (body && body.detail) ||
                (resp.status >= 500
                  ? "O servidor está iniciando ou instável no momento. Aguarde alguns segundos e tente novamente."
                  : "Não foi possível completar a operação. Tente novamente.");
              throw { detail: detail, status: resp.status };
            });
        }

        if (auth) touchActivity();
        return resp.status === 204 ? null : resp.json();
      })
      .catch(function (err) {
        clearTimeout(timer);
        // Erro já normalizado (branch acima já lançou um {detail,...}) — repassa como está.
        if (err && err.detail) throw err;
        if (err && err.name === "AbortError") {
          throw { detail: "O servidor demorou demais para responder. Tente novamente em instantes." };
        }
        throw { detail: "Não foi possível conectar ao servidor. Verifique sua internet e tente novamente." };
      });
  }

  return {
    login: function (username, password) {
      return request("POST", "/auth/login", {
        json: { username: username, password: password },
        auth: false,
        isLoginCall: true,
      });
    },
    logout: function () {
      return request("POST", "/auth/logout", { auth: true });
    },
  };
})();
