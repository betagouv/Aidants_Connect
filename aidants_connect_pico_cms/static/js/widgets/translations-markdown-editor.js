import {MarkdownEditor} from "./markdown-editor.js";

(function () {
    class TranslationsMarkdownEditor extends MarkdownEditor {
        formDataEntries(plainText) {
            return {
                ...super.formDataEntries(plainText),
                lang: this.langInputTarget.value
            };
        }

        static targets = [
            ...MarkdownEditor.targets,
            "langInput"
        ]
    }

    function init() {
        const target = document.querySelector("[data-markdown-editor-target='textareaContainer']");
        const container = target.closest("form");
        container.dataset.controller = "markdown-editor";
        Stimulus.Application.start().register("markdown-editor", TranslationsMarkdownEditor);
    }

    new Promise(resolve => window.addEventListener("load", resolve)).then(init);
})();
