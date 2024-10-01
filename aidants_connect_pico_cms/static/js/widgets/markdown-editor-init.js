import { MarkdownEditor } from "./markdown-editor.js";

(() => {
  function init() {
    const container = document.querySelector(
      "[data-markdown-editor-target='textareaContainer']",
    ).parentNode;
    container.dataset.controller = "markdown-editor";
    Stimulus.Application.start().register("markdown-editor", MarkdownEditor);
  }

  new Promise((resolve) => window.addEventListener("load", resolve)).then(init);
})();
