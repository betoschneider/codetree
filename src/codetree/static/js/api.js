(function (global) {
  "use strict";

  var TIMEOUT_MS = 5000;

  function extractMessage(data, status) {
    if (data && typeof data.detail === "string") {
      return data.detail;
    }
    if (status === 413) {
      return "Conteúdo muito grande.";
    }
    if (status === 415) {
      return "Formato de envio inválido.";
    }
    if (status === 429) {
      return "Muitas requisições. Aguarde um instante e tente novamente.";
    }
    if (status === 503) {
      return "O servidor demorou para responder. Tente novamente.";
    }
    return "Entrada inválida.";
  }

  function postJson(path, body) {
    var controller = new AbortController();
    var timer = global.setTimeout(function () {
      controller.abort();
    }, TIMEOUT_MS);

    return fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    })
      .then(function (response) {
        return response
          .json()
          .catch(function () {
            return {};
          })
          .then(function (data) {
            if (!response.ok) {
              throw new Error(extractMessage(data, response.status));
            }
            return data;
          });
      })
      .catch(function (error) {
        if (error && error.name === "AbortError") {
          throw new Error("Tempo de resposta excedido. Tente novamente.");
        }
        throw error;
      })
      .finally(function () {
        global.clearTimeout(timer);
      });
  }

  global.CodeTreeApi = {
    generateTree: function (text, mode) {
      return postJson("/api/tree", { text: text, mode: mode });
    },
    generateTimeline: function (text) {
      return postJson("/api/timeline", { text: text });
    },
  };
})(window);
