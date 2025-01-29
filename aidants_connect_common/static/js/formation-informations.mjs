import {BaseController, aidantsConnectApplicationReady} from "AidantsConnectApplication"

/**
 * @property {HTMLSelectElement} regionsInputTarget
 * @property {HTMLElement} informationsContainerTarget
 * @property {String} regionSelectValue
 */
class FormationInformation extends BaseController {
    static targets = ["informationsContainer", "regionsInput"]
    static values = {regionSelect: String}

    initialize () {
        this.showElement(this.element);
        if(this.regionsInputTarget.value) {
            this.regionSelectValue = this.regionsInputTarget.value;
        }
    }

    regionSelectValueChanged(val) {
        fetch(Urls.formationInformations({pk: val}))
            .then(async response => {
                if (response.ok) {
                    this.informationsContainerTarget.innerHTML = await response.text();
                }
            }).catch(() => {});
    }

    regionChanged (evt) {
        this.regionSelectValue = evt.target.value;
    }
}

aidantsConnectApplicationReady.then(application => application.register("formation-informations", FormationInformation));
