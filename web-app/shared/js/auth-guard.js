"use strict";

(function () {
  var SIX_HOURS_MS = 6 * 60 * 60 * 1000;

  var token = null;
  var lastActivity = null;
  try {
    token = sessionStorage.getItem("cf-token");
    lastActivity = Number(sessionStorage.getItem("cf-last-activity"));
  } catch (e) {
  }

  var expired = !token || !lastActivity || Date.now() - lastActivity > SIX_HOURS_MS;

  if (expired) {
    try {
      sessionStorage.removeItem("cf-token");
      sessionStorage.removeItem("cf-user");
      sessionStorage.removeItem("cf-last-activity");
    } catch (e) {
    }
    window.location.replace("../Login/");
  }
})();
