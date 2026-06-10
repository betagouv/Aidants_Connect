import {BaseController, aidantsConnectApplicationReady} from "AidantsConnectApplication"

class MandateFormController extends BaseController {
    static targets = ["bdfWarning"];

    static values = {
        bdfWarning: String,
        scopes: {type: Object, default: {}},
    }

    connect () {
        const scopesValue = this.scopesValue;
        document.querySelectorAll(".mandat-demarche input").forEach(it => {
            it.dataset.action = `${ this.identifier }#scopeSelected`;
            scopesValue[it.value] = it.checked;
        });
        this.scopesValue = scopesValue
    }

    scopeSelected (evt) {
        const scopesValue = this.scopesValue;
        scopesValue[evt.target.value] = evt.target.checked;
        this.scopesValue = scopesValue;
    }

    scopesValueChanged (val) {
        this.mutateVisibility(this.scopesValue[this.bdfWarningValue], this.bdfWarningTarget);
    }
}

aidantsConnectApplicationReady.then(application => {
    application.register("mandate-form-controller", MandateFormController);
});
