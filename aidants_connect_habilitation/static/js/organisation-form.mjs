import {BaseController, aidantsConnectApplicationReady} from "AidantsConnectApplication"

class DynamicForm extends BaseController {
    static targets = [
        "typeOtherInputContainer",
        "typeInput",
        "onlyShownIfPrivateOrg",
        "privateOrgInput",
        "franceServicesInput",
        "onlyShownIfFranceServices"
    ];

    static values = {typeOther: String}

    connect() {
        this.mutateVisibility(this.typeInputTarget.value === this.typeOtherValue, this.typeOtherInputContainerTarget);
        this.mutateVisibility(this.privateOrgInputTarget.checked, this.onlyShownIfPrivateOrgTarget);
        this.mutateVisibility(this.franceServicesInputTarget.checked, this.onlyShownIfFranceServicesTarget);
    }

     onFranceServicesChange(evt) {
        this.mutateVisibility(evt.target.checked, this.onlyShownIfFranceServicesTarget);
    }

    onIsPrivateOrgChange(evt) {
        this.mutateVisibility(evt.target.checked, this.onlyShownIfPrivateOrgTarget);
    }

    onTypeChange(evt) {
        this.mutateVisibility(evt.target.value === this.typeOtherValue, this.typeOtherInputContainerTarget);
    }
}

aidantsConnectApplicationReady.then(application => application.register("dynamic-form", DynamicForm));
