"use strict";

(function () {
    const DynamicForm = Object.extendClass(Stimulus.Controller);

    Object.assign(DynamicForm.prototype, {
        "connect": function connect() {
            this.selectOrgType(this.typeInputTarget.value);
        },

        "onTypeChange": function onTypeChange(evt) {
            this.selectOrgType(evt.target.value);
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
            this.typeOtherInputContainerTarget.value = "";
        },

        "showTypeOtherInputContainer": function showTypeOtherInputContainer() {
            this.typeOtherInputContainerTarget.removeAttribute("hidden");
            this.typeOtherInputContainerTarget.querySelector("label").textContent =
                this.typeOtherInputTarget.dataset.displayedLabel;
        },
    });

    /* Static fields */
    DynamicForm.targets = ["typeOtherInputContainer", "typeOtherInput", "typeInput"];

    function init() {
        const application = Stimulus.Application.start();
        application.register("dynamic-form", DynamicForm);
    }

    window.addEventListener("load", init);
})();
