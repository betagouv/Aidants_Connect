import {
  BaseController,
  aidantsConnectApplicationReady,
} from "AidantsConnectApplication";

class BaseAidantRequestFormset extends BaseController {
  // static values = {
  //   managerData: Object,
  // };
  // static targets = ["aidantForm"];

  connect() {
    this.openLastForm();
  }

  openLastForm() {
    this.closeAllAccordions();

    const accordions = this.element.querySelectorAll(".fr-accordion");
    if (accordions.length > 0) {
      const lastAccordion = accordions[accordions.length - 1];
      this.openAccordion(lastAccordion);
    }
  }

  closeAllAccordions() {
    const accordions = this.element.querySelectorAll(".fr-accordion");
    accordions.forEach((accordion) => {
      const button = accordion.querySelector(".fr-accordion__btn");
      const collapse = accordion.querySelector(".fr-collapse");

      button.setAttribute("aria-expanded", "false");
      collapse.classList.remove("fr-collapse--expanded");
    });
  }

  openAccordion(accordion) {
    const button = accordion.querySelector(".fr-accordion__btn");
    const collapse = accordion.querySelector(".fr-collapse");

    button.setAttribute("aria-expanded", "true");
    collapse.classList.add("fr-collapse--expanded");
  }
}

aidantsConnectApplicationReady.then((application) =>
  application.register("base-aidant-request-formset", BaseAidantRequestFormset)
);
