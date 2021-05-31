"use strict";

(function () {
    window.addEventListener("load", function () {
        function poll() {
            function onLoad(event) {
                var xhr = event.target;
                if (xhr.status === 200 && xhr.response.connectionStatus === "OK") {
                    var path = "";
                    if (window.location.pathname === Urls.renewMandatRemotePending()) {
                        path = Urls.newMandatRecap();
                    } else {
                        path = Urls.fcAuthorize();
                    }
                    var url = window.location.origin + path;
                    location.replace(url);
                }
            }

            var xhr = new XMLHttpRequest();
            xhr.responseType = "json";
            xhr.timeout = 5000;
            xhr.addEventListener("load", onLoad);

            var url = window.location.origin + Urls.newMandatRemotePendingJson();
            xhr.open("GET", url, true);
            xhr.setRequestHeader("Accept", "application/json");

            xhr.send()
        }

        window.addEventListener("trigger_manual", poll);
        setInterval(poll, 10000);
    })
})();
