import { BaseController } from "./base-controller.js";

(() => {
  const DIALOG_BTN_TARGET_CSS =
    '[data-follow-request-modale-target="dialogBtn"]';

  class FollowRequestModale extends BaseController {
    initialize() {
      const dialogBtnTarget = document.querySelectorAll(DIALOG_BTN_TARGET_CSS);
      if (dialogBtnTarget.length === 0) {
        console.error(
          `No element with CSS ${DIALOG_BTN_TARGET_CSS} present, can't add dialog button`,
        );
        return;
      }

      fetch(Urls.habilitationFollowMyRequest())
        .then(async (response) => {
          if (response.ok) {
            this.element.insertAdjacentHTML(
              "beforeend",
              `<template data-follow-request-modale-target="formTpl">${await response.text()}</template>`,
            );
            dialogBtnTarget.forEach((elt) => {
              elt.outerHTML = this.dialogBtnTplTarget.innerHTML;
            });
          }
        })
        .catch(this.noop);
    }

    async onSubmit(evt) {
      this.submitRequestOngoingValue = true;
      try {
        const response = await fetch(Urls.habilitationFollowMyRequest(), {
          method: "POST",
          body: new FormData(evt.target),
        });
        this.formContentTarget.innerHTML = await response.text();
      } catch {
        this.formContentTarget.insertAdjacentHTML(
          "afterbegin",
          this.unknownErrorMsgTplTarget.innerHTML,
        );
      } finally {
        this.submitRequestOngoingValue = false;
      }
    }

    onModaleOpen() {
      this.formContentTarget.innerHTML = this.formTplTarget.innerHTML;
    }

    submitRequestOngoingValueChanged(value) {
      if (value) {
        // Remove errors
        this.formContentTarget
          .querySelectorAll(".fr-alert--error")
          .forEach((el) => el.remove());
        this.submitBtnTargets.forEach((elt) =>
          elt.setAttribute("disabled", "disabled"),
        );
        this.submitBtnTargets.forEach((elt) =>
          elt.classList.add(...this.loadingClasses),
        );
      } else {
        this.submitBtnTargets.forEach((elt) => elt.removeAttribute("disabled"));
        this.submitBtnTargets.forEach((elt) =>
          elt.classList.remove(...this.loadingClasses),
        );
      }
    }

    static classes = ["loading"];
    static targets = [
      "formContent",
      "submitBtn",
      "unknownErrorMsgTpl",
      "formTpl",
      "dialogBtnTpl",
    ];
    static values = { submitRequestOngoing: { type: Boolean, default: false } };
  }

  new Promise((resolve) => window.addEventListener("load", resolve)).then(
    () => {
      const application = Stimulus.Application.start();
      application.register("follow-request-modale", FollowRequestModale);
    },
  );
})();
