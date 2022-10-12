"use strict";

(function () {
    const NewMandatForm = Object.extendClass(Stimulus.Controller);

    Object.assign(NewMandatForm.prototype, {
        "connect": function connect() {
            this.mutateVisibility(this.isRemoteInputTarget.checked, this.remoteContentSectionTarget);
            this.remoteConstentMethodInputTargets.forEach(function(elt) {
                this.mutateRequirement(this.isRemoteInputTarget.checked, elt);
            }.bind(this));

            const checkedRadioElt = document.querySelector("#id_remote_constent_method input[type='radio']:checked");
            const isUserConsentSms = checkedRadioElt ? checkedRadioElt.value === this.smsMethodValue : false;
            this.mutateVisibility(isUserConsentSms, this.userPhoneInputSectionTarget);
            this.mutateRequirement(isUserConsentSms, this.userPhoneInputTarget);
        },

        "isRemoteChanged": function isRemoteChanged(evt) {
            this.mutateVisibility(evt.target.checked, this.remoteContentSectionTarget);
            this.remoteConstentMethodInputTargets.forEach(function(elt) {
                this.mutateRequirement(evt.target.checked, elt);
            }.bind(this));
        },

        "remoteConstentMethodChanged": function remoteConstentMethodChanged(evt) {
            const isUserConsentSms = evt.target.value === this.smsMethodValue;
            this.mutateVisibility(isUserConsentSms, this.userPhoneInputSectionTarget);
            this.mutateRequirement(isUserConsentSms, this.userPhoneInputTarget);
        },

        "mutateVisibility": function mutateVisibility(visible, elt) {
            if (visible) {
                elt.removeAttribute("hidden");
                elt.removeAttribute("aria-hidden");
            } else {
                elt.setAttribute("hidden", "hidden");
                elt.setAttribute("aria-hidden", "aria-hidden");
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
