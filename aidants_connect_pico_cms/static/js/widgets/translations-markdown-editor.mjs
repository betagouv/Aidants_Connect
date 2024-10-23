import {aidantsConnectApplicationReady} from "AidantsConnectApplication"
import {MarkdownEditor} from "MarkdownEditor"

class TranslationsMarkdownEditor extends MarkdownEditor {
    formDataEntries (plainText) {
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

aidantsConnectApplicationReady.then(app => {
    const target = document.querySelector("[data-markdown-editor-target='textareaContainer']");
    const container = target.closest("form");
    container.dataset.controller = "markdown-editor";
    app.register("markdown-editor", TranslationsMarkdownEditor);
})
