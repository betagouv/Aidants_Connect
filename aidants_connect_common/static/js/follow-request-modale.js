"use strict";

import {BaseController} from "./base-controller.js"

(function () {
    class FollowRequestModale extends BaseController {
        initialize () {
            fetch(Urls.habilitationFollowMyRequest())
                .then(async response => {
                    if (response.ok) {
                        this.element.insertAdjacentHTML(
                            "beforeend", 
                            `<template data-follow-request-modale-target="formTpl">${await response.text()}</template>`
                        );
                        this.showElement(this.element);
                    }
                }).catch(this.noop);
        }

        async onSubmit (evt) {
            this.submitRequestOngoingValue = true;
            try {
                const response = await fetch(
                    Urls.habilitationFollowMyRequest(),
                    {
                        method: "POST",
                        body: new FormData(evt.target),
                    },
                );
                this.formContentTarget.innerHTML = await response.text();
            } catch {
                this.formContentTarget.insertAdjacentHTML("afterbegin", this.unknownErrorMsgTplTarget.innerHTML);
            } finally {
                this.submitRequestOngoingValue = false;
            }
        }

        onModaleOpen() {
            this.formContentTarget.innerHTML = this.formTplTarget.innerHTML;
        }

        submitRequestOngoingValueChanged (value) {
            if (value) {
                // Remove errors
                this.formContentTarget.querySelectorAll(".fr-alert--error").forEach(el => el.remove());
            } else {

            }
        }

        static targets = ["formContent", "unknownErrorMsgTpl", "formTpl"]
        static values = {submitRequestOngoing: {type: Boolean, default: false}}
    }

    new Promise(resolve => window.addEventListener("load", resolve)).then(() => {
        const application = Stimulus.Application.start();
        application.register("follow-request-modale", FollowRequestModale);
    });
})();
