"use strict";

import {BaseController} from "./base-controller.js"

(function () {
    const REMOTE_METHOD_EVENT_NAME = "remoteconsent:changed"

    class IsRemoteController extends BaseController {
        connect () {
            this.isRemoteValue = this.isRemoteInputTarget.checked;
            this.consentMethodValue = "";
            this.requiredInputTargets
                .filter(elt => elt.checked)
                .forEach(elt => { this.consentMethodValue = elt.value; });
        }

        isRemoteInputTriggered (evt) {
            this.isRemoteValue = evt.target.checked
        }

        consentMethodValueChanged (value) {
            const event = new CustomEvent(REMOTE_METHOD_EVENT_NAME, {detail: {method: value.trim()}});
            this.element.dispatchEvent(event);
        }

        remoteMethodTriggered (evt) {
            this.consentMethodValue = evt.target.value;
        }

        isRemoteValueChanged (value) {
            this.mutateVisibility(value, this.remoteConsentSectionTarget);
            this.remoteLabelTextTargets.forEach(elt => this.mutateVisibility(value, elt));
            this.requiredInputTargets.forEach(elt => this.mutateRequirement(value, elt));
        }

        static targets = [
            "isRemoteInput",
            "requiredInput",
            "remoteLabelText",
            "remoteConsentSection"
        ];

        static values = {
            "isRemote": Boolean,
            "consentMethod": String,
        }
    }

    class RemoteMethodController extends BaseController {
        connect () {
            if (this.hasRequiredInputsTarget) {
                this.boundRemoteMethodTriggered = this.remoteMethodTriggered.bind(this);
                document.querySelector("[data-controller='is-remote-controller']").addEventListener(
                    REMOTE_METHOD_EVENT_NAME, this.boundRemoteMethodTriggered
                );
            }
        }

        remoteMethodTriggered (event) {
            const state = event.detail.method === this.consentMethodValue;
            this.mutateVisibility(state, this.requiredInputsTarget);
            this.requiredInputsTarget.querySelectorAll("input").forEach(elt => this.mutateRequirement(state, elt));
        }

        disconnect () {
            if (this.hasRequiredInputsTarget) {
                this.element.removeEventListener(REMOTE_METHOD_EVENT_NAME, this.boundRemoteMethodTriggered);
            }
        }

        static targets = ["requiredInputs"];
        static values = {"consentMethod": String}
    }


    new Promise(resolve => window.addEventListener("load", resolve)).then(() => {
        const application = Stimulus.Application.start();
        application.register("is-remote-controller", IsRemoteController);
        application.register("remote-method-controller", RemoteMethodController);
    });
})();
