import {BaseController, aidantsConnectApplicationReady} from "AidantsConnectApplication"

/**
 * @property {HTMLElement} addressContainerTarget
 * @property {HTMLInputElement} addressSameAsOrgRadioTarget
 * @property {HTMLInputElement} autcompleteInputTarget
 * @property {HTMLInputElement} zipcodeInputTarget
 * @property {HTMLInputElement} cityInputTarget
 */
class ManagerForm extends BaseController {
    static values = {issuerData: Object}
    static targets = ["addressContainer", "addressSameAsOrgRadio", "autcompleteInput", "zipcodeInput", "cityInput"]

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
      //   this.mutateAddressContainer(0)
        this.mutateRequirement(!JSON.parse(value.toLowerCase()), this.autcompleteInputTarget)
        this.mutateRequirement(!JSON.parse(value.toLowerCase()), this.zipcodeInputTarget)
        this.mutateRequirement(!JSON.parse(value.toLowerCase()), this.cityInputTarget)
    }

    mutateAddressContainer(value) {
        this.mutateVisibility(!value, this.addressContainerTarget)
    }
}

aidantsConnectApplicationReady.then(application => application.register("manager-form", ManagerForm));
