import { BaseController } from "./base-controller.js";

(() => {
  class CommuneImportForm extends BaseController {
    initialize() {
      this.hideElement(this.communeZrrClassificationWrapperTarget);
    }
    onOptionSelected(evt) {
      const idx = Number.parseInt(evt.target.value, 10);
      this.mutateVisibility(
        evt.target.options[idx].text === this.zrrResourceNameValue,
        this.communeZrrClassificationWrapperTarget,
      );
    }

    static targets = ["communeZrrClassificationWrapper"];
    static values = { zrrResourceName: String };
  }

  new Promise((resolve) => window.addEventListener("load", resolve)).then(
    () => {
      const application = Stimulus.Application.start();
      application.register("commune-import-form", CommuneImportForm);
    },
  );
})();
