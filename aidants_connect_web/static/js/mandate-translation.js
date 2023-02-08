"use strict";

(function () {
    const MandateTranslation = Object.extendClass(Stimulus.Controller);

    Object.assign(MandateTranslation.prototype, {
        "connect": function connect() {
            this.langCodeValue = document.querySelector(
                "#mandate-translation-lang"
            ).value;
        },

        "langCodeValueChanged": function langCodeValueChanged() {
            if (this.langCodeValue === "") {
                return this.setContainerContent(undefined);
            }

            var xhr = new XMLHttpRequest();
            xhr.responseType = "text";
            xhr.timeout = 15000;
            xhr.addEventListener("load", this.onResponse.bind(this));

            const form = new FormData();
            form.append("lang_code", this.langCodeValue);
            var url = new URL(this.translationEndpointValue);
            xhr.open("POST", url, true);
            xhr.setRequestHeader("Accept", "text/html");
            xhr.send(form);
        },

        "mutateVisibility": function mutateVisibility(visible, elt) {
            if (visible) {
                elt.removeAttribute("hidden");
                elt.removeAttribute("aria-hidden");
            } else {
                elt.setAttribute("hidden", "hidden");
                elt.setAttribute("aria-hidden", "true");
            }
        },

        "onResponse": function onResponse(evt) {
            if (evt.target.status === 200) {
                this.setContainerContent(evt.target.response);
            } else {
                this.setContainerContent(undefined);
            }
        },

        "print": function print() {
            window.print();
        },

        "setContainerContent": function setContainerContent(html) {
            if (html === undefined) {
                this.translationContainerTarget.innerHTML = "";
                this.translationContainerTarget.removeAttribute("lang");
                this.mutateVisibility(false, this.translationContainerTarget);
            } else {
                this.translationContainerTarget.innerHTML = html;
                this.translationContainerTarget.setAttribute("lang", this.langCodeValue);
                this.mutateVisibility(true, this.translationContainerTarget);
            }
        },

        "selectTranslation": function selectTranslation(evt) {
            this.langCodeValue = evt.target.value.trim();
        },
    });

    MandateTranslation.targets = [
        "translationContainer",
    ];

    MandateTranslation.values = {
        "translationEndpoint": String,
        "langCode": String,
    };


    const OpenMandateTranslation = Object.extendClass(Stimulus.Controller);

    Object.assign(OpenMandateTranslation.prototype, {
        "connect": function connect() {
            this.mutateVisibility(true, this.buttonTarget);
        },

        "onOpenTranslation": function onOpenTranslation(evt) {
            evt.preventDefault();
            evt.stopPropagation();

            const searchParams = new URLSearchParams(new FormData(this.formTarget));
            const url = new URL(this.openUrlValue);
            searchParams.forEach(function (v, k, _) {
                if (k !== "csrfmiddlewaretoken") {
                    url.searchParams.append(k, v);
                }
            });
            window.open(url.toString(), "_blank", "noopener,noreferrer");
        },

        "mutateVisibility": function mutateVisibility(visible, elt) {
            if (visible) {
                elt.removeAttribute("hidden");
                elt.removeAttribute("aria-hidden");
            } else {
                elt.setAttribute("hidden", "hidden");
                elt.setAttribute("aria-hidden", "true");
            }
        }
    });

    OpenMandateTranslation.targets = [
        "form",
        "button",
    ]

    OpenMandateTranslation.values = {
        "openUrl": String,
    }

    function init() {
        const application = Stimulus.Application.start();
        application.register("mandate-translation", MandateTranslation);
        application.register("open-mandate-translation", OpenMandateTranslation);
    }

    window.addEventListener("load", init);
})();
