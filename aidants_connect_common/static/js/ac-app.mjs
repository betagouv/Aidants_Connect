import {Application, Controller} from "Stimulus"

class BaseController extends Controller {
    noop() { /* Does nothing */ }
    showElement(elt) {
        elt.removeAttribute("hidden");
        elt.removeAttribute("aria-hidden");
    }

    hideElement(elt) {
        elt.setAttribute("hidden", "hidden");
        elt.setAttribute("aria-hidden", "true");
    }

    mutateVisibility(visibility, elt) {
        if (visibility) this.showElement(elt);
        else this.hideElement(elt);
    }

    mutateRequirement(required, elt) {
        if (required) elt.setAttribute("required", "required");
        else elt.removeAttribute("required");
    }
}

const AidantsConnectApplication = new Application();
const aidantsConnectApplicationReady = AidantsConnectApplication.start().then(() => AidantsConnectApplication)

export {AidantsConnectApplication, aidantsConnectApplicationReady, BaseController}
