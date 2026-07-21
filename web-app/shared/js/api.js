"use strict";

window.cfApi = (function () {
  var BASE_URL = "https://iaprovalebackend.onrender.com";
  var DEFAULT_TIMEOUT_MS = 90000;

  function touchActivity() {
    try {
      sessionStorage.setItem("cf-last-activity", String(Date.now()));
    } catch (e) {
    }
  }

  function clearSessionAndRedirect() {
    try {
      sessionStorage.removeItem("cf-token");
      sessionStorage.removeItem("cf-user");
      sessionStorage.removeItem("cf-last-activity");
    } catch (e) {
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

        if (resp.status === 401 && !isLoginCall) {
          clearSessionAndRedirect();
          throw { detail: "Sessão expirada." };
        }

        if (!resp.ok) {
          return resp
            .json()
            .catch(function () {
              return null;
            })
            .then(function (body) {
              var detail =
                (body && typeof body.detail === "string" && body.detail) ||
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
    getProfile: function () {
      return request("GET", "/profile", { auth: true });
    },
    search: function (query, usarCurriculo) {
      return request("POST", "/search", {
        json: { query: query, usar_curriculo: !!usarCurriculo },
        auth: true,
      });
    },
    updateProfile: function (payload) {
      return request("PUT", "/profile", { json: payload, auth: true });
    },
    lookupCep: function (cep) {
      return request("GET", "/cep/" + cep, { auth: true, timeoutMs: 15000 });
    },
    listUsers: function () {
      return request("GET", "/auth/users", { auth: true });
    },
    createUser: function (username, isAdmin) {
      return request("POST", "/auth/users", {
        json: { username: username, is_admin: !!isAdmin },
        auth: true,
      });
    },
    renameUser: function (userId, newUsername) {
      return request("PATCH", "/auth/users/" + userId + "/username", {
        json: { username: newUsername },
        auth: true,
      });
    },
    resetPassword: function (userId) {
      return request("POST", "/auth/users/" + userId + "/reset-password", { auth: true });
    },
    deactivateUser: function (userId) {
      return request("PATCH", "/auth/users/" + userId + "/deactivate", { auth: true });
    },
    reactivateUser: function (userId) {
      return request("PATCH", "/auth/users/" + userId + "/reactivate", { auth: true });
    },
    deleteUser: function (userId) {
      return request("DELETE", "/auth/users/" + userId, { auth: true });
    },
    pdf: function (results, query, extractedSummary) {
      var token = null;
      try {
        token = sessionStorage.getItem("cf-token");
      } catch (e) {
      }
      var headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = "Bearer " + token;

      return fetch(BASE_URL + "/pdf", {
        method: "POST",
        headers: headers,
        body: JSON.stringify({ results: results, query: query, extracted_summary: extractedSummary }),
      }).then(function (resp) {
        if (resp.status === 401) {
          clearSessionAndRedirect();
          throw { detail: "Sessão expirada." };
        }
        if (!resp.ok) {
          return resp
            .json()
            .catch(function () {
              return null;
            })
            .then(function (body) {
              throw { detail: (body && body.detail) || "Não foi possível gerar o PDF." };
            });
        }
        touchActivity();
        return resp.blob();
      });
    },
  };
})();
