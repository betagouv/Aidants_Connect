"use strict";

import {BaseController} from "./base-controller.js"

(function () {
    const REMOTE_METHOD_EVENT_NAME = "changed"
    const REMOTE_METHOD_EVENT_NAME_PREFIX = "remoteconsent"
    const IS_REMOTE_METHOD_EVENT_NAME = "changed"
    const IS_REMOTE_METHOD_EVENT_NAME_PREFIX = "isremote"

    class MandateFormController extends BaseController {
        connect () {
            this.isRemoteValue = this.isRemoteInputTarget.checked;
            this.consentMethodValue = "";
            this.requiredInputTargets
                .filter(elt => elt.checked)
                .forEach(elt => { this.consentMethodValue = elt.value; });

            const scopesValue = this.scopesValue;
            document.querySelectorAll(".mandat-demarche input").forEach(it => {
                it.dataset.action = `${ this.identifier }#scopeSelected`;
                scopesValue[it.value] = it.checked;
            });
            this.scopesValue = scopesValue
        }

        scopeSelected (evt) {
            const scopesValue = this.scopesValue;
            scopesValue[evt.target.value] = evt.target.checked;
            this.scopesValue = scopesValue;
        }

        scopesValueChanged (val) {
            this.mutateVisibility(this.scopesValue[this.bdfWarningValue], this.bdfWarningTarget);
        }

        isRemoteInputTriggered (evt) {
            this.isRemoteValue = evt.target.checked
        }

        consentMethodValueChanged (value) {
            this.dispatch(
                REMOTE_METHOD_EVENT_NAME,
                {detail: {method: value.trim()}, prefix: REMOTE_METHOD_EVENT_NAME_PREFIX}
            )
        }

        remoteMethodTriggered (evt) {
            this.consentMethodValue = evt.target.value;
        }

        isRemoteValueChanged (value) {
            this.mutateVisibility(value, this.remoteConsentSectionTarget);
            this.remoteLabelTextTargets.forEach(elt => this.mutateVisibility(value, elt));
            this.requiredInputTargets.forEach(elt => this.mutateRequirement(value, elt));

            this.dispatch(
                IS_REMOTE_METHOD_EVENT_NAME,
                {detail: {isRemote: value}, prefix: IS_REMOTE_METHOD_EVENT_NAME_PREFIX}
            )
        }

        static targets = [
            "isRemoteInput",
            "requiredInput",
            "remoteLabelText",
            "remoteConsentSection",
            "bdfWarning",
        ];

        static values = {
            isRemote: Boolean,
            consentMethod: String,
            bdfWarning: String,
            scopes: {type: Object, default: {}},
        }
    }

    class RemoteMethodController extends BaseController {
        connect () {
            if (this.hasRequiredInputsTarget) {
                this.boundRemoteMethodTriggered = this.remoteMethodTriggered.bind(this);
                this.mandateFormControllerElt.addEventListener(
                    `${REMOTE_METHOD_EVENT_NAME_PREFIX}:${REMOTE_METHOD_EVENT_NAME}`, this.boundRemoteMethodTriggered
                );

                this.boundIsRemoteTriggered = this.isRemoteTriggered.bind(this);
                this.mandateFormControllerElt.addEventListener(
                    `${IS_REMOTE_METHOD_EVENT_NAME_PREFIX}:${IS_REMOTE_METHOD_EVENT_NAME}`, this.boundIsRemoteTriggered
                );
            }
        }

        get mandateFormControllerElt() {
            return document.querySelector("[data-controller='mandate-form-controller']");
        }

        remoteMethodTriggered (event) {
            const state = event.detail.method === this.consentMethodValue;
            this.mutateVisibility(state, this.requiredInputsTarget);
            this.requiredInputsTarget.querySelectorAll("input").forEach(elt => this.mutateRequirement(state, elt));
        }

        isRemoteTriggered (event) {
            this.mutateVisibility(event.detail.isRemote, this.requiredInputsTarget);
            this.requiredInputsTarget.querySelectorAll("input").forEach(elt => this.mutateRequirement(event.detail.isRemote, elt));
        }

        disconnect () {
            if (this.hasRequiredInputsTarget) {
                this.mandateFormControllerElt.removeEventListener(
                    `${REMOTE_METHOD_EVENT_NAME_PREFIX}:${REMOTE_METHOD_EVENT_NAME}`, this.boundRemoteMethodTriggered
                );
                this.mandateFormControllerElt.removeEventListener(
                    `${IS_REMOTE_METHOD_EVENT_NAME_PREFIX}:${IS_REMOTE_METHOD_EVENT_NAME}`, this.boundIsRemoteTriggered
                );
            }
        }

        static targets = ["requiredInputs"];
        static values = {"consentMethod": String}
    }


    new Promise(resolve => window.addEventListener("load", resolve)).then(() => {
        const application = Stimulus.Application.start();
        application.register("mandate-form-controller", MandateFormController);
        application.register("remote-method-controller", RemoteMethodController);
    });
})();
