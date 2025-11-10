import {
  BaseController,
  aidantsConnectApplicationReady,
} from "AidantsConnectApplication";

class BaseAidantRequestFormset extends BaseController {
  connect() {
    // Detect browser back navigation and reload page to avoid cached form data
    window.addEventListener("pageshow", (event) => {
      if (event.persisted) {
        // Page was restored from cache (back button), force reload
        window.location.reload();
      }
    });

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
