import {BaseController, aidantsConnectApplicationReady} from "AidantsConnectApplication"

class AdminFilterSelect extends BaseController {
    onChange (evt) {
        window.location.href = evt.target.value;
    }
}

aidantsConnectApplicationReady.then(app => app.register("admin-filter-select", AdminFilterSelect))
