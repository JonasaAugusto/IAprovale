"use strict";

window.cfPdfJs = (function () {
  var VERSION = "6.1.200";
  var BASE = "https://cdn.jsdelivr.net/npm/pdfjs-dist@" + VERSION + "/build/";
  var _loaded = null;

  function carregar() {
    if (_loaded) return _loaded;
    _loaded = import(/* @vite-ignore */ BASE + "pdf.min.mjs").then(function (mod) {
      mod.GlobalWorkerOptions.workerSrc = BASE + "pdf.worker.min.mjs";
      return mod;
    });
    return _loaded;
  }

  async function extrairTexto(arrayBuffer) {
    var pdfjsLib = await carregar();
    var doc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    var partes = [];
    for (var i = 1; i <= doc.numPages; i++) {
      var page = await doc.getPage(i);
      var content = await page.getTextContent();
      partes.push(
        content.items
          .map(function (it) {
            return it.str;
          })
          .join(" ")
      );
    }
    return partes.join("\n");
  }

  return { extrairTexto: extrairTexto };
})();
