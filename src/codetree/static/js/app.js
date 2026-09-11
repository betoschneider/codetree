(function (global) {
  "use strict";

  var DEBOUNCE_MS = 150;
  var THEME_KEY = "codetree-theme";

  var CONTENT = {
    tree: {
      label: "Estrutura de pastas",
      hint: "Uma linha por pasta. Na indentação, use espaços para indicar o nível; nos caminhos, use / para separar os níveis.",
      example: "projeto\n src\n  componentes\n docs\n  guia",
      file: "codetree-arvore.txt",
    },
    timeline: {
      label: "Eventos da linha do tempo",
      hint: "Uma linha com data (dd/mm) é um evento; linhas iniciadas por - são subitens do evento anterior.",
      example:
        "01/03 | Início do projeto\n  - Planejamento\n\n15/03 | Primeira entrega\n  - Revisão\n  - Publicação",
      file: "codetree-timeline.txt",
    },
  };

  var input = document.getElementById("input");
  var output = document.getElementById("output");
  var hint = document.getElementById("hint");
  var example = document.getElementById("example");
  var editorLabel = document.getElementById("editor-label");
  var modeRow = document.getElementById("mode-row");
  var status = document.getElementById("status");
  var copyButton = document.getElementById("copy");
  var downloadButton = document.getElementById("download");
  var themeButton = document.getElementById("theme-toggle");
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tab"));

  var currentTab = "tree";
  var debounceTimer = null;
  var requestId = 0;
  var lastResult = "";
  var hasResult = false;

  function currentMode() {
    var checked = document.querySelector('input[name="tree-mode"]:checked');
    return checked ? checked.value : "auto";
  }

  function setStatus(message) {
    status.textContent = message || "";
  }

  function setOutput(text, isError) {
    output.textContent = text;
    output.classList.toggle("is-error", Boolean(isError));
    hasResult = Boolean(text) && !isError;
    lastResult = hasResult ? text : "";
  }

  function scheduleGenerate() {
    global.clearTimeout(debounceTimer);
    debounceTimer = global.setTimeout(generate, DEBOUNCE_MS);
  }

  function generate() {
    var text = input.value;
    if (!text.trim()) {
      setOutput("", false);
      return;
    }

    var id = ++requestId;
    var request =
      currentTab === "tree"
        ? CodeTreeApi.generateTree(text, currentMode())
        : CodeTreeApi.generateTimeline(text);

    request
      .then(function (data) {
        if (id !== requestId) {
          return;
        }
        setOutput(typeof data.result === "string" ? data.result : "", false);
      })
      .catch(function (error) {
        if (id !== requestId) {
          return;
        }
        setOutput(error && error.message ? error.message : "Erro inesperado.", true);
      });
  }

  function applyTab(tab) {
    currentTab = tab;
    var content = CONTENT[tab];

    tabs.forEach(function (button) {
      var selected = button.dataset.tab === tab;
      button.setAttribute("aria-selected", selected ? "true" : "false");
    });

    editorLabel.textContent = content.label;
    hint.textContent = content.hint;
    example.textContent = content.example;
    modeRow.hidden = tab !== "tree";

    setStatus("");
    setOutput("", false);
    generate();
  }

  function copyText(text) {
    if (navigator.clipboard && global.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var helper = document.createElement("textarea");
      helper.value = text;
      helper.setAttribute("readonly", "");
      helper.className = "clipboard-helper";
      document.body.appendChild(helper);
      helper.select();
      var ok = false;
      try {
        ok = document.execCommand("copy");
      } catch (error) {
        ok = false;
      }
      document.body.removeChild(helper);
      if (ok) {
        resolve();
      } else {
        reject(new Error("Não foi possível copiar."));
      }
    });
  }

  function downloadText(text, filename) {
    var blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    global.setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 0);
  }

  function resolveTheme(preference) {
    if (preference === "light" || preference === "dark") {
      return preference;
    }
    return global.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(preference) {
    var resolved = resolveTheme(preference);
    document.documentElement.setAttribute("data-theme", resolved);
    themeButton.setAttribute(
      "aria-label",
      resolved === "dark" ? "Ativar tema claro" : "Ativar tema escuro"
    );
  }

  tabs.forEach(function (button) {
    button.addEventListener("click", function () {
      if (button.dataset.tab !== currentTab) {
        applyTab(button.dataset.tab);
      }
    });
  });

  input.addEventListener("input", scheduleGenerate);

  modeRow.addEventListener("change", generate);

  copyButton.addEventListener("click", function () {
    if (!hasResult) {
      setStatus("Nada para copiar.");
      return;
    }
    copyText(lastResult)
      .then(function () {
        setStatus("Copiado!");
        global.setTimeout(function () {
          setStatus("");
        }, 1500);
      })
      .catch(function (error) {
        setStatus(error && error.message ? error.message : "Não foi possível copiar.");
      });
  });

  downloadButton.addEventListener("click", function () {
    if (!hasResult) {
      setStatus("Nada para baixar.");
      return;
    }
    downloadText(lastResult, CONTENT[currentTab].file);
    setStatus("Download iniciado.");
  });

  themeButton.addEventListener("click", function () {
    var stored = localStorage.getItem(THEME_KEY);
    var next = resolveTheme(stored) === "dark" ? "light" : "dark";
    localStorage.setItem(THEME_KEY, next);
    applyTheme(next);
  });

  global.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
    if (!localStorage.getItem(THEME_KEY)) {
      applyTheme("system");
    }
  });

  applyTheme(localStorage.getItem(THEME_KEY) || "system");
  applyTab("tree");
})(window);
