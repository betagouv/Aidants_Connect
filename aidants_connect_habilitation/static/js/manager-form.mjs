import {BaseController, aidantsConnectApplicationReady} from "AidantsConnectApplication"

class ManagerForm extends BaseController {
    static targets = ["managerSubform"]

    static values = {issuerData: Object}

    connect() {
        const elt = document.querySelector("#issuer-data");
        this.issuerDataValue = elt ? JSON.parse(elt.textContent) : {};
    }

    onManagerItsMeBtnClicked() {
        Object.keys(this.issuerDataValue).forEach(key => {
            this.managerSubformTarget.querySelector(`[name$='${key}']`).value = this.issuerDataValue[key];
        });
    }
}

aidantsConnectApplicationReady.then(application => application.register("manager-form", ManagerForm));
