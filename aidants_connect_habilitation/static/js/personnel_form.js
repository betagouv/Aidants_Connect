"use strict";

(function () {
    const PersonnelForm = Object.extendClass(Stimulus.Controller);

    Object.assign(PersonnelForm.prototype, {
        "connect": function connect() {
            this.formCountValue = this.managmentFormCountTarget.value;
            this.formMaxCountValue = this.managmentFormMaxCountTarget.value;
            this.mutateAddAidantButtonVisibility();
            this.issuerDataValue = JSON.parse(document.getElementById("issuer-data").textContent)
            this.controllerInitializedValue = true;
        },

        "formCountValueChanged": function formCountValueChanged() {
            // A bug in Stimulus makes change events to get fired
            // before the controller's `initialize` method is called
            // which makes the initial form value to get erased. We use
            // the controllerInitializedValue as a flag that the value
            // has not been initialized yet, here.
            if (this.controllerInitializedValue) {
                this.managmentFormCountTarget.value = this.formCountValue;
            }
        },

        "onAddAidantButtonClicked": function onAddAidantButtonClicked() {
            const template = this.aidantFormTemplateTarget.innerHTML.replace(
                /__prefix__/gm, String(this.formCountValue)
            );

            this.aidantFormsetTarget.insertAdjacentHTML("beforeend", template);
            this.formCountValue++;
            this.mutateAddAidantButtonVisibility();
        },

        "onItsMeBtnClicked": function onItsMeBtnClicked(target) {
            const self = this;
            Object.keys(this.issuerDataValue).forEach(function (key) {
                target.querySelector("[name$='" + key + "']").value = self.issuerDataValue[key];
            });
        },

        "onManagerItsMeBtnClicked": function onManagerItsMeBtnClicked() {
            this.onItsMeBtnClicked(this.managerSubformTarget);
        },

        "onDpoItsMeBtnClicked": function onDpoItsMeBtnClicked() {
            this.onItsMeBtnClicked(this.dpoSubformTarget);
        },

        "mutateAddAidantButtonVisibility": function mutateAddAidantButtonVisibility() {
            if (this.formCountValue >= this.formMaxCountValue) {
                this.addAidantButtonContainerTarget.setAttribute("hidden", "hidden");
            } else {
                this.addAidantButtonContainerTarget.removeAttribute("hidden");
            }
        }
    });

    /* Static fields */
    PersonnelForm.targets = [
        "managmentFormCount",
        "managmentFormMaxCount",
        "addAidantButtonContainer",
        "aidantFormTemplate",
        "aidantFormset",
        "managerSubform",
        "dpoSubform",
    ];

    PersonnelForm.values = {
        formCount: Number,
        formMaxCount: Number,
        controllerInitialized: Boolean,
        issuerData: Object
    };

    function init() {
        const application = Stimulus.Application.start();
        application.register("personnel-form", PersonnelForm);
    }

    window.addEventListener("load", init);
})();
