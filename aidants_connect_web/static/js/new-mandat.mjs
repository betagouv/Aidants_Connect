import {BaseController, aidantsConnectApplicationReady} from "AidantsConnectApplication"

class MandateFormController extends BaseController {
    static targets = [
        "isRemoteInput",
        "remoteLabelText",
        "bdfWarning",
    ];

    static values = {
        isRemote: Boolean,
        bdfWarning: String,
        scopes: {type: Object, default: {}},
    }

    connect () {
        this.isRemoteValue = this.isRemoteInputTarget.checked;

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

    isRemoteInputTriggered (evt) {
        this.isRemoteValue = evt.target.checked
    }

    isRemoteValueChanged (value) {
        this.remoteLabelTextTargets.forEach(elt => this.mutateVisibility(value, elt));
    }
}

aidantsConnectApplicationReady.then(application => {
    application.register("mandate-form-controller", MandateFormController);
});
