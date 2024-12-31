import {BaseController, aidantsConnectApplicationReady} from "AidantsConnectApplication";

class RemoteConsentWaitingRoom extends BaseController {
    static values = {
        "next": String,
        "poll": String,
        "pollTimeout": Number,
        "csrfToken": String,
    }

    poll () {
        const form = new FormData();
        form.set("csrfmiddlewaretoken", this.csrfTokenValue);

        fetch(this.pollValue, {body: form, method: "post"})
            .then(response => response.ok ? response.json() : Promise.reject())
            .then(result => { if (result.connectionStatus === "OK") window.location.href = this.nextValue; });
    }

    pollTimeoutValueChanged (value) {
        if (this.intervalId) clearInterval(this.intervalId);
        if (value > 0) {
            clearInterval(this.intervalId);
            this.intervalId = setInterval(this.poll.bind(this), value);
        }
    }
}

aidantsConnectApplicationReady.then(app => app.register("remote-consent-waiting-room", RemoteConsentWaitingRoom))
