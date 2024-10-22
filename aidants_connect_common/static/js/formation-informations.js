import { BaseController } from "./base-controller.js";

(() => {
  /**
   * @property {HTMLSelectElement} regionsInputTarget
   * @property {HTMLElement} informationsContainerTarget
   * @property {String} regionSelectValue
   */
  class FormationInformation extends BaseController {
    initialize() {
      this.showElement(this.element);
      if (this.regionsInputTarget.value) {
        this.regionSelectValue = this.regionsInputTarget.value;
      }
    }

    regionSelectValueChanged(val) {
      fetch(Urls.formationInformations({ pk: val }))
        .then(async (response) => {
          if (response.ok) {
            this.informationsContainerTarget.innerHTML = await response.text();
          }
        })
        .catch(() => {});
    }

    regionChanged(evt) {
      this.regionSelectValue = evt.target.value;
    }

    static targets = ["informationsContainer", "regionsInput"];
    static values = { regionSelect: String };
  }

  new Promise((resolve) => window.addEventListener("load", resolve)).then(
    () => {
      const application = Stimulus.Application.start();
      application.register("formation-informations", FormationInformation);
    },
  );
})();
