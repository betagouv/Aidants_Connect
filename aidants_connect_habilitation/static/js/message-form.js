import { BaseController } from "./base-controller.js";

(() => {
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

      const dest = new URL(this.formTarget.action, location.origin);
      dest.searchParams.append("http-api", "true");

      this.onGoingRequestValue = true;

      const response = await fetch(dest.toString(), {
        method: this.formTarget.method.toUpperCase(),
        body: new FormData(this.formTarget),
      }).finally(() => {
        this.onGoingRequestValue = false;
      });

      if (response.ok) {
        const html = await response.text();
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

    static targets = [
      "form",
      "emptyElement",
      "messagesList",
      "submitBtn",
      "textarea",
    ];
    static values = { onGoingRequest: Boolean };
  }

  new Promise((resolve) => window.addEventListener("load", resolve)).then(
    () => {
      const application = Stimulus.Application.start();
      application.register("message-form", MessageForm);
    },
  );
})();
