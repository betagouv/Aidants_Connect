"use strict";

(function () {
    const DynamicForm = Object.extendClass(Stimulus.Controller);

    Object.assign(DynamicForm.prototype, {
        "connect": function connect() {
            this.selectOrgType(this.typeInputTarget.value);
            this.showHide(this.onlyShownIfPrivateOrgTarget, this.privateOrgInputTarget.checked);
        },

        "onTypeChange": function onTypeChange(evt) {
            this.selectOrgType(evt.target.value);
        },

        "onIsPrivateOrgChange": function onIsPrivateOrgChange(evt) {
            this.showHide(this.onlyShownIfPrivateOrgTarget, evt.target.checked);
        },

        "showHide": function showHide(element, show) {
            if (show) {
                element.removeAttribute("hidden");
            } else {
                element.setAttribute("hidden", "hidden");
            }
        },

        "selectOrgType": function selectOrgType(value) {
            if (value === this.typeInputTarget.dataset.otherValue) {
                this.showTypeOtherInputContainer();
            } else {
                this.hideTypeOtherInputContainer();
            }
        },

        "hideTypeOtherInputContainer": function hideTypeOtherInputContainer() {
            this.typeOtherInputContainerTarget.setAttribute("hidden", "hidden");
        },

        "showTypeOtherInputContainer": function showTypeOtherInputContainer() {
            this.typeOtherInputContainerTarget.removeAttribute("hidden");
            this.typeOtherInputContainerTarget.querySelector("label").textContent =
                this.typeOtherInputTarget.dataset.displayedLabel;
        },
    });

    /* Static fields */
    DynamicForm.targets = ["typeOtherInputContainer", "typeOtherInput", "typeInput", "onlyShownIfPrivateOrg", "privateOrgInput"];

    function init() {
        const application = Stimulus.Application.start();
        application.register("dynamic-form", DynamicForm);
    }

    window.addEventListener("load", init);
})();
