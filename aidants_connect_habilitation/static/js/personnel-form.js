import {BaseController, aidantsConnectApplicationReady} from "AidantsConnectApplication"

class PersonnelForm extends BaseController {
    static targets = [
        "managmentFormCount",
        "managmentFormMaxCount",
        "addAidantButtonContainer",
        "aidantFormTemplate",
        "aidantFormset",
        "managerSubform",
    ]

    static values = {
        formCount: Number,
        formMaxCount: Number,
        controllerInitialized: Boolean,
        issuerData: Object
    }

    connect() {
        this.formCountValue = this.managmentFormCountTarget.value;
        this.formMaxCountValue = this.managmentFormMaxCountTarget.value;
        const elt = document.querySelector("#issuer-data");
        this.issuerDataValue = elt ? JSON.parse(elt.textContent) : {};
        this.controllerInitializedValue = true;
    }

    formCountValueChanged() {
        // A bug in Stimulus makes change events to get fired before the controller's `initialize` method is called
        // which makes the initial form value to get erased. We use the controllerInitializedValue as a flag that
        // the value has not been initialized yet, here.
        if (this.controllerInitializedValue) {
            this.managmentFormCountTarget.value = this.formCountValue;
            this.mutateVisibility(
                this.formCountValue < this.formMaxCountValue, this.addAidantButtonContainerTarget
            );
        }
    }

    onAddAidantButtonClicked() {
        const template = this.aidantFormTemplateTarget.innerHTML.replace(/__prefix__/gm, `${this.formCountValue}`);
        this.aidantFormsetTarget.insertAdjacentHTML("beforeend", template);
        this.formCountValue++;
    }

    onManagerItsMeBtnClicked() {
        Object.keys(this.issuerDataValue).forEach(key => {
            this.managerSubformTarget.querySelector(`[name$='${key}']`).value = this.issuerDataValue[key];
        });
    }
}

aidantsConnectApplicationReady.then(application => application.register("personnel-form", PersonnelForm));
