import {
  BaseController,
  aidantsConnectApplicationReady,
} from "AidantsConnectApplication";

class AidantRequestForm extends BaseController {
  static values = {
    managerData: Object,
  };
  static targets = ["aidantForm"];

  connect() {
    const elt = document.querySelector("#manager-data");
    this.managerData = elt ? JSON.parse(elt.textContent) : {};
  }

  onManagerIsAidant(event) {
    // Search within the accordion (not a fieldset): text fields are no longer
    // wrapped in a fieldset; only the conseiller numérique radios are.
    const container = event.target.closest(".fr-accordion");

    Object.keys(this.managerData).forEach((key) => {
      const field = container.querySelector(`[name$='${key}']`);
      if (field) field.value = this.managerData[key];
    });
  }
}

aidantsConnectApplicationReady.then((application) =>
  application.register("aidant-request-form", AidantRequestForm)
);
