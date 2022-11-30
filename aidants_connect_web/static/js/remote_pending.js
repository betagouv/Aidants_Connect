"use strict";

(function () {
    const RemoteConsentWaitingRoom = Object.extendClass(Stimulus.Controller);

    Object.assign(RemoteConsentWaitingRoom.prototype, {
        "poll": function poll() {
            var xhr = new XMLHttpRequest();
            xhr.responseType = "json";
            xhr.timeout = 15000;
            xhr.addEventListener("load", this.onResponse.bind(this));

            var url = window.location.origin + this.pollValue;
            xhr.open("GET", url, true);
            xhr.setRequestHeader("Accept", "application/json");

            xhr.send();
        },

        "onResponse": function onResponse(event) {
            var xhr = event.target;
            if (xhr.status === 200 && xhr.response.connectionStatus === "OK") {
                var url = window.location.origin + this.nextValue;
                location.replace(url);
            }
        },

        "pollTimeoutValueChanged": function pollTimeoutValueChanged(value) {
            if(value > 0) {
                clearInterval(this.intervalId);
                this.intervalId = setInterval(this.poll, value);
            } else if (this.intervalId){
                clearInterval(this.intervalId);
            }
        }
    });

    RemoteConsentWaitingRoom.values = {
        "next": String,
        "poll": String,
        "pollTimeout": Number
    }

    function init() {
        const application = Stimulus.Application.start();
        application.register("remote-content-waiting-room", RemoteConsentWaitingRoom);
    }

    window.addEventListener("load", init);
})();
