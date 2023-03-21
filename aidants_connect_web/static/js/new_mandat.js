"use strict";

(function () {
    const REMOTE_METHOD_EVENT_NAME = "remoteconsent:changed"

    const MutateStateMixin = {
        mutateVisibility: function mutateVisibility(visible, elt) {
            if (visible) {
                elt.removeAttribute("hidden");
                elt.removeAttribute("aria-hidden");
            } else {
                elt.setAttribute("hidden", "hidden");
                elt.setAttribute("aria-hidden", "true");
            }
        },

        mutateRequirement: function mutateRequirement(required, elt) {
            if (required) {
                elt.setAttribute("required", "required");
            } else {
                elt.removeAttribute("required");
            }
        }
    };

    const IsRemoteController = Object.extendClass(Stimulus.Controller);

    Object.assign(IsRemoteController.prototype, MutateStateMixin, {
        connect: function connect() {
            this.isRemoteValue = this.isRemoteInputTarget.checked;
            this.consentMethodValue = "";
            this.requiredInputTargets
                .filter(function (elt) {
                    return elt.checked;
                })
                .forEach(function (elt) {
                    this.consentMethodValue = elt.value
                }.bind(this));
        },

        isRemoteInputTriggered: function isRemoteInputTriggered(evt) {
            this.isRemoteValue = evt.target.checked
        },

        consentMethodValueChanged: function consentMethodValueChanged(value) {
            const event = new CustomEvent(REMOTE_METHOD_EVENT_NAME, {detail: {method: value.trim()}});
            this.element.dispatchEvent(event);
        },

        remoteMethodTriggered: function (evt) {
            this.consentMethodValue = evt.target.value;
        },

        isRemoteValueChanged: function isRemoteValueChanged(value) {
            this.mutateVisibility(value, this.remoteConsentSectionTarget);
            this.remoteLabelTextTargets.forEach(function (elt) {
                this.mutateVisibility(value, elt);
            }.bind(this));
            this.requiredInputTargets.forEach(function (elt) {
                this.mutateRequirement(value, elt);
            }.bind(this));
        },
    });

    /* Static fields */
    IsRemoteController.targets = [
        "isRemoteInput",
        "requiredInput",
        "remoteLabelText",
        "remoteConsentSection"
    ];

    IsRemoteController.values = {
        "isRemote": Boolean,
        "consentMethod": String,
    };

    const RemoteMethodController = Object.extendClass(Stimulus.Controller);

    Object.assign(RemoteMethodController.prototype, MutateStateMixin, {
            connect: function connect() {
                if (this.hasRequiredInputsTarget) {
                    this.boundRemoteMethodTriggered = this.remoteMethodTriggered.bind(this);
                    document.querySelector("[data-controller='is-remote-controller']").addEventListener(
                        REMOTE_METHOD_EVENT_NAME, this.boundRemoteMethodTriggered
                    );
                }
            },

            remoteMethodTriggered: function remoteMethodTriggered(event) {
                const state = event.detail.method === this.consentMethodValue;
                this.mutateVisibility(state, this.requiredInputsTarget);
                this.requiredInputsTarget.querySelectorAll("input").forEach(function (elt) {
                    this.mutateRequirement(state, elt);
                }.bind(this));
            },

            disconnect: function disconnect() {
                if (this.hasRequiredInputsTarget) {
                    document.querySelector("[data-controller='is-remote-controller']").removeEventListener(
                        REMOTE_METHOD_EVENT_NAME, this.boundRemoteMethodTriggered
                    );
                }
            },
        }
    );

    RemoteMethodController.targets = [
        "requiredInputs"
    ];

    RemoteMethodController.values = {
        "consentMethod": String,
    }

    function init() {
        const application = Stimulus.Application.start();
        application.register("is-remote-controller", IsRemoteController);
        application.register("remote-method-controller", RemoteMethodController);
    }

    window.addEventListener("load", init);
})();
