export class MarkdownEditor extends Stimulus.Controller {
    initialize() {
        this.textareaContainerTarget.parentElement.classList.add("markdown-editor");
        // Since we can only set values on the textarea widget, we need to replicate data values set on it
        // to the controller's element so they are not empty
        for(let key in this.textareaContainerTarget.dataset) {
            if(key.endsWith("Value")) {
                this.element.dataset[key] = this.textareaContainerTarget.dataset[key];
            }
        }
        this.easyMDE = new EasyMDE({
            // Options documentation available here: https://github.com/Ionaru/easy-markdown-editor#options-list
            element: this.textareaContainerTarget,
            autofocus: true,
            autoDownloadFontAwesome: false,
            hideIcons: ["guide"],
            spellChecker: false,
            nativeSpellcheck: false,
            sideBySideFullscreen: false,
            previewRender: this.previewRender.bind(this),
        });
    }

    previewRender(plainText, preview) {
        const body = new FormData();
        Object.entries(this.formDataEntries(plainText)).forEach(([k, v]) => body.append(k, v.toString()));
        fetch(this.renderEndpointValue, {method: "POST", body: body}).then(response => {
            if (response.ok) {
                response.text().then(body => {preview.innerHTML = body;});
            }
        });

        return "En attente…"
    }

    formDataEntries(plainText) {
        return {[this.renderKwargValue]: plainText};
    }


    static targets = [
        "textareaContainer",
    ]

    static values = {
        "render-endpoint": String,
        "render-kwarg": String,
    }
}
