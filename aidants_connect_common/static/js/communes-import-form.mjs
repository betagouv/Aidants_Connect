import {BaseController, aidantsConnectApplicationReady} from "AidantsConnectApplication"

class CommuneImportForm extends BaseController {
    static targets = ["communeZrrClassificationWrapper"]
    static values = {zrrResourceName: String}

    initialize() {
        this.hideElement(this.communeZrrClassificationWrapperTarget);
    }
    onOptionSelected(evt) {
        const idx = parseInt(evt.target.value, 10);
        this.mutateVisibility(
            evt.target.options[idx].text === this.zrrResourceNameValue,
            this.communeZrrClassificationWrapperTarget
        )
    }
}

aidantsConnectApplicationReady.then(application => application.register("commune-import-form", CommuneImportForm));
