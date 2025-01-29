import {BaseController, aidantsConnectApplicationReady} from "AidantsConnectApplication"

class NotificationController extends BaseController {
    static values = {url: String}

    async markRead() {
        const response = await fetch(this.urlValue, {
            method: "DELETE",
            redirect: "manual",
        });
        if (response.ok) {
            this.element.remove();
        }
    }
}

aidantsConnectApplicationReady.then(application => application.register("notification", NotificationController));
