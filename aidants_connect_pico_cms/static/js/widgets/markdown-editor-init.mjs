import {aidantsConnectApplicationReady} from "AidantsConnectApplication"
import {MarkdownEditor} from "MarkdownEditor"

aidantsConnectApplicationReady.then(application => {
    const container = document.querySelector("[data-markdown-editor-target='textareaContainer']").parentNode;
    container.dataset.controller = "markdown-editor";
    application.register("markdown-editor", MarkdownEditor);
});
