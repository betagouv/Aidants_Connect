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
    console.log("AidantRequestForm connected");

    const elt = document.querySelector("#manager-data");
    console.log(elt);
    this.managerData = elt ? JSON.parse(elt.textContent) : {};
  }

  onManagerIsAidant(event) {
    console.log(event.target);
    const fieldset = event.target
      .closest(".fr-accordion")
      .querySelector(".fr-fieldset");

    Object.keys(this.managerData).forEach((key) => {
      const field = fieldset.querySelector(`[name$='${key}']`);
      if (field) field.value = this.managerData[key];
    });
  }
}

aidantsConnectApplicationReady.then((application) =>
  application.register("aidant-request-form", AidantRequestForm)
);
