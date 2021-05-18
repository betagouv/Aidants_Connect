"use strict";

(function () {
    window.addEventListener("load", function () {
        function poll() {
            function onLoad(event) {
                var xhr = event.target;
                if (xhr.status === 200 && xhr.response.connectionStatus === "OK") {
                    var url = window.location.origin + Urls.fcAuthorize();
                    location.replace(url);
                }
            }

            var xhr = new XMLHttpRequest();
            xhr.responseType = "json";
            xhr.timeout = 15000;
            xhr.addEventListener("load", onLoad);

            var url = window.location.origin + Urls.newMandatRemotePendingJson();
            xhr.open("GET", url, true);
            xhr.setRequestHeader("Accept", "application/json");

            xhr.send()
        }

        setInterval(poll, 30000);
    })
})();
