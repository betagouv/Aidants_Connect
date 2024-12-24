import {BaseController, aidantsConnectApplicationReady} from "AidantsConnectApplication"

/**
 * @property {HTMLElement} addressContainerTarget
 * @property {HTMLInputElement} addressSameAsOrgRadioTarget
 */
class ManagerForm extends BaseController {
    static values = {issuerData: Object}
    static targets = ["addressContainer", "addressSameAsOrgRadio"]

    connect() {
        const elt = document.querySelector("#issuer-data");
        this.issuerDataValue = elt ? JSON.parse(elt.textContent) : {};
    }

    addressSameAsOrgRadioTargetConnected(elt) {
        if(elt.checked) {
            this.onAddressSameAsOrgChanged({target: elt})
        }
    }

    onManagerItsMeBtnClicked() {
        Object.keys(this.issuerDataValue).forEach(key => {
            this.element.querySelector(`[name$='${key}']`).value = this.issuerDataValue[key];
        });
    }

    onAddressSameAsOrgChanged({target: {value}}) {
        this.mutateAddressContainer(JSON.parse(value.toLowerCase()))
    }

    mutateAddressContainer(value) {
        this.mutateVisibility(!value, this.addressContainerTarget)
    }
}

aidantsConnectApplicationReady.then(application => application.register("manager-form", ManagerForm));
