"use strict";

(function () {
    const NewMandatForm = Object.extendClass(Stimulus.Controller);

    Object.assign(NewMandatForm.prototype, {
        "connect": function connect() {
            this.computeUiForRemoteMandateValue(this.isRemoteInputTarget.checked);
            const checkedRadioElt = document.querySelector("#id_remote_constent_method input[type='radio']:checked");
            this.computeUiForRemoteConstentMethod(checkedRadioElt ? checkedRadioElt.value : undefined);
        },

        "isRemoteChanged": function isRemoteChanged(evt) {
            this.computeUiForRemoteMandateValue(evt.target.checked);
        },

        "remoteConstentMethodChanged": function remoteConstentMethodChanged(evt) {
            this.computeUiForRemoteConstentMethod(evt.target.value);
        },

        "computeUiForRemoteMandateValue": function computeUiForRemoteMandateValue(checked) {
            this.remoteLabelTextTargets.forEach(function (elt) {
                this.mutateVisibility(checked, elt);
            }.bind(this));
            this.mutateVisibility(checked, this.remoteContentSectionTarget);
            this.remoteConstentMethodInputTargets.forEach(function(elt) {
                this.mutateRequirement(checked, elt);
            }.bind(this));
        },

        "computeUiForRemoteConstentMethod": function computeUiForRemoteConstentMethod(value) {
            const isUserConsentSms = value === this.smsMethodValue;
            this.mutateVisibility(isUserConsentSms, this.userPhoneInputSectionTarget);
            this.mutateRequirement(isUserConsentSms, this.userPhoneInputTarget);
        },

        "mutateVisibility": function mutateVisibility(visible, elt) {
            if (visible) {
                elt.removeAttribute("hidden");
                elt.removeAttribute("aria-hidden");
            } else {
                elt.setAttribute("hidden", "hidden");
                elt.setAttribute("aria-hidden", "true");
            }
        },

        "mutateRequirement": function mutateRequirement(required, elt) {
            if (required) {
                elt.setAttribute("required", "required");
            } else {
                elt.removeAttribute("required");
            }
        }

    });

    /* Static fields */
    NewMandatForm.targets = [
        "remoteContentSection",
        "isRemoteInput",
        "userPhoneInputSection",
        "userPhoneInput",
        "remoteConstentMethodInput",
        "remoteLabelText",
    ];

    NewMandatForm.values = {
        "smsMethod": String,
    }

    function init() {
        const application = Stimulus.Application.start();
        application.register("new-mandat-form", NewMandatForm);
    }

    window.addEventListener("load", init);
})();
