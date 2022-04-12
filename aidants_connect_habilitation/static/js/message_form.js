"use strict";

(function () {
    // This JS code won't be executed on IE11, so we can write ES6 code
    class MessageForm extends Stimulus.Controller {
        initialize() {
            this.onGoingRequestValue = false;
        }

        async onSubmit(evt) {
            if (this.onGoingRequestValue) {
                return;
            }

            evt.preventDefault();
            evt.stopPropagation();

            if (!this.formTarget.checkValidity()) {
                return;
            }

            let dest = new URL(this.formTarget.action, location.origin);
            dest.searchParams.append("http-api", "true");

            this.onGoingRequestValue = true;

            let response = await fetch(dest.toString(), {
                method: this.formTarget.method.toUpperCase(),
                body: new FormData(this.formTarget),
            }).finally(() => {this.onGoingRequestValue = false});

            if (response.ok) {
                let html = await response.text();
                if (this.hasEmptyElementTarget) {
                    this.emptyElementTarget.remove();
                }

                this.messagesListTarget.insertAdjacentHTML("beforeend", html);
                this.formTarget.reset();
            }
        }

        onGoingRequestValueChanged(value, _) {
            if (value) {
                this.submitBtnTarget.setAttribute("disabled", "disabled");
                this.textareaTarget.setAttribute("disabled", "disabled");
            } else {
                this.submitBtnTarget.removeAttribute("disabled");
                this.textareaTarget.removeAttribute("disabled");
            }
        }

        static targets = ["form", "emptyElement", "messagesList", "submitBtn", "textarea"]
        static values = {"onGoingRequest": Boolean}
    }

    if (window.fetch) {
        window.addEventListener("load", () =>
            Stimulus.Application.start().register("message-form", MessageForm)
        );
    }
})();
